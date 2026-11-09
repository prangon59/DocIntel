"""Celery tasks for distributed asynchronous document ingestion and parallel chunking."""

import asyncio
import json
import logging
import uuid
from typing import Any

import redis
from celery import shared_task  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.ingest.pipeline import process_document_sync

logger = logging.getLogger("docintel.tasks")


def update_redis_progress(
    document_id: str,
    stage: str,
    status: str,
    pages_done: int = 0,
    pages_total: int = 0,
) -> None:
    """Publish real-time progress update to Redis."""
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
        percentage = round((pages_done / pages_total * 100), 1) if pages_total > 0 else 0.0
        payload = {
            "document_id": document_id,
            "stage": stage,
            "status": status,
            "pages_done": pages_done,
            "pages_total": pages_total,
            "percentage": percentage,
        }
        r.set(f"doc:{document_id}:progress", json.dumps(payload), ex=3600)
    except Exception as exc:
        logger.debug("Redis progress update failed: %s", exc)


def get_redis_progress(document_id: str) -> dict[str, Any]:
    """Retrieve document processing progress from Redis."""
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
        raw = r.get(f"doc:{document_id}:progress")
        if raw:
            return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except Exception as exc:
        logger.debug("Could not read Redis progress: %s", exc)
    return {
        "document_id": document_id,
        "stage": "PENDING",
        "status": "PENDING",
        "pages_done": 0,
        "pages_total": 0,
        "percentage": 0.0,
    }


@shared_task(
    name="tasks.process_document",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def process_document_task(self, document_id_str: str) -> dict[str, Any]:
    """Celery task running the ingestion pipeline on an uploaded document."""
    doc_uuid = uuid.UUID(document_id_str)
    update_redis_progress(document_id_str, stage="INGESTION", status="PROCESSING")

    async def _runner():
        async with async_session_factory() as session:
            doc = await process_document_sync(doc_uuid, session)
            return doc.status.value, doc.page_count, doc.error_message

    try:
        status, page_count, err_msg = asyncio.run(_runner())
        update_redis_progress(
            document_id_str,
            stage="INGESTION",
            status=status,
            pages_done=page_count,
            pages_total=page_count,
        )
        return {
            "document_id": document_id_str,
            "status": status,
            "page_count": page_count,
            "error": err_msg,
        }
    except Exception as exc:
        logger.exception("Worker failed processing document %s: %s", document_id_str, exc)
        update_redis_progress(
            document_id_str,
            stage="INGESTION",
            status="FAILED",
            pages_done=0,
            pages_total=0,
        )
        return {
            "document_id": document_id_str,
            "status": "FAILED",
            "error": str(exc),
        }
