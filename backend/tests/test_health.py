"""Health check and API routing tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient) -> None:
    """Verify that /health responds with 200 and valid schema."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "error")
    assert "version" in data
    assert "environment" in data
    assert "components" in data


@pytest.mark.asyncio
async def test_api_v1_info_endpoint(async_client: AsyncClient) -> None:
    """Verify that /api/v1/info responds with 200 and API metadata."""
    response = await async_client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert "description" in data


@pytest.mark.asyncio
async def test_request_id_header_injected(async_client: AsyncClient) -> None:
    """Verify that X-Request-ID and X-Process-Time-Ms headers are injected by middleware."""
    custom_id = "test-request-id-12345"
    response = await async_client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    assert "X-Process-Time-Ms" in response.headers
