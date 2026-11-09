"""Manual correction service with audit logging and automatic validation re-evaluation."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.correction import Correction
from app.models.document import Document
from app.models.event import ProcessingEvent
from app.models.extraction import Extraction, LineItem
from app.models.validation import ValidationIssue
from app.schemas.correction import CorrectionPayload
from app.schemas.extraction import (
    DateEvidence,
    DecimalEvidence,
    ExtractedLineItem,
    InvoiceExtractionSchema,
    StringEvidence,
)
from app.services.validation.duplicates import detect_duplicate_invoices
from app.services.validation.engine import validate_extracted_invoice


async def apply_manual_correction(
    document_id: UUID,
    payload: CorrectionPayload,
    db: AsyncSession,
) -> dict:
    """Apply manual reviewer edits to extracted fields, log audit history, and re-run validation.

    Args:
        document_id: UUID of document to correct.
        payload: Field updates with audit reason and author.
        db: Async database session.

    Returns:
        dict: Updated document result including extractions, validation issues, and audit history.
    """
    stmt = (
        select(Document)
        .options(
            selectinload(Document.extractions).selectinload(Extraction.line_items),
            selectinload(Document.validation_issues),
            selectinload(Document.corrections),
        )
        .where(Document.id == document_id)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    if not doc.extractions:
        # Create an extraction record if none existed
        ext = Extraction(document_id=doc.id)
        db.add(ext)
        await db.flush()
        doc.extractions.append(ext)
    else:
        ext = doc.extractions[0]

    audit_records: list[Correction] = []

    # Map of editable header fields: payload attribute -> extraction column
    field_mappings = [
        ("invoice_number", "invoice_number"),
        ("invoice_date", "invoice_date"),
        ("supplier_name", "supplier_name"),
        ("customer_name", "customer_name"),
        ("subtotal", "subtotal"),
        ("tax", "tax"),
        ("total", "total"),
        ("currency", "currency"),
    ]

    payload_dict = payload.model_dump(exclude_unset=True)

    for payload_attr, ext_col in field_mappings:
        if payload_attr in payload_dict:
            new_val = payload_dict[payload_attr]
            old_val = getattr(ext, ext_col)

            # Check if value actually changed
            if old_val != new_val:
                setattr(ext, ext_col, new_val)
                corr = Correction(
                    document_id=doc.id,
                    field_name=ext_col,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    reason=payload.reason,
                    updated_by=payload.updated_by,
                )
                db.add(corr)
                audit_records.append(corr)

    # Line item updates
    if payload.line_items is not None:
        existing_items_map = {item.id: item for item in ext.line_items}
        for item_corr in payload.line_items:
            if item_corr.id and item_corr.id in existing_items_map:
                li = existing_items_map[item_corr.id]
                for attr in ("description", "quantity", "unit_price", "line_total"):
                    v = getattr(item_corr, attr)
                    if v is not None and getattr(li, attr) != v:
                        old_v = getattr(li, attr)
                        setattr(li, attr, v)
                        corr = Correction(
                            document_id=doc.id,
                            field_name=f"line_item[{li.id}].{attr}",
                            old_value=str(old_v) if old_v is not None else None,
                            new_value=str(v),
                            reason=payload.reason,
                            updated_by=payload.updated_by,
                        )
                        db.add(corr)
                        audit_records.append(corr)
            elif item_corr.description or item_corr.line_total:
                # Add new line item
                new_li = LineItem(
                    extraction_id=ext.id,
                    description=item_corr.description or "",
                    quantity=item_corr.quantity,
                    unit_price=item_corr.unit_price,
                    line_total=item_corr.line_total,
                    confidence=1.0,
                )
                db.add(new_li)
                ext.line_items.append(new_li)
                corr = Correction(
                    document_id=doc.id,
                    field_name="line_items.add",
                    old_value=None,
                    new_value=f"{new_li.description} ({new_li.line_total})",
                    reason=payload.reason,
                    updated_by=payload.updated_by,
                )
                db.add(corr)
                audit_records.append(corr)

    await db.flush()

    # =========================================================================
    # RE-RUN DETERMINISTIC VALIDATION & DUPLICATE DETECTION
    # =========================================================================
    # Construct extraction schema from updated record
    extracted_schema = InvoiceExtractionSchema(
        invoice_number=StringEvidence(value=ext.invoice_number, confidence=1.0),
        supplier_name=StringEvidence(value=ext.supplier_name, confidence=1.0),
        customer_name=StringEvidence(value=ext.customer_name, confidence=1.0) if ext.customer_name else None,
        invoice_date=DateEvidence(value=ext.invoice_date.isoformat(), confidence=1.0) if ext.invoice_date else None,
        subtotal=DecimalEvidence(value=ext.subtotal, confidence=1.0) if ext.subtotal is not None else None,
        tax=DecimalEvidence(value=ext.tax, confidence=1.0) if ext.tax is not None else None,
        total=DecimalEvidence(value=ext.total, confidence=1.0) if ext.total is not None else None,
        currency=StringEvidence(value=ext.currency or "USD", confidence=1.0),
        line_items=[
            ExtractedLineItem(
                description=StringEvidence(value=item.description, confidence=1.0),
                quantity=DecimalEvidence(value=item.quantity, confidence=1.0) if item.quantity is not None else None,
                unit_price=DecimalEvidence(value=item.unit_price, confidence=1.0) if item.unit_price is not None else None,
                line_total=DecimalEvidence(value=item.line_total, confidence=1.0) if item.line_total is not None else None,
                confidence=1.0,
            )
            for item in ext.line_items
        ],
        overall_confidence=1.0,
    )

    val_report = validate_extracted_invoice(extracted_schema, tolerance=settings.MATH_TOLERANCE)
    dup_issues = await detect_duplicate_invoices(extracted_schema, current_document_id=doc.id, db=db)

    all_issues = list(val_report.issues) + list(dup_issues)
    needs_review = val_report.needs_review or bool(dup_issues)

    # Delete previous validation issues
    await db.execute(delete(ValidationIssue).where(ValidationIssue.document_id == doc.id))

    for issue in all_issues:
        db.add(
            ValidationIssue(
                document_id=doc.id,
                code=issue.code,
                severity=issue.severity,
                field=issue.field,
                message=issue.message,
                details=issue.details,
            )
        )

    doc.needs_review = needs_review

    # Add processing event
    db.add(
        ProcessingEvent(
            document_id=doc.id,
            stage="CORRECTION",
            status="SUCCESS",
            duration_ms=10.0,
        )
    )

    await db.commit()
    await db.refresh(doc)

    # Return refreshed result
    refreshed_stmt = (
        select(Document)
        .options(
            selectinload(Document.extractions).selectinload(Extraction.line_items),
            selectinload(Document.validation_issues),
            selectinload(Document.corrections),
        )
        .where(Document.id == document_id)
    )
    refreshed_doc = (await db.execute(refreshed_stmt)).scalar_one()

    return {
        "document_id": str(refreshed_doc.id),
        "filename": refreshed_doc.filename,
        "status": refreshed_doc.status.value,
        "needs_review": refreshed_doc.needs_review,
        "extraction": {
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
            "line_items": [
                {
                    "id": str(li.id),
                    "description": li.description,
                    "quantity": str(li.quantity) if li.quantity is not None else None,
                    "unit_price": str(li.unit_price) if li.unit_price is not None else None,
                    "line_total": str(li.line_total) if li.line_total is not None else None,
                }
                for li in ext.line_items
            ],
        },
        "validation_issues": [
            {
                "id": str(i.id),
                "code": i.code,
                "severity": i.severity.value,
                "field": i.field,
                "message": i.message,
                "details": i.details,
            }
            for i in refreshed_doc.validation_issues
        ],
        "audit_trail": [
            {
                "id": str(c.id),
                "field_name": c.field_name,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "reason": c.reason,
                "updated_by": c.updated_by,
                "created_at": c.created_at.isoformat(),
            }
            for c in refreshed_doc.corrections
        ],
    }
