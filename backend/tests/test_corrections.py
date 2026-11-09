"""Unit and integration tests for manual corrections, audit trail, and automatic re-validation."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correction import Correction
from app.models.document import Document, DocumentStatus
from app.models.extraction import Extraction, LineItem
from app.models.validation import IssueSeverity, ValidationIssue
from app.schemas.correction import CorrectionPayload, LineItemCorrection
from app.services.correction.service import apply_manual_correction


@pytest.fixture
async def sample_invoice_with_math_error(db_session: AsyncSession):
    doc = Document(
        id=uuid.uuid4(),
        filename="error_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        file_hash="hash_err_1",
        storage_path="path_err",
        status=DocumentStatus.COMPLETED,
        needs_review=True,
    )
    db_session.add(doc)
    await db_session.flush()

    ext = Extraction(
        id=uuid.uuid4(),
        document_id=doc.id,
        invoice_number="INV-ERR-001",
        supplier_name="Apex Corp",
        invoice_date=date(2024, 4, 1),
        subtotal=Decimal("100.00"),
        tax=Decimal("10.00"),
        total=Decimal("150.00"),  # Error: 100 + 10 != 150
        currency="USD",
        overall_confidence=0.95,
    )
    db_session.add(ext)

    li = LineItem(
        id=uuid.uuid4(),
        extraction_id=ext.id,
        description="Consulting Hour",
        quantity=Decimal("1.00"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
        confidence=1.0,
    )
    db_session.add(li)

    # Initial validation issue
    issue = ValidationIssue(
        document_id=doc.id,
        code="MATH_MISMATCH_TOTAL",
        severity=IssueSeverity.ERROR,
        field="total",
        message="Subtotal (100.00) + Tax (10.00) != Total (150.00)",
        details={},
    )
    db_session.add(issue)
    await db_session.commit()

    return doc, ext, li


@pytest.mark.asyncio
async def test_manual_correction_fixes_math_and_clears_needs_review(
    db_session: AsyncSession, sample_invoice_with_math_error
):
    doc, ext, _ = sample_invoice_with_math_error

    # Reviewer corrects total from 150.00 to 110.00
    payload = CorrectionPayload(
        total=Decimal("110.00"),
        reason="Corrected OCR misread of grand total",
        updated_by="reviewer@company.com",
    )

    result = await apply_manual_correction(doc.id, payload, db_session)

    # Verify updated extraction
    assert result["extraction"]["total"] == "110.00"

    # Crucial: Validation re-ran automatically; math mismatch is gone and needs_review is False
    assert result["needs_review"] is False
    issue_codes = [i["code"] for i in result["validation_issues"]]
    assert "MATH_MISMATCH_TOTAL" not in issue_codes

    # Verify audit trail record was saved to DB
    corrections = (
        (await db_session.execute(select(Correction).where(Correction.document_id == doc.id)))
        .scalars()
        .all()
    )
    assert len(corrections) == 1
    assert corrections[0].field_name == "total"
    assert corrections[0].old_value == "150.00"
    assert corrections[0].new_value == "110.00"
    assert corrections[0].reason == "Corrected OCR misread of grand total"
    assert corrections[0].updated_by == "reviewer@company.com"


@pytest.mark.asyncio
async def test_manual_correction_line_items(
    db_session: AsyncSession, sample_invoice_with_math_error
):
    doc, _, li = sample_invoice_with_math_error

    payload = CorrectionPayload(
        total=Decimal("110.00"),
        line_items=[
            LineItemCorrection(
                id=li.id,
                description="Senior Consulting Hour",
            )
        ],
        reason="Updated line item description to be more specific",
    )

    result = await apply_manual_correction(doc.id, payload, db_session)
    assert result["extraction"]["line_items"][0]["description"] == "Senior Consulting Hour"

    # Audit trail tracks line item change
    corrections = (
        (await db_session.execute(select(Correction).where(Correction.document_id == doc.id)))
        .scalars()
        .all()
    )
    corr_fields = [c.field_name for c in corrections]
    assert any(f"line_item[{li.id}].description" in f for f in corr_fields)


@pytest.mark.asyncio
async def test_patch_document_result_endpoint(
    async_client: AsyncClient, sample_invoice_with_math_error
):
    doc, _, _ = sample_invoice_with_math_error

    response = await async_client.patch(
        f"/api/v1/documents/{doc.id}/result",
        json={
            "total": "110.00",
            "reason": "API test correction",
            "updated_by": "qa_tester",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["needs_review"] is False
    assert data["extraction"]["total"] == "110.00"
    assert len(data["audit_trail"]) >= 1


@pytest.mark.asyncio
async def test_correction_nonexistent_document_raises_404(async_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await async_client.patch(
        f"/api/v1/documents/{random_id}/result",
        json={"total": "100.00"},
    )
    assert response.status_code == 404
