"""Unified document processing pipeline orchestrator.

Coordinates magic-byte validation, text extraction (PyMuPDF / OCR / Spreadsheets),
LLM information extraction (Gemini / LLMClient), grounding checks, deterministic
financial math validation, and duplicate detection.
"""

import logging
import time
import uuid

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding
from app.models.event import ProcessingEvent
from app.models.extraction import Extraction, LineItem
from app.models.page import Page
from app.models.validation import ValidationIssue
from app.schemas.extraction import InvoiceExtractionSchema
from app.services.extraction import LLMClient, get_llm_client
from app.services.extraction.grounding import GroundingIssue, verify_extraction_grounding
from app.services.ingest.detector import detect_file_type
from app.services.ingest.storage import get_absolute_file_path
from app.services.ocr.engine import extract_ocr_from_image, extract_ocr_from_multipage_tiff
from app.services.pdf.extractor import extract_all_pdf_pages, inspect_pdf
from app.services.search.embedder import get_embedder
from app.services.spreadsheet.mapping import (
    heuristic_header_mapping,
    parse_rows_with_mapping,
)
from app.services.spreadsheet.parser import parse_spreadsheet
from app.services.validation.duplicates import detect_duplicate_invoices
from app.services.validation.engine import validate_extracted_invoice

logger = logging.getLogger("docintel.pipeline")


class PipelineProcessingError(Exception):
    """Raised when an unrecoverable document pipeline failure occurs."""

    pass


async def process_document_sync(
    document_id: uuid.UUID,
    db: AsyncSession,
    llm_client: LLMClient | None = None,
) -> Document:
    """Execute end-to-end ingestion, AI extraction, and validation pipeline.

    Ensures that any failure marks the document as FAILED with a clear error
    and records a failed ProcessingEvent, without raising an uncaught exception.

    Args:
        document_id: UUID of the Document to process.
        db: Active Async SQLAlchemy session.
        llm_client: Optional LLMClient override for dependency injection in tests.

    Returns:
        Updated Document instance.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    document: Document | None = result.scalar_one_or_none()

    if not document:
        raise ValueError(f"Document {document_id} not found.")

    pipeline_start = time.perf_counter()
    document.status = DocumentStatus.PROCESSING
    await db.commit()

    file_path = str(get_absolute_file_path(document.storage_path))
    active_client = llm_client or get_llm_client()

    try:
        # =====================================================================
        # STAGE 1: INGESTION & TEXT EXTRACTION
        # =====================================================================
        ingest_start = time.perf_counter()
        with open(file_path, "rb") as f:
            file_bytes = f.read(8192)

        detection = detect_file_type(file_bytes, filename=document.filename)
        if not detection.is_supported:
            raise PipelineProcessingError(
                detection.error_message or f"Unsupported file type: {detection.file_type}"
            )

        document.file_type = detection.file_type
        document.mime_type = detection.mime_type

        pages_to_create: list[Page] = []
        file_type = detection.file_type
        parsed_sheets_data = None

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
            parsed_sheets_data = parse_spreadsheet(file_path, file_type=file_type)
            document.page_count = len(parsed_sheets_data)
            for s in parsed_sheets_data:
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

        for page in pages_to_create:
            db.add(page)

        ingest_duration_ms = (time.perf_counter() - ingest_start) * 1000
        db.add(
            ProcessingEvent(
                document_id=document.id,
                stage="INGESTION",
                status="SUCCESS",
                duration_ms=ingest_duration_ms,
            )
        )
        await db.flush()

        # =====================================================================
        # STAGE 2: AI INFORMATION EXTRACTION & GROUNDING
        # =====================================================================
        extract_start = time.perf_counter()
        extractions_to_persist: list[InvoiceExtractionSchema] = []
        grounding_issues: list[GroundingIssue] = []

        combined_text = "\n\n".join(p.raw_text for p in pages_to_create if p.raw_text.strip())

        if file_type in ("xlsx", "xls", "csv") and parsed_sheets_data:
            # Spreadsheet extraction via column mapping
            for sheet in parsed_sheets_data:
                try:
                    mapping = await active_client.map_spreadsheet_columns(sheet.headers)
                except Exception as map_err:
                    logger.warning(
                        "LLM column mapping unavailable (%s); using heuristics.", map_err
                    )
                    mapping = heuristic_header_mapping(sheet.headers)

                sheet_extractions = parse_rows_with_mapping(sheet, mapping)
                extractions_to_persist.extend(sheet_extractions)
        else:
            # Document/image extraction via LLM
            if combined_text:
                try:
                    extraction_schema = await active_client.extract_invoice(combined_text)
                    # Grounding check against verbatim source text
                    g_issues = verify_extraction_grounding(extraction_schema, combined_text)
                    grounding_issues.extend(g_issues)
                    extractions_to_persist.append(extraction_schema)
                except Exception as llm_err:
                    logger.warning("LLM extraction call failed: %s", llm_err)
                    # Empty extraction schema with null values if LLM is unavailable
                    extractions_to_persist.append(InvoiceExtractionSchema())
            else:
                extractions_to_persist.append(InvoiceExtractionSchema())

        # Persist Extractions and LineItems to database
        model_name = getattr(active_client, "model_name", "gemini-2.5-flash")
        for ext_schema in extractions_to_persist:
            ext_record = Extraction(
                document_id=document.id,
                invoice_number=ext_schema.invoice_number.value
                if ext_schema.invoice_number
                else None,
                invoice_date=ext_schema.invoice_date.as_date() if ext_schema.invoice_date else None,
                supplier_name=ext_schema.supplier_name.value if ext_schema.supplier_name else None,
                customer_name=ext_schema.customer_name.value if ext_schema.customer_name else None,
                subtotal=ext_schema.subtotal.value if ext_schema.subtotal else None,
                tax=ext_schema.tax.value if ext_schema.tax else None,
                total=ext_schema.total.value if ext_schema.total else None,
                currency=ext_schema.currency.value if ext_schema.currency else None,
                overall_confidence=ext_schema.overall_confidence,
                raw_llm_payload=ext_schema.model_dump(mode="json"),
                model_name=model_name,
                prompt_version="v1.0",
            )
            db.add(ext_record)
            await db.flush()

            for item in ext_schema.line_items:
                line_record = LineItem(
                    extraction_id=ext_record.id,
                    description=item.description.value or "",
                    quantity=item.quantity.value,
                    unit_price=item.unit_price.value,
                    line_total=item.line_total.value,
                    confidence=item.confidence,
                )
                db.add(line_record)

        extract_duration_ms = (time.perf_counter() - extract_start) * 1000
        db.add(
            ProcessingEvent(
                document_id=document.id,
                stage="EXTRACTION",
                status="SUCCESS",
                duration_ms=extract_duration_ms,
            )
        )
        await db.flush()

        # =====================================================================
        # STAGE 3: DETERMINISTIC VALIDATION & DUPLICATE DETECTION
        # =====================================================================
        validate_start = time.perf_counter()
        needs_review = False

        for ext_schema in extractions_to_persist:
            # 1. Deterministic math & sanity validation
            val_report = validate_extracted_invoice(
                ext_schema,
                tolerance=settings.MATH_TOLERANCE,
                grounding_issues=grounding_issues,
            )
            if val_report.needs_review:
                needs_review = True

            for issue in val_report.issues:
                db.add(
                    ValidationIssue(
                        document_id=document.id,
                        code=issue.code,
                        severity=issue.severity,
                        field=issue.field,
                        message=issue.message,
                        details=issue.details,
                    )
                )

            # 2. Duplicate invoice detection
            dup_issues = await detect_duplicate_invoices(ext_schema, document.id, db)
            if dup_issues:
                needs_review = True
                for issue in dup_issues:
                    db.add(
                        ValidationIssue(
                            document_id=document.id,
                            code=issue.code,
                            severity=issue.severity,
                            field=issue.field,
                            message=issue.message,
                            details=issue.details,
                        )
                    )

        validate_duration_ms = (time.perf_counter() - validate_start) * 1000
        db.add(
            ProcessingEvent(
                document_id=document.id,
                stage="VALIDATION",
                status="SUCCESS",
                duration_ms=validate_duration_ms,
            )
        )

        # =====================================================================
        # STAGE 4: VECTOR EMBEDDING GENERATION
        # =====================================================================
        try:
            embedder = get_embedder()
            for page in pages_to_create:
                if page.raw_text and page.raw_text.strip():
                    page_text = page.raw_text.strip()
                    vector = await embedder.embed_text(page_text[:2000])
                    db.add(
                        Embedding(
                            document_id=document.id,
                            page_id=page.id,
                            chunk_text=page_text[:2000],
                            embedding=vector,
                        )
                    )
        except Exception as emb_err:
            logger.warning(
                "Embedding generation skipped for doc %s (%s); continuing pipeline.",
                document.id,
                emb_err,
            )

        # Final document state
        document.status = DocumentStatus.COMPLETED
        document.needs_review = needs_review
        document.error_message = None

        await db.commit()
        await db.refresh(document)
        return document

    except Exception as exc:
        total_duration_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.warning("Document %s pipeline failed: %s", document.id, exc)

        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)

        db.add(
            ProcessingEvent(
                document_id=document.id,
                stage="PIPELINE",
                status="FAILED",
                duration_ms=total_duration_ms,
                error_message=str(exc),
            )
        )
        await db.commit()
        await db.refresh(document)
        return document
