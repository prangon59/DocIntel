"""Unit tests for the end-to-end ingestion pipeline across document types."""

import shutil
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.event import ProcessingEvent
from app.models.page import Page
from app.services.ingest.pipeline import process_document_sync

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_pipeline_digital_pdf(db_session: AsyncSession, tmp_path: Path):
    # Copy fixture to temp storage
    test_file = tmp_path / "digital_invoice.pdf"
    shutil.copy(FIXTURES_DIR / "digital_invoice.pdf", test_file)

    doc = Document(
        id=uuid.uuid4(),
        filename="digital_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file.stat().st_size,
        file_hash="hash123",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    processed_doc = await process_document_sync(doc.id, db_session)
    assert processed_doc.status == DocumentStatus.COMPLETED
    assert processed_doc.page_count == 1
    assert processed_doc.error_message is None

    # Verify pages saved in DB
    pages = (
        (await db_session.execute(select(Page).where(Page.document_id == doc.id))).scalars().all()
    )
    assert len(pages) == 1
    assert "INV-2024-001" in pages[0].raw_text
    assert pages[0].extraction_method == "digital_pdf"

    # Verify processing event
    events = (
        (
            await db_session.execute(
                select(ProcessingEvent).where(ProcessingEvent.document_id == doc.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(events) >= 1
    stages = [e.stage for e in events]
    assert "INGESTION" in stages
    assert events[0].status == "SUCCESS"


@pytest.mark.asyncio
async def test_pipeline_scanned_image(db_session: AsyncSession, tmp_path: Path):
    test_file = tmp_path / "scanned_invoice.png"
    shutil.copy(FIXTURES_DIR / "scanned_invoice.png", test_file)

    doc = Document(
        id=uuid.uuid4(),
        filename="scanned_invoice.png",
        file_type="png",
        mime_type="image/png",
        file_size=test_file.stat().st_size,
        file_hash="hash456",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    processed_doc = await process_document_sync(doc.id, db_session)
    assert processed_doc.status == DocumentStatus.COMPLETED
    assert processed_doc.page_count == 1

    pages = (
        (await db_session.execute(select(Page).where(Page.document_id == doc.id))).scalars().all()
    )
    assert len(pages) == 1
    assert pages[0].extraction_method == "tesseract_ocr"


@pytest.mark.asyncio
async def test_pipeline_multisheet_xlsx(db_session: AsyncSession, tmp_path: Path):
    test_file = tmp_path / "multi_sheet_invoices.xlsx"
    shutil.copy(FIXTURES_DIR / "multi_sheet_invoices.xlsx", test_file)

    doc = Document(
        id=uuid.uuid4(),
        filename="multi_sheet_invoices.xlsx",
        file_type="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=test_file.stat().st_size,
        file_hash="hash789",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    processed_doc = await process_document_sync(doc.id, db_session)
    assert processed_doc.status == DocumentStatus.COMPLETED
    assert processed_doc.page_count == 2

    pages = (
        (await db_session.execute(select(Page).where(Page.document_id == doc.id))).scalars().all()
    )
    assert len(pages) == 2
    assert any("Vendor Invoices" in p.raw_text for p in pages)
    assert any("Line Item Details" in p.raw_text for p in pages)


@pytest.mark.asyncio
async def test_pipeline_corrupted_file_never_crashes_batch(
    db_session: AsyncSession, tmp_path: Path
):
    test_file = tmp_path / "corrupted.pdf"
    shutil.copy(FIXTURES_DIR / "corrupted.pdf", test_file)

    doc = Document(
        id=uuid.uuid4(),
        filename="corrupted.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=test_file.stat().st_size,
        file_hash="hash_corrupt",
        storage_path=str(test_file),
        status=DocumentStatus.PENDING,
    )
    db_session.add(doc)
    await db_session.commit()

    # Must complete gracefully without raising unhandled exception
    processed_doc = await process_document_sync(doc.id, db_session)
    assert processed_doc.status == DocumentStatus.FAILED
    assert processed_doc.error_message is not None

    events = (
        (
            await db_session.execute(
                select(ProcessingEvent).where(ProcessingEvent.document_id == doc.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].status == "FAILED"
