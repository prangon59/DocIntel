"""Documents API endpoints for multi-file upload, status polling, and inspection."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db_session
from app.core.logging import logger
from app.models.document import Document, DocumentStatus
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadItem,
    DocumentUploadResponse,
)
from app.services.ingest.detector import detect_file_type
from app.services.ingest.storage import save_uploaded_file
from app.workers.tasks import get_redis_progress, process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload one or multiple business documents for async processing.",
)
async def upload_documents(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """Accept multiple PDF, JPG, PNG, TIFF, XLSX, XLS, and CSV files.

    Validates files by magic bytes, persists to storage, creates Document records,
    and dispatches background Celery workers. Never crashes the batch if an individual file fails.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided in the upload request.",
        )

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    upload_items: list[DocumentUploadItem] = []

    for file in files:
        filename = file.filename or "unknown_file"
        try:
            content = await file.read()
            if len(content) > max_bytes:
                # Mark as failed due to size limit
                doc = Document(
                    filename=filename,
                    file_type="unknown",
                    mime_type="application/octet-stream",
                    file_size=len(content),
                    file_hash="exceeded_size",
                    storage_path="",
                    status=DocumentStatus.FAILED,
                    error_message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_MB}MB.",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                upload_items.append(
                    DocumentUploadItem(
                        id=doc.id,
                        filename=filename,
                        status="FAILED",
                        job_id="none",
                    )
                )
                continue

            # 1. Magic-byte verification
            detected = detect_file_type(content, filename=filename)
            if not detected.is_supported:
                # Invalid magic bytes or unsupported format
                doc = Document(
                    filename=filename,
                    file_type=detected.file_type,
                    mime_type=detected.mime_type,
                    file_size=len(content),
                    file_hash="invalid_magic_bytes",
                    storage_path="",
                    status=DocumentStatus.FAILED,
                    error_message=detected.error_message or "Unsupported file format.",
                )
                db.add(doc)
                await db.commit()
                await db.refresh(doc)
                upload_items.append(
                    DocumentUploadItem(
                        id=doc.id,
                        filename=filename,
                        status="FAILED",
                        job_id="none",
                    )
                )
                continue

            # 2. Persist to storage
            storage_path, file_hash, file_size = save_uploaded_file(content, filename)

            # 3. Create document record
            doc = Document(
                filename=filename,
                file_type=detected.file_type,
                mime_type=detected.mime_type,
                file_size=file_size,
                file_hash=file_hash,
                storage_path=storage_path,
                status=DocumentStatus.PENDING,
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)

            # 4. Dispatch Celery task
            job_id = f"job-{doc.id}"
            try:
                task = process_document_task.delay(str(doc.id))
                job_id = task.id
            except Exception as task_exc:
                logger.warning("Celery dispatch offline: %s. Document remains PENDING.", task_exc)

            upload_items.append(
                DocumentUploadItem(
                    id=doc.id,
                    filename=filename,
                    status=DocumentStatus.PENDING.value,
                    job_id=job_id,
                )
            )

        except Exception as exc:
            logger.exception("Error processing uploaded file %s: %s", filename, exc)
            # Never let a single bad file crash the batch
            upload_items.append(
                DocumentUploadItem(
                    id=uuid.uuid4(),
                    filename=filename,
                    status="FAILED",
                    job_id="none",
                )
            )

    return DocumentUploadResponse(
        uploaded=upload_items,
        total_files=len(upload_items),
        message=f"Successfully queued {len(upload_items)} file(s) for ingestion.",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List ingested documents with optional filtering and pagination.",
)
async def list_documents(
    status: DocumentStatus | None = None,
    file_type: str | None = None,
    needs_review: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """Query ingested documents with pagination, status filtering, and review status."""
    query = select(Document)
    count_query = select(func.count(Document.id))

    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)
    if file_type:
        query = query.where(Document.file_type == file_type.lower())
        count_query = count_query.where(Document.file_type == file_type.lower())
    if needs_review is not None:
        query = query.where(Document.needs_review == needs_review)
        count_query = count_query.where(Document.needs_review == needs_review)

    total_count = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    documents = (await db.execute(query)).scalars().all()

    return DocumentListResponse(
        items=[DocumentRead.model_validate(doc) for doc in documents],
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get full document metadata and extracted page texts.",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DocumentDetailResponse:
    """Fetch complete document metadata along with individual page extractions."""
    stmt = select(Document).options(selectinload(Document.pages)).where(Document.id == document_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} was not found.",
        )
    return DocumentDetailResponse.model_validate(doc)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get real-time document processing stage and progress.",
)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DocumentStatusResponse:
    """Poll live processing stage, page-level progress, and completion status."""
    # First check Redis live progress
    progress = get_redis_progress(str(document_id))

    # If completed or failed in Redis, return
    if progress.get("status") in (DocumentStatus.COMPLETED.value, DocumentStatus.FAILED.value):
        return DocumentStatusResponse(
            document_id=document_id,
            status=progress["status"],
            stage=progress.get("stage", "INGESTION"),
            pages_done=progress.get("pages_done", 0),
            pages_total=progress.get("pages_total", 0),
            percentage=progress.get("percentage", 100.0),
        )

    # Fallback to DB
    stmt = select(Document).where(Document.id == document_id)
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    pages_total = doc.page_count
    pages_done = pages_total if doc.status == DocumentStatus.COMPLETED else 0
    pct = (
        100.0
        if doc.status == DocumentStatus.COMPLETED
        else (50.0 if doc.status == DocumentStatus.PROCESSING else 0.0)
    )

    return DocumentStatusResponse(
        document_id=doc.id,
        status=doc.status.value,
        stage="INGESTION" if doc.status == DocumentStatus.PROCESSING else "COMPLETED",
        pages_done=pages_done,
        pages_total=pages_total,
        percentage=pct,
        error_message=doc.error_message,
    )


@router.get(
    "/{document_id}/result",
    summary="Get extracted results, line items, and validation issues.",
)
async def get_document_result(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Fetch structured invoice data, line items, and deterministic validation issues."""
    stmt = (
        select(Document)
        .options(
            selectinload(Document.extractions),
            selectinload(Document.validation_issues),
        )
        .where(Document.id == document_id)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status.value,
        "needs_review": doc.needs_review,
        "extractions": [
            {
                "id": str(ext.id),
                "invoice_number": ext.invoice_number,
                "invoice_date": str(ext.invoice_date) if ext.invoice_date else None,
                "supplier_name": ext.supplier_name,
                "customer_name": ext.customer_name,
                "subtotal": str(ext.subtotal) if ext.subtotal is not None else None,
                "tax": str(ext.tax) if ext.tax is not None else None,
                "total": str(ext.total) if ext.total is not None else None,
                "currency": ext.currency,
                "confidence": ext.overall_confidence,
            }
            for ext in doc.extractions
        ],
        "validation_issues": [
            {
                "id": str(issue.id),
                "code": issue.code,
                "severity": issue.severity.value,
                "field": issue.field,
                "message": issue.message,
                "details": issue.details,
            }
            for issue in doc.validation_issues
        ],
    }
