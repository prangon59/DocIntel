"""Unit and integration tests for keyword, semantic, and hybrid search."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding
from app.models.extraction import Extraction
from app.models.page import Page
from app.schemas.search import SearchMode
from app.services.search.embedder import MockEmbedder, set_embedder
from app.services.search.service import search_documents


@pytest.fixture(autouse=True)
def mock_embedder_setup():
    embedder = MockEmbedder(dimensions=768)
    set_embedder(embedder)
    yield
    set_embedder(None)


@pytest.fixture
async def seed_search_data(db_session: AsyncSession):
    embedder = MockEmbedder(dimensions=768)

    # Document 1: Acme Corp invoice for cloud consulting
    doc1 = Document(
        id=uuid.uuid4(),
        filename="acme_cloud_invoice.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        file_hash="hash_s1",
        storage_path="path1",
        status=DocumentStatus.COMPLETED,
        needs_review=False,
    )
    db_session.add(doc1)
    await db_session.flush()

    p1 = Page(
        document_id=doc1.id,
        page_number=1,
        raw_text="Acme Cloud Solutions. Invoice INV-2024-ACME. Consulting services $1,500.00.",
        extraction_method="digital_pdf",
        ocr_confidence=1.0,
        char_count=80,
    )
    db_session.add(p1)

    ext1 = Extraction(
        document_id=doc1.id,
        invoice_number="INV-2024-ACME",
        supplier_name="Acme Cloud Solutions",
        invoice_date=date(2024, 2, 10),
        total=Decimal("1500.00"),
        subtotal=Decimal("1500.00"),
        currency="USD",
    )
    db_session.add(ext1)

    vec1 = await embedder.embed_text("Acme Cloud Solutions consulting services")
    emb1 = Embedding(
        document_id=doc1.id,
        chunk_text="Acme Cloud Solutions consulting services",
        embedding=vec1,
    )
    db_session.add(emb1)

    # Document 2: Global Logistics hardware shipment
    doc2 = Document(
        id=uuid.uuid4(),
        filename="hardware_shipment_log.xlsx",
        file_type="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=2048,
        file_hash="hash_s2",
        storage_path="path2",
        status=DocumentStatus.COMPLETED,
        needs_review=True,
    )
    db_session.add(doc2)
    await db_session.flush()

    p2 = Page(
        document_id=doc2.id,
        page_number=1,
        raw_text="Global Logistics Inc. Invoice LOG-9988. Heavy hardware freight $450.00.",
        extraction_method="xlsx_sheet",
        ocr_confidence=1.0,
        char_count=70,
    )
    db_session.add(p2)

    ext2 = Extraction(
        document_id=doc2.id,
        invoice_number="LOG-9988",
        supplier_name="Global Logistics Inc",
        invoice_date=date(2024, 6, 20),
        total=Decimal("450.00"),
        subtotal=Decimal("400.00"),
        currency="USD",
    )
    db_session.add(ext2)

    vec2 = await embedder.embed_text("Global Logistics heavy hardware freight shipping")
    emb2 = Embedding(
        document_id=doc2.id,
        chunk_text="Global Logistics heavy hardware freight shipping",
        embedding=vec2,
    )
    db_session.add(emb2)

    await db_session.commit()
    return doc1, doc2


@pytest.mark.asyncio
async def test_keyword_search_by_supplier(db_session: AsyncSession, seed_search_data):
    doc1, _ = seed_search_data
    resp = await search_documents(db=db_session, query="Acme", mode=SearchMode.KEYWORD)
    assert resp.total_hits >= 1
    assert resp.results[0].document_id == doc1.id
    assert resp.results[0].supplier_name == "Acme Cloud Solutions"
    assert resp.results[0].match_type == "keyword"


@pytest.mark.asyncio
async def test_keyword_search_by_invoice_number(db_session: AsyncSession, seed_search_data):
    _, doc2 = seed_search_data
    resp = await search_documents(db=db_session, query="LOG-9988", mode=SearchMode.KEYWORD)
    assert resp.total_hits == 1
    assert resp.results[0].document_id == doc2.id
    assert resp.results[0].invoice_number == "LOG-9988"


@pytest.mark.asyncio
async def test_semantic_search(db_session: AsyncSession, seed_search_data):
    doc1, _ = seed_search_data
    # Semantic search query with conceptual similarity
    resp = await search_documents(
        db=db_session,
        query="Acme Cloud Solutions consulting services",
        mode=SearchMode.SEMANTIC,
    )
    assert resp.total_hits >= 1
    assert resp.results[0].document_id == doc1.id
    assert resp.results[0].match_type == "semantic"
    assert resp.results[0].score > 0.9  # Identical text produces ~1.0 cosine similarity


@pytest.mark.asyncio
async def test_hybrid_search_rrf(db_session: AsyncSession, seed_search_data):
    doc1, _ = seed_search_data
    resp = await search_documents(
        db=db_session,
        query="Acme Cloud",
        mode=SearchMode.HYBRID,
    )
    assert resp.total_hits >= 1
    top = resp.results[0]
    assert top.document_id == doc1.id
    assert top.score > 0.0


@pytest.mark.asyncio
async def test_search_filters(db_session: AsyncSession, seed_search_data):
    # Filter by needs_review=True
    resp = await search_documents(
        db=db_session,
        query="",
        mode=SearchMode.KEYWORD,
        needs_review=True,
    )
    assert resp.total_hits == 1
    assert resp.results[0].needs_review is True

    # Filter by min_total=1000
    resp_total = await search_documents(
        db=db_session,
        query="",
        mode=SearchMode.KEYWORD,
        min_total=Decimal("1000.00"),
    )
    assert resp_total.total_hits == 1
    assert resp_total.results[0].total == Decimal("1500.00")


@pytest.mark.asyncio
async def test_search_endpoint(async_client: AsyncClient, seed_search_data):
    response = await async_client.get("/api/v1/search?q=Acme&mode=hybrid")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Acme"
    assert data["mode"] == "hybrid"
    assert len(data["results"]) >= 1
