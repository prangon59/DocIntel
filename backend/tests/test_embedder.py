"""Unit tests for the Embedder interface and implementations."""

import math
from unittest.mock import MagicMock

import pytest

from app.services.search.embedder import (
    GeminiEmbedder,
    MockEmbedder,
    get_embedder,
    set_embedder,
)


def test_mock_embedder_generates_normalized_vectors():
    embedder = MockEmbedder(dimensions=768)
    vec1 = embedder._generate_vector("Invoice from Acme Corp")
    assert len(vec1) == 768

    # Check vector is approximately unit-normalized
    norm = math.sqrt(sum(v * v for v in vec1))
    assert pytest.approx(norm, rel=1e-3) == 1.0

    # Deterministic: same text yields same vector
    vec2 = embedder._generate_vector("Invoice from Acme Corp")
    assert vec1 == vec2

    # Different text yields different vector
    vec3 = embedder._generate_vector("Spreadsheet financial ledger")
    assert vec1 != vec3


@pytest.mark.asyncio
async def test_mock_embedder_batch():
    embedder = MockEmbedder(dimensions=768)
    texts = ["Page 1 text", "Page 2 text", "Page 3 text"]
    results = await embedder.embed_batch(texts)
    assert len(results) == 3
    for r in results:
        assert len(r) == 768


@pytest.mark.asyncio
async def test_gemini_embedder_mock_sdk():
    client = GeminiEmbedder(api_key="fake-key")
    mock_sdk = MagicMock()

    mock_emb1 = MagicMock()
    mock_emb1.values = [0.1] * 768
    mock_resp = MagicMock()
    mock_resp.embeddings = [mock_emb1]

    mock_sdk.models.embed_content.return_value = mock_resp
    client._client = mock_sdk

    res = await client.embed_text("Sample invoice line")
    assert len(res) == 768
    assert res[0] == 0.1


def test_get_and_set_embedder():
    custom = MockEmbedder(dimensions=768)
    set_embedder(custom)
    assert get_embedder() is custom
    set_embedder(None)
