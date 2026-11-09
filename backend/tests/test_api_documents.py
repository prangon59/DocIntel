"""Integration tests for Document upload and management REST API endpoints."""

from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_upload_single_document(async_client: AsyncClient):
    pdf_bytes = (FIXTURES_DIR / "digital_invoice.pdf").read_bytes()
    files = {"files": ("digital_invoice.pdf", pdf_bytes, "application/pdf")}

    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 1
    assert len(data["uploaded"]) == 1
    item = data["uploaded"][0]
    assert item["status"] == "PENDING"
    assert "id" in item


@pytest.mark.asyncio
async def test_upload_multiple_documents(async_client: AsyncClient):
    pdf_bytes = (FIXTURES_DIR / "digital_invoice.pdf").read_bytes()
    png_bytes = (FIXTURES_DIR / "scanned_invoice.png").read_bytes()
    csv_bytes = (FIXTURES_DIR / "invoices.csv").read_bytes()

    files = [
        ("files", ("invoice.pdf", pdf_bytes, "application/pdf")),
        ("files", ("receipt.png", png_bytes, "image/png")),
        ("files", ("data.csv", csv_bytes, "text/csv")),
    ]

    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 3
    assert len(data["uploaded"]) == 3


@pytest.mark.asyncio
async def test_upload_rejects_invalid_magic_bytes_without_crashing_batch(async_client: AsyncClient):
    pdf_bytes = (FIXTURES_DIR / "digital_invoice.pdf").read_bytes()
    invalid_bytes = b"Random unsupported binary \x00\x01\x02\x03\x04"

    files = [
        ("files", ("valid.pdf", pdf_bytes, "application/pdf")),
        ("files", ("invalid.xyz", invalid_bytes, "application/octet-stream")),
    ]

    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 2

    # First is valid PENDING, second is marked FAILED
    statuses = {item["filename"]: item["status"] for item in data["uploaded"]}
    assert statuses["valid.pdf"] == "PENDING"
    assert statuses["invalid.xyz"] == "FAILED"


@pytest.mark.asyncio
async def test_list_and_get_documents(async_client: AsyncClient):
    # Upload one doc first
    pdf_bytes = (FIXTURES_DIR / "digital_invoice.pdf").read_bytes()
    upload_res = await async_client.post(
        "/api/v1/documents/upload",
        files={"files": ("digital_invoice.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = upload_res.json()["uploaded"][0]["id"]

    # List documents
    list_res = await async_client.get("/api/v1/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == doc_id for item in list_data["items"])

    # Get specific document
    detail_res = await async_client.get(f"/api/v1/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == doc_id
    assert detail_data["filename"] == "digital_invoice.pdf"

    # Check status endpoint
    status_res = await async_client.get(f"/api/v1/documents/{doc_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["document_id"] == doc_id
    assert "status" in status_data
    assert "stage" in status_data


@pytest.mark.asyncio
async def test_get_nonexistent_document(async_client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await async_client.get(f"/api/v1/documents/{fake_id}")
    assert res.status_code == 404
