"""Unit and integration tests for cross-document verification (PDF <-> PDF, PDF <-> Excel)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.extraction import Extraction, LineItem
from app.services.verification.cross_verifier import (
    find_and_verify_counterparts,
    verify_document_pair,
)


@pytest.fixture
async def seed_crossverify_pair(db_session: AsyncSession):
    # Document 1: PDF invoice from supplier
    doc_pdf = Document(
        id=uuid.uuid4(),
        filename="invoice_vendor.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        file_hash="hash_pdf_xv",
        storage_path="path_pdf",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(doc_pdf)
    await db_session.flush()

    ext_pdf = Extraction(
        id=uuid.uuid4(),
        document_id=doc_pdf.id,
        invoice_number="INV-XV-99",
        supplier_name="Global Steel Works Inc",
        invoice_date=date(2024, 7, 1),
        subtotal=Decimal("2000.00"),
        tax=Decimal("200.00"),
        total=Decimal("2200.00"),
        currency="USD",
    )
    db_session.add(ext_pdf)

    li_pdf = LineItem(
        id=uuid.uuid4(),
        extraction_id=ext_pdf.id,
        description="Steel Beams Type A",
        quantity=Decimal("20.00"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("2000.00"),
    )
    db_session.add(li_pdf)

    # Document 2: Matching Excel record with matching values
    doc_excel = Document(
        id=uuid.uuid4(),
        filename="accounting_ledger.xlsx",
        file_type="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=2048,
        file_hash="hash_xlsx_xv",
        storage_path="path_xlsx",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(doc_excel)
    await db_session.flush()

    ext_excel = Extraction(
        id=uuid.uuid4(),
        document_id=doc_excel.id,
        invoice_number="INV-XV-99",
        supplier_name="Global Steel Works",
        invoice_date=date(2024, 7, 1),
        subtotal=Decimal("2000.00"),
        tax=Decimal("200.00"),
        total=Decimal("2200.00"),
        currency="USD",
    )
    db_session.add(ext_excel)

    li_excel = LineItem(
        id=uuid.uuid4(),
        extraction_id=ext_excel.id,
        description="Steel Beams Type A",
        quantity=Decimal("20.00"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("2000.00"),
    )
    db_session.add(li_excel)

    await db_session.commit()
    return doc_pdf, doc_excel, ext_pdf, ext_excel


@pytest.mark.asyncio
async def test_cross_verify_concordant_pair(db_session: AsyncSession, seed_crossverify_pair):
    doc_pdf, doc_excel, _, _ = seed_crossverify_pair

    report = await verify_document_pair(doc_pdf.id, doc_excel.id, db_session)
    assert report.matched is True
    assert report.is_concordant is True
    assert len(report.discrepancies) == 0
    assert "concordant" in report.summary.lower()


@pytest.mark.asyncio
async def test_cross_verify_mismatched_amounts(db_session: AsyncSession, seed_crossverify_pair):
    doc_pdf, doc_excel, _, ext_excel = seed_crossverify_pair

    # Introduce a discrepancy in the Excel ledger total (e.g. 2150.00 instead of 2200.00)
    ext_excel.total = Decimal("2150.00")
    await db_session.commit()

    report = await verify_document_pair(doc_pdf.id, doc_excel.id, db_session)
    assert report.matched is True
    assert report.is_concordant is False
    assert len(report.discrepancies) == 1
    assert report.discrepancies[0].field == "total"
    assert "2200.00" in report.discrepancies[0].message
    assert "2150.00" in report.discrepancies[0].message


@pytest.mark.asyncio
async def test_cross_verify_unmatched_pair(db_session: AsyncSession, seed_crossverify_pair):
    doc_pdf, doc_excel, _, ext_excel = seed_crossverify_pair

    # Change invoice number and supplier on doc_excel so they do not match
    ext_excel.invoice_number = "INV-DIFFERENT"
    ext_excel.supplier_name = "Unrelated Vendor"
    await db_session.commit()

    report = await verify_document_pair(doc_pdf.id, doc_excel.id, db_session)
    assert report.matched is False
    assert report.is_concordant is False


@pytest.mark.asyncio
async def test_find_and_verify_counterparts(db_session: AsyncSession, seed_crossverify_pair):
    doc_pdf, doc_excel, _, _ = seed_crossverify_pair

    reports = await find_and_verify_counterparts(doc_pdf.id, db_session)
    assert len(reports) == 1
    assert reports[0].document_b_id == doc_excel.id
    assert reports[0].matched is True


@pytest.mark.asyncio
async def test_cross_verify_endpoints(async_client: AsyncClient, seed_crossverify_pair):
    doc_pdf, doc_excel, _, _ = seed_crossverify_pair

    # POST /api/v1/crossverify
    post_resp = await async_client.post(
        "/api/v1/crossverify",
        json={"document_id_a": str(doc_pdf.id), "document_id_b": str(doc_excel.id)},
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["matched"] is True
    assert data["is_concordant"] is True

    # GET /api/v1/documents/{id}/crossverify
    get_resp = await async_client.get(f"/api/v1/documents/{doc_pdf.id}/crossverify")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert len(get_data) == 1
    assert get_data[0]["document_b_id"] == str(doc_excel.id)
