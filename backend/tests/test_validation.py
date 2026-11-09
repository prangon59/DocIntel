"""Unit tests for deterministic validation engine and duplicate detection."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.extraction import Extraction
from app.models.validation import IssueSeverity
from app.schemas.extraction import (
    DateEvidence,
    DecimalEvidence,
    ExtractedLineItem,
    InvoiceExtractionSchema,
    StringEvidence,
)
from app.services.validation.duplicates import detect_duplicate_invoices
from app.services.validation.engine import validate_extracted_invoice


def _build_valid_extraction() -> InvoiceExtractionSchema:
    return InvoiceExtractionSchema(
        invoice_number=StringEvidence(value="INV-2024-001", confidence=0.95),
        supplier_name=StringEvidence(value="Acme Corp", confidence=0.95),
        customer_name=StringEvidence(value="Beta LLC", confidence=0.90),
        invoice_date=DateEvidence(value="2024-01-15", confidence=0.95),
        currency=StringEvidence(value="USD", confidence=0.99),
        subtotal=DecimalEvidence(value=Decimal("100.00"), confidence=0.95),
        tax=DecimalEvidence(value=Decimal("10.00"), confidence=0.95),
        total=DecimalEvidence(value=Decimal("110.00"), confidence=0.95),
        line_items=[
            ExtractedLineItem(
                description=StringEvidence(value="Item 1", confidence=0.9),
                quantity=DecimalEvidence(value=Decimal("2.00"), confidence=0.9),
                unit_price=DecimalEvidence(value=Decimal("50.00"), confidence=0.9),
                line_total=DecimalEvidence(value=Decimal("100.00"), confidence=0.9),
            )
        ],
        overall_confidence=0.95,
    )


def test_valid_invoice_passes_validation():
    extraction = _build_valid_extraction()
    report = validate_extracted_invoice(extraction)
    assert len(report.issues) == 0
    assert report.needs_review is False
    assert report.is_valid is True


def test_missing_required_fields():
    extraction = InvoiceExtractionSchema(
        invoice_number=StringEvidence(value=None),
        supplier_name=StringEvidence(value=None),
        total=DecimalEvidence(value=None),
    )
    report = validate_extracted_invoice(extraction)
    assert report.needs_review is True
    codes = [i.code for i in report.issues]
    assert "MISSING_INVOICE_NUMBER" in codes
    assert "MISSING_SUPPLIER_NAME" in codes
    assert "MISSING_TOTAL" in codes


def test_math_mismatch_total():
    """When subtotal + tax != total, flag MATH_MISMATCH_TOTAL and needs_review=True."""
    extraction = _build_valid_extraction()
    # Change total so 100.00 + 10.00 != 125.00
    extraction.total = DecimalEvidence(value=Decimal("125.00"), confidence=0.95)

    report = validate_extracted_invoice(extraction)
    assert report.needs_review is True
    math_issues = [i for i in report.issues if i.code == "MATH_MISMATCH_TOTAL"]
    assert len(math_issues) == 1
    assert "110.00" in math_issues[0].message
    assert "125.00" in math_issues[0].message


def test_math_tolerance_allows_small_rounding_delta():
    """A 1-cent rounding difference should pass when tolerance is 0.01."""
    extraction = _build_valid_extraction()
    # 100.00 + 10.00 = 110.00, total = 110.01 (diff = 0.01, within tolerance)
    extraction.total = DecimalEvidence(value=Decimal("110.01"), confidence=0.95)
    report = validate_extracted_invoice(extraction, tolerance=Decimal("0.01"))
    assert not any(i.code == "MATH_MISMATCH_TOTAL" for i in report.issues)


def test_math_mismatch_subtotal():
    """When sum of line items != subtotal, flag MATH_MISMATCH_SUBTOTAL."""
    extraction = _build_valid_extraction()
    # Line item is 100.00, but subtotal is 80.00
    extraction.subtotal = DecimalEvidence(value=Decimal("80.00"), confidence=0.95)
    extraction.total = DecimalEvidence(value=Decimal("90.00"), confidence=0.95)

    report = validate_extracted_invoice(extraction)
    assert any(i.code == "MATH_MISMATCH_SUBTOTAL" for i in report.issues)
    assert report.needs_review is True


def test_math_mismatch_line_item():
    """When qty * unit_price != line_total, flag MATH_MISMATCH_LINE_ITEM."""
    extraction = _build_valid_extraction()
    extraction.line_items[0].line_total = DecimalEvidence(value=Decimal("95.00"), confidence=0.9)

    report = validate_extracted_invoice(extraction)
    assert any(i.code == "MATH_MISMATCH_LINE_ITEM" for i in report.issues)


def test_negative_amounts():
    extraction = _build_valid_extraction()
    extraction.total = DecimalEvidence(value=Decimal("-50.00"), confidence=0.9)

    report = validate_extracted_invoice(extraction)
    assert any(i.code == "NEGATIVE_AMOUNT" for i in report.issues)
    assert report.needs_review is True


def test_low_confidence_flagged():
    extraction = _build_valid_extraction()
    extraction.overall_confidence = 0.50  # Below 0.70 threshold

    report = validate_extracted_invoice(extraction)
    assert any(i.code == "LOW_CONFIDENCE" for i in report.issues)
    assert report.needs_review is True


@pytest.mark.asyncio
async def test_exact_duplicate_detection(db_session: AsyncSession):
    from datetime import date
    # Existing invoice in database
    doc1 = Document(
        id=uuid.uuid4(),
        filename="first_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=100,
        file_hash="hash1",
        storage_path="path1",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(doc1)
    await db_session.flush()

    ext1 = Extraction(
        id=uuid.uuid4(),
        document_id=doc1.id,
        invoice_number="INV-2024-999",
        supplier_name="Global Tech Supplies",
        total=Decimal("500.00"),
        invoice_date=date(2024, 2, 1),
    )
    db_session.add(ext1)
    await db_session.commit()

    # Second document extraction with exact same supplier and invoice number
    doc2_id = uuid.uuid4()
    candidate = InvoiceExtractionSchema(
        invoice_number=StringEvidence(value="INV-2024-999"),
        supplier_name=StringEvidence(value="Global Tech Supplies"),
        invoice_date=DateEvidence(value="2024-02-01"),
        total=DecimalEvidence(value=Decimal("500.00")),
    )
    issues = await detect_duplicate_invoices(
        extraction=candidate,
        current_document_id=doc2_id,
        db=db_session,
    )
    assert len(issues) == 1
    assert issues[0].code == "DUPLICATE_INVOICE_EXACT"
    assert issues[0].severity == IssueSeverity.ERROR


@pytest.mark.asyncio
async def test_fuzzy_duplicate_detection(db_session: AsyncSession):
    from datetime import date
    # Existing invoice in database
    doc1 = Document(
        id=uuid.uuid4(),
        filename="first_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=100,
        file_hash="hash_orig",
        storage_path="path_orig",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(doc1)
    await db_session.flush()

    ext1 = Extraction(
        id=uuid.uuid4(),
        document_id=doc1.id,
        invoice_number="INV-FUZZY-A",
        supplier_name="Acme International Solutions LLC",
        total=Decimal("1250.00"),
        invoice_date=date(2024, 3, 1),
    )
    db_session.add(ext1)
    await db_session.commit()

    # Second document with slightly different supplier name, different invoice number, but same date and total
    doc2_id = uuid.uuid4()
    candidate = InvoiceExtractionSchema(
        invoice_number=StringEvidence(value="INV-FUZZY-B"),
        supplier_name=StringEvidence(value="Acme Intl Solutions LLC"),
        invoice_date=DateEvidence(value="2024-03-01"),
        total=DecimalEvidence(value=Decimal("1250.00")),
    )
    issues = await detect_duplicate_invoices(
        extraction=candidate,
        current_document_id=doc2_id,
        db=db_session,
    )
    assert len(issues) == 1
    assert issues[0].code == "DUPLICATE_INVOICE_FUZZY"
    assert issues[0].severity == IssueSeverity.ERROR
