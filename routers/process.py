import logging

import psycopg2
from fastapi import APIRouter, BackgroundTasks
from models.schemas import DeleteVectorsRequest, ProcessRequest
from services.parser import parse_document
from services.chunker import chunk_text
from services.embedder import embed_texts
from services.pinecone_service import delete_document_vectors, store_chunks
from db.neon import DATABASE_URL, update_document_status
from db.notifications import notify_document_failed, notify_document_ready
from db.ownership import assert_document_owner
from db.analysis import set_analysis_pending, save_document_analysis
from db.agents import set_agents_pending, save_agent_report
from db.document_review import update_document_review
from services.analyzer import analyze_contract
from services.agents import run_agent_team
from services.content_guard import security_scan_document
from job_limits import job_slot, reject_if_queue_full

router = APIRouter()
logger = logging.getLogger("pactmind.engine.process")


async def process_document_task(request: ProcessRequest):
    async with job_slot():
      try:
        # 1. Update status to processing
        update_document_status(request.document_id, "processing")

        # 2. Parse document
        text = await parse_document(request.file_url, request.file_type)

        # 3. Chunk text
        chunks = chunk_text(text)

        # 4. Embed chunks
        embeddings = embed_texts(chunks)

        # 5. Store in Pinecone
        pinecone_ids = store_chunks(request.document_id, chunks, embeddings)

        # 6. Save chunks to Neon DB (clear stale rows from prior runs)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            'DELETE FROM "Chunk" WHERE "documentId" = %s',
            (request.document_id,),
        )
        for i, (chunk, pid) in enumerate(zip(chunks, pinecone_ids)):
            cur.execute(
                'INSERT INTO "Chunk" (id, content, "chunkIndex", "pineconeId", "documentId", "createdAt") VALUES (gen_random_uuid()::text, %s, %s, %s, %s, NOW())',
                (chunk, i, pid, request.document_id)
            )
        conn.commit()
        cur.close()
        conn.close()

        # 7. Update status to ready
        update_document_status(request.document_id, "ready")
        notify_document_ready(request.document_id)

        # 7b. Auto security scan — safe-by-default (immediate use unless malicious)
        try:
            scan = security_scan_document(text)
            update_document_review(
                request.document_id,
                scan.get("status", "valid"),
                scan,
                queries_enabled=scan.get("queries_enabled", True),
            )
            if not scan.get("safe", True):
                from db.document_review import notify_admins_document_security

                notify_admins_document_security(request.document_id, scan)
        except Exception:
            logger.exception("security_scan failed for %s", request.document_id)

        # 8. PactMind auto-analysis (risk scanner + summary)
        try:
            set_analysis_pending(request.document_id)
            analysis = analyze_contract(text)
            save_document_analysis(request.document_id, analysis)
        except Exception:
            save_document_analysis(request.document_id, {"status": "failed"})

        # 9. PactMind agent team (parallel specialist opinions)
        try:
            set_agents_pending(request.document_id)
            agent_result = run_agent_team(text)
            save_agent_report(request.document_id, agent_result)
        except Exception:
            save_agent_report(request.document_id, {"status": "failed", "agents": []})

      except Exception:
        logger.exception(
            "process_document_task failed",
            extra={"document_id": request.document_id, "user_id": request.user_id},
        )
        update_document_status(request.document_id, "failed")
        notify_document_failed(request.document_id)

@router.post("/")
async def process_document(request: ProcessRequest, background_tasks: BackgroundTasks):
    assert_document_owner(request.document_id, request.user_id)
    reject_if_queue_full()
    background_tasks.add_task(process_document_task, request)
    return {"message": "Document processing started", "document_id": request.document_id}


@router.post("/delete-vectors")
async def delete_vectors(request: DeleteVectorsRequest):
    assert_document_owner(request.document_id, request.user_id)
    delete_document_vectors(request.document_id)
    return {"message": "Vectors deleted", "document_id": request.document_id}