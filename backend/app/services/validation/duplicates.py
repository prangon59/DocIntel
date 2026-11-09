"""Duplicate invoice detection engine supporting exact and Rapidfuzz fuzzy matching."""

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.extraction import Extraction
from app.models.validation import IssueSeverity
from app.schemas.extraction import InvoiceExtractionSchema


class ValidationIssueData(BaseModel):
    """Container for detected validation anomalies."""

    code: str
    severity: IssueSeverity
    field: str
    message: str
    details: dict[str, Any] = {}


async def detect_duplicate_invoices(
    extraction: InvoiceExtractionSchema,
    current_document_id: uuid.UUID,
    db: AsyncSession,
) -> list[ValidationIssueData]:
    """Scan database for exact or fuzzy duplicate invoices.

    Rules:
    - Exact duplicate: Same supplier_name (normalized) and same invoice_number.
    - Fuzzy duplicate: Rapidfuzz token_sort_ratio >= 85 on supplier name, combined with identical total and date.

    Args:
        extraction: Extracted invoice data under test.
        current_document_id: UUID of the current document (to exclude self-match).
        db: Active Async SQLAlchemy session.

    Returns:
        List of duplicate ValidationIssueData items.
    """
    issues: list[ValidationIssueData] = []

    inv_num = extraction.invoice_number.value if extraction.invoice_number else None
    supplier = extraction.supplier_name.value if extraction.supplier_name else None
    inv_date = extraction.invoice_date.as_date() if extraction.invoice_date else None
    total_val = extraction.total.value if extraction.total else None

    # If key identifiers are missing, skip duplicate check
    if not inv_num and not (supplier and total_val):
        return issues

    # Query existing extractions
    stmt = select(Extraction).where(Extraction.document_id != current_document_id)
    result = await db.execute(stmt)
    existing_records = result.scalars().all()

    for existing in existing_records:
        ex_supplier = existing.supplier_name or ""
        ex_inv_num = existing.invoice_number or ""
        ex_total = existing.total
        ex_date = existing.invoice_date

        # 1. Exact Duplicate: (supplier_name, invoice_number)
        if (
            inv_num
            and ex_inv_num
            and inv_num.strip().lower() == ex_inv_num.strip().lower()
            and supplier
            and ex_supplier
            and supplier.strip().lower() == ex_supplier.strip().lower()
        ):
            issues.append(
                ValidationIssueData(
                    code="DUPLICATE_INVOICE_EXACT",
                    severity=IssueSeverity.ERROR,
                    field="invoice_number",
                    message=(
                        f"Exact duplicate invoice detected: Invoice '{inv_num}' from supplier '{supplier}' "
                        f"already exists in document {existing.document_id}."
                    ),
                    details={
                        "matched_document_id": str(existing.document_id),
                        "invoice_number": inv_num,
                        "supplier": supplier,
                    },
                )
            )
            continue  # Avoid duplicate fuzzy flag if exact match found

        # 2. Fuzzy Duplicate: Rapidfuzz match on supplier + identical total + identical date
        if (
            supplier
            and ex_supplier
            and total_val is not None
            and ex_total is not None
            and inv_date
            and ex_date
        ):
            supplier_score = max(
                fuzz.token_sort_ratio(supplier.lower(), ex_supplier.lower()),
                fuzz.token_set_ratio(supplier.lower(), ex_supplier.lower()),
            )
            is_same_total = (
                abs(Decimal(str(total_val)) - Decimal(str(ex_total))) <= settings.MATH_TOLERANCE
            )
            is_same_date = inv_date == ex_date

            if supplier_score >= 80 and is_same_total and is_same_date:
                issues.append(
                    ValidationIssueData(
                        code="DUPLICATE_INVOICE_FUZZY",
                        severity=IssueSeverity.ERROR,
                        field="supplier_name",
                        message=(
                            f"Fuzzy duplicate invoice detected: Supplier '{supplier}' matches '{ex_supplier}' "
                            f"(similarity {supplier_score}%) with identical total {total_val} and date {inv_date}."
                        ),
                        details={
                            "matched_document_id": str(existing.document_id),
                            "similarity_score": supplier_score,
                            "supplier": supplier,
                            "existing_supplier": ex_supplier,
                            "total": str(total_val),
                            "date": str(inv_date),
                        },
                    )
                )

    return issues
