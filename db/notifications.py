import json
import uuid
from sqlalchemy import text

from db.neon import engine


def _get_document_info(document_id: str):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT "userId", title FROM "Document" WHERE id = :id'),
            {"id": document_id},
        ).fetchone()


def create_notification(
    user_id: str,
    type_: str,
    title: str,
    body: str,
    reference_key: str,
    metadata: dict | None = None,
) -> None:
    with engine.connect() as conn:
        existing = conn.execute(
            text(
                'SELECT id FROM "Notification" WHERE "userId" = :uid AND "referenceKey" = :key'
            ),
            {"uid": user_id, "key": reference_key},
        ).fetchone()
        if existing:
            return

        conn.execute(
            text(
                '''
                INSERT INTO "Notification"
                (id, "userId", type, title, body, read, metadata, "referenceKey", "createdAt")
                VALUES (:id, :uid, :type, :title, :body, false, CAST(:meta AS jsonb), :key, NOW())
                '''
            ),
            {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "type": type_,
                "title": title,
                "body": body,
                "meta": json.dumps(metadata or {}),
                "key": reference_key,
            },
        )
        conn.commit()


def notify_document_ready(document_id: str) -> None:
    row = _get_document_info(document_id)
    if not row:
        return
    user_id, title = row[0], row[1]
    create_notification(
        user_id,
        "document_ready",
        "Document ready",
        f'"{title}" is ready for analysis and chat.',
        f"document_ready:{document_id}",
        {"documentId": document_id},
    )


def notify_document_failed(document_id: str) -> None:
    row = _get_document_info(document_id)
    if not row:
        return
    user_id, title = row[0], row[1]
    create_notification(
        user_id,
        "document_failed",
        "Document processing failed",
        f'"{title}" could not be processed. Try uploading again.',
        f"document_failed:{document_id}",
        {"documentId": document_id},
    )


def notify_analysis_complete(document_id: str, result: dict) -> None:
    row = _get_document_info(document_id)
    if not row:
        return
    user_id, title = row[0], row[1]
    status = result.get("status", "failed")

    if status == "ready":
        risk_level = result.get("risk_level") or "unknown"
        create_notification(
            user_id,
            "analysis_complete",
            "Analysis complete",
            f'PactMind finished analyzing "{title}" (risk: {risk_level}).',
            f"analysis_complete:{document_id}",
            {"documentId": document_id, "riskLevel": risk_level},
        )
        _maybe_risk_alert(user_id, document_id, title, result)
    else:
        create_notification(
            user_id,
            "analysis_failed",
            "Analysis failed",
            f'PactMind could not analyze "{title}". You can retry from the document page.',
            f"analysis_failed:{document_id}",
            {"documentId": document_id},
        )


def _maybe_risk_alert(
    user_id: str, document_id: str, title: str, result: dict
) -> None:
    high_count = int(result.get("high_risk_count") or 0)
    risk_level = (result.get("risk_level") or "").lower()
    if high_count <= 0 and risk_level not in ("high", "critical"):
        return

    detail = (
        f"{high_count} high-risk clause(s) found."
        if high_count > 0
        else f"Overall risk level is {risk_level}."
    )
    create_notification(
        user_id,
        "risk_alert",
        "High-risk clauses detected",
        f'"{title}": {detail}',
        f"risk_alert:{document_id}",
        {
            "documentId": document_id,
            "highRiskCount": high_count,
            "riskLevel": risk_level,
        },
    )
