"""Cross-verification engine reconciling invoices across documents (PDF <-> PDF, PDF <-> Excel)."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.document import Document
from app.models.extraction import Extraction
from app.schemas.crossverify import CrossVerificationReport, DiscrepancyItem


def _normalize_str(val: str | None) -> str:
    return val.strip().lower() if val else ""


def _amounts_match(val_a: Decimal | None, val_b: Decimal | None, tol: Decimal) -> bool:
    if val_a is None and val_b is None:
        return True
    if val_a is None or val_b is None:
        return False
    return abs(val_a - val_b) <= tol


async def verify_document_pair(
    doc_a_id: UUID,
    doc_b_id: UUID,
    db: AsyncSession,
) -> CrossVerificationReport:
    """Reconcile extracted data between two documents (e.g. PDF invoice vs Excel ledger)."""
    stmt_a = (
        select(Document)
        .options(selectinload(Document.extractions).selectinload(Extraction.line_items))
        .where(Document.id == doc_a_id)
    )
    stmt_b = (
        select(Document)
        .options(selectinload(Document.extractions).selectinload(Extraction.line_items))
        .where(Document.id == doc_b_id)
    )

    doc_a = (await db.execute(stmt_a)).scalar_one_or_none()
    doc_b = (await db.execute(stmt_b)).scalar_one_or_none()

    if not doc_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_a_id} not found."
        )
    if not doc_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_b_id} not found."
        )

    ext_a = doc_a.extractions[0] if doc_a.extractions else None
    ext_b = doc_b.extractions[0] if doc_b.extractions else None

    if not ext_a or not ext_b:
        return CrossVerificationReport(
            document_a_id=doc_a.id,
            document_b_id=doc_b.id,
            document_a_filename=doc_a.filename,
            document_b_filename=doc_b.filename,
            matched=False,
            is_concordant=False,
            summary="One or both documents do not have structured extraction results.",
        )

    norm_inv_a = _normalize_str(ext_a.invoice_number)
    norm_inv_b = _normalize_str(ext_b.invoice_number)
    norm_sup_a = _normalize_str(ext_a.supplier_name)
    norm_sup_b = _normalize_str(ext_b.supplier_name)

    # Check key matching criteria (invoice number and supplier)
    inv_matches = norm_inv_a and norm_inv_b and (norm_inv_a == norm_inv_b)
    sup_similarity = (
        fuzz.token_sort_ratio(norm_sup_a, norm_sup_b) if norm_sup_a and norm_sup_b else 0
    )
    sup_matches = sup_similarity >= 75 or (not norm_sup_a and not norm_sup_b)

    matched = bool(
        inv_matches or (sup_matches and ext_a.total is not None and ext_a.total == ext_b.total)
    )

    if not matched:
        return CrossVerificationReport(
            document_a_id=doc_a.id,
            document_b_id=doc_b.id,
            document_a_filename=doc_a.filename,
            document_b_filename=doc_b.filename,
            supplier_name=ext_a.supplier_name or ext_b.supplier_name,
            invoice_number=ext_a.invoice_number or ext_b.invoice_number,
            matched=False,
            is_concordant=False,
            summary=(
                f"Documents did not match: Invoice # ('{ext_a.invoice_number}' vs '{ext_b.invoice_number}') "
                f"or Supplier ('{ext_a.supplier_name}' vs '{ext_b.supplier_name}')."
            ),
        )

    discrepancies: list[DiscrepancyItem] = []
    tol = settings.MATH_TOLERANCE

    # 1. Total comparison
    if not _amounts_match(ext_a.total, ext_b.total, tol):
        diff = abs(ext_a.total - ext_b.total) if (ext_a.total and ext_b.total) else None
        discrepancies.append(
            DiscrepancyItem(
                field="total",
                value_a=str(ext_a.total) if ext_a.total is not None else None,
                value_b=str(ext_b.total) if ext_b.total is not None else None,
                difference=str(diff) if diff is not None else "Missing in one document",
                severity="ERROR",
                message=f"Total amount mismatch: {doc_a.filename} has {ext_a.total}, but {doc_b.filename} has {ext_b.total}.",
            )
        )

    # 2. Subtotal comparison
    if not _amounts_match(ext_a.subtotal, ext_b.subtotal, tol):
        diff = abs(ext_a.subtotal - ext_b.subtotal) if (ext_a.subtotal and ext_b.subtotal) else None
        discrepancies.append(
            DiscrepancyItem(
                field="subtotal",
                value_a=str(ext_a.subtotal) if ext_a.subtotal is not None else None,
                value_b=str(ext_b.subtotal) if ext_b.subtotal is not None else None,
                difference=str(diff) if diff is not None else "Missing in one document",
                severity="ERROR",
                message=f"Subtotal mismatch: {doc_a.filename} has {ext_a.subtotal}, but {doc_b.filename} has {ext_b.subtotal}.",
            )
        )

    # 3. Tax comparison
    if not _amounts_match(ext_a.tax, ext_b.tax, tol):
        diff = abs(ext_a.tax - ext_b.tax) if (ext_a.tax and ext_b.tax) else None
        discrepancies.append(
            DiscrepancyItem(
                field="tax",
                value_a=str(ext_a.tax) if ext_a.tax is not None else None,
                value_b=str(ext_b.tax) if ext_b.tax is not None else None,
                difference=str(diff) if diff is not None else "Missing in one document",
                severity="WARNING",
                message=f"Tax amount mismatch: {doc_a.filename} has {ext_a.tax}, but {doc_b.filename} has {ext_b.tax}.",
            )
        )

    # 4. Invoice date comparison
    if ext_a.invoice_date and ext_b.invoice_date and ext_a.invoice_date != ext_b.invoice_date:
        discrepancies.append(
            DiscrepancyItem(
                field="invoice_date",
                value_a=str(ext_a.invoice_date),
                value_b=str(ext_b.invoice_date),
                severity="WARNING",
                message=f"Invoice date mismatch: {ext_a.invoice_date} vs {ext_b.invoice_date}.",
            )
        )

    # 5. Currency comparison
    if ext_a.currency and ext_b.currency and ext_a.currency.upper() != ext_b.currency.upper():
        discrepancies.append(
            DiscrepancyItem(
                field="currency",
                value_a=ext_a.currency,
                value_b=ext_b.currency,
                severity="ERROR",
                message=f"Currency mismatch: {ext_a.currency} vs {ext_b.currency}.",
            )
        )

    # 6. Line items comparison
    lines_a = ext_a.line_items
    lines_b = ext_b.line_items
    if lines_a and lines_b:
        if len(lines_a) != len(lines_b):
            discrepancies.append(
                DiscrepancyItem(
                    field="line_items_count",
                    value_a=len(lines_a),
                    value_b=len(lines_b),
                    severity="WARNING",
                    message=f"Line item count differs: {len(lines_a)} in {doc_a.filename} vs {len(lines_b)} in {doc_b.filename}.",
                )
            )

        # Compare pairwise items by index
        min_len = min(len(lines_a), len(lines_b))
        for idx in range(min_len):
            item_a = lines_a[idx]
            item_b = lines_b[idx]
            if not _amounts_match(item_a.line_total, item_b.line_total, tol):
                discrepancies.append(
                    DiscrepancyItem(
                        field=f"line_items[{idx}].line_total",
                        value_a=str(item_a.line_total),
                        value_b=str(item_b.line_total),
                        severity="ERROR",
                        message=(
                            f"Line item {idx + 1} total mismatch: '{item_a.description}' ({item_a.line_total}) vs "
                            f"'{item_b.description}' ({item_b.line_total})."
                        ),
                    )
                )

    is_concordant = len(discrepancies) == 0
    summary = (
        "Documents are fully concordant. All verified financial figures and dates match."
        if is_concordant
        else f"Reconciliation detected {len(discrepancies)} discrepancies between {doc_a.filename} and {doc_b.filename}."
    )

    return CrossVerificationReport(
        document_a_id=doc_a.id,
        document_b_id=doc_b.id,
        document_a_filename=doc_a.filename,
        document_b_filename=doc_b.filename,
        supplier_name=ext_a.supplier_name or ext_b.supplier_name,
        invoice_number=ext_a.invoice_number or ext_b.invoice_number,
        matched=True,
        is_concordant=is_concordant,
        discrepancies=discrepancies,
        summary=summary,
    )


async def find_and_verify_counterparts(
    document_id: UUID,
    db: AsyncSession,
) -> list[CrossVerificationReport]:
    """Find other documents in the database that share the same invoice number / supplier, and reconcile them."""
    stmt_target = (
        select(Document)
        .options(selectinload(Document.extractions))
        .where(Document.id == document_id)
    )
    target_doc = (await db.execute(stmt_target)).scalar_one_or_none()
    if not target_doc or not target_doc.extractions:
        return []

    target_ext = target_doc.extractions[0]
    inv_num = target_ext.invoice_number
    if not inv_num:
        return []

    # Query other documents with matching invoice number
    stmt_candidates = select(Extraction).where(
        Extraction.document_id != document_id,
        Extraction.invoice_number == inv_num,
    )
    candidates = (await db.execute(stmt_candidates)).scalars().all()

    reports: list[CrossVerificationReport] = []
    seen_docs: set[UUID] = set()

    for cand in candidates:
        if cand.document_id in seen_docs:
            continue
        seen_docs.add(cand.document_id)
        report = await verify_document_pair(document_id, cand.document_id, db)
        reports.append(report)

    return reports
