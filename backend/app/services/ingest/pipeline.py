"""Unified document processing pipeline orchestrator.

Coordinates magic-byte validation, OCR/PyMuPDF/Spreadsheet extraction,
page persistence, and status updates. Never crashes the batch on individual failures.
"""

import logging
import time
import uuid

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.event import ProcessingEvent
from app.models.page import Page
from app.services.ingest.detector import detect_file_type
from app.services.ingest.storage import get_absolute_file_path
from app.services.ocr.engine import extract_ocr_from_image, extract_ocr_from_multipage_tiff
from app.services.pdf.extractor import extract_all_pdf_pages, inspect_pdf
from app.services.spreadsheet.parser import parse_spreadsheet

logger = logging.getLogger("docintel.pipeline")


class PipelineProcessingError(Exception):
    """Raised when an unrecoverable document pipeline failure occurs."""

    pass


async def process_document_sync(
    document_id: uuid.UUID,
    db: AsyncSession,
) -> Document:
    """Execute end-to-end ingestion pipeline for a document record.

    Ensures that any failure marks the document as FAILED with an error message
    and records a failed ProcessingEvent, without raising an uncaught exception.

    Args:
        document_id: UUID of the Document to process.
        db: Active Async SQLAlchemy session.

    Returns:
        Updated Document instance.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document: Document | None = result.scalar_one_or_none()

    if not document:
        raise ValueError(f"Document {document_id} not found.")

    start_time = time.perf_counter()
    document.status = DocumentStatus.PROCESSING
    await db.commit()

    file_path = str(get_absolute_file_path(document.storage_path))

    try:
        # 1. Read header bytes to verify magic bytes
        with open(file_path, "rb") as f:
            file_bytes = f.read(8192)

        detection = detect_file_type(file_bytes, filename=document.filename)
        if not detection.is_supported:
            raise PipelineProcessingError(
                detection.error_message or f"Unsupported file type: {detection.file_type}"
            )

        # Update detected mime/type if verified
        document.file_type = detection.file_type
        document.mime_type = detection.mime_type

        # 2. Dispatch extraction by format
        pages_to_create: list[Page] = []
        file_type = detection.file_type

        if file_type == "pdf":
            page_count, is_enc, err = inspect_pdf(file_path)
            if err:
                raise PipelineProcessingError(err)

            pdf_pages = extract_all_pdf_pages(file_path)
            document.page_count = len(pdf_pages)

            for p in pdf_pages:
                pages_to_create.append(
                    Page(
                        document_id=document.id,
                        page_number=p.page_number,
                        raw_text=p.text,
                        extraction_method=p.method,
                        ocr_confidence=p.ocr_confidence,
                        char_count=p.char_count,
                    )
                )

        elif file_type in ("png", "jpg"):
            document.page_count = 1
            with Image.open(file_path) as img:
                ocr_result = extract_ocr_from_image(img)

            pages_to_create.append(
                Page(
                    document_id=document.id,
                    page_number=1,
                    raw_text=ocr_result.text,
                    extraction_method="tesseract_ocr",
                    ocr_confidence=ocr_result.confidence,
                    char_count=ocr_result.char_count,
                )
            )

        elif file_type == "tiff":
            ocr_results = extract_ocr_from_multipage_tiff(file_path)
            document.page_count = len(ocr_results)
            for p_idx, ocr_res in enumerate(ocr_results, start=1):
                pages_to_create.append(
                    Page(
                        document_id=document.id,
                        page_number=p_idx,
                        raw_text=ocr_res.text,
                        extraction_method="tesseract_ocr",
                        ocr_confidence=ocr_res.confidence,
                        char_count=ocr_res.char_count,
                    )
                )

        elif file_type in ("xlsx", "xls", "csv"):
            sheets = parse_spreadsheet(file_path, file_type=file_type)
            document.page_count = len(sheets)
            for s in sheets:
                pages_to_create.append(
                    Page(
                        document_id=document.id,
                        page_number=s.sheet_index,
                        raw_text=s.raw_text,
                        extraction_method=f"{file_type}_sheet",
                        ocr_confidence=1.0,
                        char_count=len(s.raw_text),
                    )
                )
        else:
            raise PipelineProcessingError(f"Unhandled document type: {file_type}")

        # 3. Persist pages
        for page in pages_to_create:
            db.add(page)

        duration_ms = (time.perf_counter() - start_time) * 1000
        document.status = DocumentStatus.COMPLETED
        document.error_message = None

        # Record successful processing event
        event = ProcessingEvent(
            document_id=document.id,
            stage="INGESTION",
            status="SUCCESS",
            duration_ms=duration_ms,
        )
        db.add(event)
        await db.commit()
        await db.refresh(document)
        return document

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.warning("Document %s processing failed: %s", document.id, exc)

        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)

        # Record failed processing event
        event = ProcessingEvent(
            document_id=document.id,
            stage="INGESTION",
            status="FAILED",
            duration_ms=duration_ms,
            error_message=str(exc),
        )
        db.add(event)
        await db.commit()
        await db.refresh(document)
        return document
