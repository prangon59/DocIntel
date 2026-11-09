"""Background job management and bulk reprocessing endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.document import Document, DocumentStatus
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/reprocess-failed",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk re-queue all documents currently in FAILED status.",
)
async def reprocess_failed_jobs(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Find all FAILED documents, reset their status to PENDING, and dispatch Celery tasks."""
    stmt = select(Document).where(Document.status == DocumentStatus.FAILED)
    failed_docs = (await db.execute(stmt)).scalars().all()

    reprocessed_ids: list[str] = []
    for doc in failed_docs:
        doc.status = DocumentStatus.PENDING
        doc.error_message = None
        process_document_task.delay(doc.id)
        reprocessed_ids.append(str(doc.id))

    await db.commit()

    return {
        "reprocessed_count": len(reprocessed_ids),
        "document_ids": reprocessed_ids,
        "message": f"Successfully queued {len(reprocessed_ids)} failed documents for reprocessing.",
    }
