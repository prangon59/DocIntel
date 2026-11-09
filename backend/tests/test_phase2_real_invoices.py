"""Tests specifically verifying the user's Phase 2 real invoice acceptance criteria:

1. Upload the digital PDF and check the result endpoint: fields filled with confidence scores.
2. Test invoice where subtotal + tax != total: flagged needs_review.
3. Upload the same invoice twice: confirm duplicate flag appears.
4. Check that a missing field comes back as null, not an invented value.
"""

import shutil
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.schemas.extraction import (
    DateEvidence,
    DecimalEvidence,
    ExtractedLineItem,
    InvoiceExtractionSchema,
    SpreadsheetColumnMapping,
    StringEvidence,
)
from app.services.extraction import set_llm_client
from app.services.extraction.client import LLMClient
from app.services.ingest.pipeline import process_document_sync

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class ControlledMockLLMClient(LLMClient):
    """Configurable mock LLMClient for testing extraction scenarios."""

    def __init__(self, response_builder=None):
        self.response_builder = response_builder

    async def extract_invoice(self, text: str) -> InvoiceExtractionSchema:
        if self.response_builder:
            return self.response_builder(text)
        return InvoiceExtractionSchema()

    async def map_spreadsheet_columns(self, headers: list[str]) -> SpreadsheetColumnMapping:
        return SpreadsheetColumnMapping()


@pytest.mark.asyncio
async def test_criterion_1_and_4_digital_pdf_result_and_null_missing_field(
    db_session: AsyncSession, async_client: AsyncClient, tmp_path: Path
):
    """Criterion 1: Upload digital PDF and check result endpoint. Fields have confidence scores.
    Criterion 4: Check that a missing field (e.g. customer_name, po_number) comes back as null,
    not an invented value.
    """
    test_file = tmp_path / "digital_invoice.pdf"
    shutil.copy(FIXTURES_DIR / "digital_invoice.pdf", test_file)

    def mock_extraction(text: str) -> InvoiceExtractionSchema:
        return InvoiceExtractionSchema(
            invoice_number=StringEvidence(
                value="INV-2024-001", confidence=0.98, source_snippet="INV-2024-001"
            ),
            supplier_name=StringEvidence(
                value="Acme Industrial Supplies Ltd",
                confidence=0.96,
                source_snippet="Acme Industrial Supplies Ltd",
            ),
            customer_name=None,  # Missing field in extraction: must be null, not fabricated
            invoice_date=DateEvidence(
                value="2024-05-15", confidence=0.95, source_snippet="2024-05-15"
            ),
            subtotal=DecimalEvidence(
                value=Decimal("500.00"), confidence=0.97, source_snippet="500.00"
            ),
            tax=DecimalEvidence(value=Decimal("50.00"), confidence=0.95, source_snippet="50.00"),
            total=DecimalEvidence(
                value=Decimal("550.00"), confidence=0.99, source_snippet="550.00"
            ),
            currency=StringEvidence(value="USD", confidence=0.99, source_snippet="USD"),
            line_items=[
                ExtractedLineItem(
                    description=StringEvidence(
                        value="Heavy Duty Widget A",
                        confidence=0.92,
                        source_snippet="Heavy Duty Widget A",
                    ),
                    quantity=DecimalEvidence(
                        value=Decimal("10.00"), confidence=0.95, source_snippet="10"
                    ),
                    unit_price=DecimalEvidence(
                        value=Decimal("25.00"), confidence=0.95, source_snippet="25.00"
                    ),
                    line_total=DecimalEvidence(
                        value=Decimal("250.00"), confidence=0.98, source_snippet="250.00"
                    ),
                ),
                ExtractedLineItem(
                    description=StringEvidence(
                        value="Precision Gadget B",
                        confidence=0.92,
                        source_snippet="Precision Gadget B",
                    ),
                    quantity=DecimalEvidence(
                        value=Decimal("2.00"), confidence=0.95, source_snippet="2"
                    ),
                    unit_price=DecimalEvidence(
                        value=Decimal("125.00"), confidence=0.95, source_snippet="125.00"
                    ),
                    line_total=DecimalEvidence(
                        value=Decimal("250.00"), confidence=0.98, source_snippet="250.00"
                    ),
                ),
            ],
            overall_confidence=0.96,
        )

    set_llm_client(ControlledMockLLMClient(mock_extraction))

    doc = Document(
        id=uuid.uuid4(),
        filename="digital_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file.stat().st_size,
        file_hash="hash_pdf_real_1",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    # Process pipeline
    await process_document_sync(doc.id, db_session)

    # Query result endpoint
    resp = await async_client.get(f"/api/v1/documents/{doc.id}/result")
    assert resp.status_code == 200
    data = resp.json()

    # Verify fields are filled with confidence scores
    ext = data["extraction"]
    assert ext["invoice_number"] == "INV-2024-001"
    assert ext["supplier_name"] == "Acme Industrial Supplies Ltd"
    assert ext["confidence_scores"]["invoice_number"] == 0.98
    assert ext["confidence_scores"]["total"] == 0.99
    assert Decimal(str(ext["total"])) == Decimal("550.00")
    assert len(ext["line_items"]) == 2
    assert Decimal(str(ext["line_items"][0]["line_total"])) == Decimal("250.00")

    # Criterion 4: Missing field comes back as null, NOT an invented value
    assert ext["customer_name"] is None

    # Reset LLM client
    set_llm_client(None)


@pytest.mark.asyncio
async def test_criterion_2_math_mismatch_flags_needs_review(
    db_session: AsyncSession, async_client: AsyncClient, tmp_path: Path
):
    """Criterion 2: Test invoice where subtotal + tax != total is flagged needs_review."""
    test_file = tmp_path / "digital_invoice.pdf"
    shutil.copy(FIXTURES_DIR / "digital_invoice.pdf", test_file)

    def math_mismatch_extraction(text: str) -> InvoiceExtractionSchema:
        return InvoiceExtractionSchema(
            invoice_number=StringEvidence(
                value="INV-2024-001", confidence=0.98, source_snippet="INV-2024-001"
            ),
            supplier_name=StringEvidence(
                value="Acme Industrial Supplies Ltd",
                confidence=0.96,
                source_snippet="Acme Industrial Supplies Ltd",
            ),
            invoice_date=DateEvidence(
                value="2024-05-15", confidence=0.95, source_snippet="2024-05-15"
            ),
            subtotal=DecimalEvidence(
                value=Decimal("500.00"), confidence=0.95, source_snippet="500.00"
            ),
            tax=DecimalEvidence(value=Decimal("50.00"), confidence=0.95, source_snippet="50.00"),
            total=DecimalEvidence(
                value=Decimal("600.00"), confidence=0.95
            ),  # 500 + 50 != 600! Math mismatch!
            currency=StringEvidence(value="USD", confidence=0.95, source_snippet="USD"),
            line_items=[],
            overall_confidence=0.95,
        )

    set_llm_client(ControlledMockLLMClient(math_mismatch_extraction))

    doc = Document(
        id=uuid.uuid4(),
        filename="math_error_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file.stat().st_size,
        file_hash="hash_math_err",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    await process_document_sync(doc.id, db_session)

    resp = await async_client.get(f"/api/v1/documents/{doc.id}/result")
    assert resp.status_code == 200
    data = resp.json()

    # Flagged needs_review
    assert data["needs_review"] is True
    # Validation issues contain MATH_MISMATCH_TOTAL
    issue_codes = [i["code"] for i in data["validation_issues"]]
    assert "MATH_MISMATCH_TOTAL" in issue_codes

    set_llm_client(None)


@pytest.mark.asyncio
async def test_criterion_3_upload_same_invoice_twice_detects_duplicate(
    db_session: AsyncSession, async_client: AsyncClient, tmp_path: Path
):
    """Criterion 3: Upload the same invoice twice and confirm the duplicate flag appears."""
    test_file1 = tmp_path / "invoice_first.pdf"
    test_file2 = tmp_path / "invoice_second.pdf"
    shutil.copy(FIXTURES_DIR / "digital_invoice.pdf", test_file1)
    shutil.copy(FIXTURES_DIR / "digital_invoice.pdf", test_file2)

    def standard_extraction(text: str) -> InvoiceExtractionSchema:
        return InvoiceExtractionSchema(
            invoice_number=StringEvidence(
                value="INV-2024-001", confidence=0.98, source_snippet="INV-2024-001"
            ),
            supplier_name=StringEvidence(
                value="Acme Industrial Supplies Ltd",
                confidence=0.96,
                source_snippet="Acme Industrial Supplies Ltd",
            ),
            invoice_date=DateEvidence(
                value="2024-05-15", confidence=0.95, source_snippet="2024-05-15"
            ),
            subtotal=DecimalEvidence(
                value=Decimal("500.00"), confidence=0.97, source_snippet="500.00"
            ),
            tax=DecimalEvidence(value=Decimal("50.00"), confidence=0.95, source_snippet="50.00"),
            total=DecimalEvidence(
                value=Decimal("550.00"), confidence=0.99, source_snippet="550.00"
            ),
            currency=StringEvidence(value="USD", confidence=0.99, source_snippet="USD"),
            line_items=[
                ExtractedLineItem(
                    description=StringEvidence(
                        value="Heavy Duty Widget A",
                        confidence=0.92,
                        source_snippet="Heavy Duty Widget A",
                    ),
                    quantity=DecimalEvidence(
                        value=Decimal("10.00"), confidence=0.95, source_snippet="10"
                    ),
                    unit_price=DecimalEvidence(
                        value=Decimal("25.00"), confidence=0.95, source_snippet="25.00"
                    ),
                    line_total=DecimalEvidence(
                        value=Decimal("250.00"), confidence=0.98, source_snippet="250.00"
                    ),
                ),
                ExtractedLineItem(
                    description=StringEvidence(
                        value="Precision Gadget B",
                        confidence=0.92,
                        source_snippet="Precision Gadget B",
                    ),
                    quantity=DecimalEvidence(
                        value=Decimal("2.00"), confidence=0.95, source_snippet="2"
                    ),
                    unit_price=DecimalEvidence(
                        value=Decimal("125.00"), confidence=0.95, source_snippet="125.00"
                    ),
                    line_total=DecimalEvidence(
                        value=Decimal("250.00"), confidence=0.98, source_snippet="250.00"
                    ),
                ),
            ],
            overall_confidence=0.96,
        )

    set_llm_client(ControlledMockLLMClient(standard_extraction))

    # First invoice upload & process
    doc1 = Document(
        id=uuid.uuid4(),
        filename="invoice_first.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file1.stat().st_size,
        file_hash="hash_dup_1",
        storage_path=str(test_file1),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc1)
    await db_session.commit()
    await process_document_sync(doc1.id, db_session)

    resp1 = await async_client.get(f"/api/v1/documents/{doc1.id}/result")
    data1 = resp1.json()
    assert data1["needs_review"] is False

    # Second invoice upload & process (same supplier & invoice number)
    doc2 = Document(
        id=uuid.uuid4(),
        filename="invoice_second.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file2.stat().st_size,
        file_hash="hash_dup_2",
        storage_path=str(test_file2),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc2)
    await db_session.commit()
    await process_document_sync(doc2.id, db_session)

    resp2 = await async_client.get(f"/api/v1/documents/{doc2.id}/result")
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Second invoice must be flagged needs_review with duplicate issue
    assert data2["needs_review"] is True
    issue_codes = [i["code"] for i in data2["validation_issues"]]
    assert "DUPLICATE_INVOICE_EXACT" in issue_codes

    set_llm_client(None)
