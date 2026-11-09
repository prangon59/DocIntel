"""Unit and integration tests for document and failed job reprocessing."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus


@pytest.fixture
async def seed_reprocess_documents(db_session: AsyncSession):
    # Failed document 1
    doc_failed1 = Document(
        id=uuid.uuid4(),
        filename="corrupted_file.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=500,
        file_hash="hash_f1",
        storage_path="path_f1",
        status=DocumentStatus.FAILED,
        error_message="Corrupted header",
    )
    # Failed document 2
    doc_failed2 = Document(
        id=uuid.uuid4(),
        filename="broken_image.png",
        file_type="png",
        mime_type="image/png",
        file_size=600,
        file_hash="hash_f2",
        storage_path="path_f2",
        status=DocumentStatus.FAILED,
        error_message="OCR timeout",
    )
    # Completed document
    doc_completed = Document(
        id=uuid.uuid4(),
        filename="completed_doc.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=700,
        file_hash="hash_c1",
        storage_path="path_c1",
        status=DocumentStatus.COMPLETED,
    )

    db_session.add_all([doc_failed1, doc_failed2, doc_completed])
    await db_session.commit()
    return doc_failed1, doc_failed2, doc_completed


@pytest.mark.asyncio
async def test_reprocess_single_document(
    async_client: AsyncClient, db_session: AsyncSession, seed_reprocess_documents
):
    doc_failed1, _, _ = seed_reprocess_documents

    response = await async_client.post(f"/api/v1/documents/{doc_failed1.id}/reprocess")
    assert response.status_code == 202
    data = response.json()
    assert data["document_id"] == str(doc_failed1.id)
    assert data["status"] == DocumentStatus.PENDING.value

    # Verify status in DB updated to PENDING
    refreshed = (
        await db_session.execute(
            select(Document).where(Document.id == doc_failed1.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed is not None
    assert refreshed.status == DocumentStatus.PENDING
    assert refreshed.error_message is None


@pytest.mark.asyncio
async def test_reprocess_nonexistent_document_raises_404(async_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await async_client.post(f"/api/v1/documents/{random_id}/reprocess")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reprocess_failed_jobs(
    async_client: AsyncClient, db_session: AsyncSession, seed_reprocess_documents
):
    doc_failed1, doc_failed2, doc_completed = seed_reprocess_documents

    response = await async_client.post("/api/v1/jobs/reprocess-failed")
    assert response.status_code == 202
    data = response.json()
    assert data["reprocessed_count"] == 2
    assert str(doc_failed1.id) in data["document_ids"]
    assert str(doc_failed2.id) in data["document_ids"]
    assert str(doc_completed.id) not in data["document_ids"]

    # Verify both failed docs reset to PENDING
    d1 = (
        await db_session.execute(
            select(Document).where(Document.id == doc_failed1.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    d2 = (
        await db_session.execute(
            select(Document).where(Document.id == doc_failed2.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    d_c = (
        await db_session.execute(
            select(Document).where(Document.id == doc_completed.id).execution_options(populate_existing=True)
        )
    ).scalar_one()

    assert d1.status == DocumentStatus.PENDING
    assert d2.status == DocumentStatus.PENDING
    assert d_c.status == DocumentStatus.COMPLETED  # Unchanged
