from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from models.schemas import QueryRequest, QueryResponse, QuerySource
from db.ownership import assert_document_owner
from db.billing import assert_usage_allowed
from db.document_review import get_document_query_flags
from services.content_guard import (
  assess_question_scope,
  assess_retrieval_relevance,
  _OFF_TOPIC_SHORT,
)
from services.groq_service import (
  generate_answer,
  generate_answer_stream,
  _clean_answer,
  _confidence_from_sources,
)
from services.retrieval import retrieve_document_chunks

router = APIRouter()

_BLOCKED_DOC_MESSAGE = (
  "This document has been flagged during content review. "
  "Chat is disabled until an admin approves it or you upload a valid contract. "
  "Contact support if you believe this is a mistake."
)


def _document_query_allowed(document_id: str) -> tuple[bool, str | None]:
  flags = get_document_query_flags(document_id)
  if not flags.get("found"):
    return False, "Document not found"
  if flags.get("content_review_status") == "rejected":
    return False, _BLOCKED_DOC_MESSAGE
  if flags.get("queries_enabled") is False:
    return False, _BLOCKED_DOC_MESSAGE
  return True, None


def _blocked_stream(message: str, *, irrelevant: bool = False):
  def event_stream():
    yield f"data: {json.dumps({'type': 'status', 'text': 'Checking…'})}\n\n"
    yield f"data: {json.dumps({'type': 'token', 'text': message})}\n\n"
    yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'confidence': 'low', 'irrelevant': irrelevant})}\n\n"

  return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  )


def _done_payload(confidence: str, *, irrelevant: bool = False) -> str:
  return json.dumps({
    "type": "done",
    "confidence": confidence,
    "irrelevant": irrelevant,
  })


def _sources_payload(chunks: list[dict]) -> list[dict]:
  return [
    {
      "content": c["content"],
      "chunk_index": c["chunk_index"],
      "score": c["score"],
    }
    for c in chunks
  ]


@router.post("/stream")
async def query_document_stream(request: QueryRequest):
  assert_document_owner(request.document_id, request.user_id)
  assert_usage_allowed(request.user_id, "chatMessages")

  allowed, block_reason = _document_query_allowed(request.document_id)
  if not allowed:
    return _blocked_stream(block_reason or _BLOCKED_DOC_MESSAGE)

  scope = assess_question_scope(request.question)
  if not scope["allowed"]:
    return _blocked_stream(
      scope["reason"]
      or "PactMind only answers questions about your uploaded contract.",
      irrelevant=True,
    )

  history = [{"role": t.role, "content": t.content} for t in request.history]

  def event_stream():
    yield f"data: {json.dumps({'type': 'status', 'text': 'Analyzing…'})}\n\n"

    chunks = retrieve_document_chunks(request.question, request.document_id, history)

    relevance = assess_retrieval_relevance(request.question, chunks)
    if not relevance["relevant"]:
      yield f"data: {json.dumps({'type': 'token', 'text': relevance['reason']})}\n\n"
      yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
      yield f"data: {_done_payload('low', irrelevant=True)}\n\n"
      return

    if not chunks:
      yield f"data: {json.dumps({'type': 'token', 'text': 'I could not find relevant information in this document for your question.'})}\n\n"
      yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
      yield f"data: {_done_payload('low', irrelevant=True)}\n\n"
      return

    sources = _sources_payload(chunks)
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'text': 'Thinking…'})}\n\n"

    parts: list[str] = []
    for token in generate_answer_stream(
      request.question, chunks, mode=request.mode, history=request.history
    ):
      parts.append(token)
      yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

    answer = _clean_answer("".join(parts))
    confidence = _confidence_from_sources(chunks, answer)
    yield f"data: {_done_payload(confidence, irrelevant=False)}\n\n"

  return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  )


@router.post("/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
  assert_document_owner(request.document_id, request.user_id)
  assert_usage_allowed(request.user_id, "chatMessages")

  allowed, block_reason = _document_query_allowed(request.document_id)
  if not allowed:
    return QueryResponse(
      answer=block_reason or _BLOCKED_DOC_MESSAGE,
      sources=[],
      confidence="low",
    )

  scope = assess_question_scope(request.question)
  if not scope["allowed"]:
    return QueryResponse(
      answer=scope["reason"]
      or "PactMind only answers questions about your uploaded contract.",
      sources=[],
      confidence="low",
      irrelevant=True,
    )

  history = [{"role": t.role, "content": t.content} for t in request.history]
  chunks = retrieve_document_chunks(request.question, request.document_id, history)

  relevance = assess_retrieval_relevance(request.question, chunks)
  if not relevance["relevant"]:
    return QueryResponse(
      answer=relevance["reason"] or _OFF_TOPIC_SHORT,
      sources=[],
      confidence="low",
      irrelevant=True,
    )

  if not chunks:
    return QueryResponse(
      answer="I could not find relevant information in this document for your question.",
      sources=[],
      confidence="low",
      irrelevant=True,
    )

  result = generate_answer(
    request.question, chunks, mode=request.mode, history=request.history
  )

  sources = [
    QuerySource(
      content=c["content"],
      chunk_index=c["chunk_index"],
      score=c["score"],
    )
    for c in chunks
  ]

  return QueryResponse(
    answer=result["answer"],
    sources=sources,
    confidence=result["confidence"],
  )
