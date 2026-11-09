"""Embedder interface and Gemini vector embedding implementation for semantic search."""

import asyncio
import hashlib
import math
from abc import ABC, abstractmethod

from google import genai

from app.core.config import settings
from app.core.logging import logger


class Embedder(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate a dense vector embedding for a single text chunk.

        Args:
            text: Input string to embed.

        Returns:
            list[float]: Embedding vector of dimensions equal to settings.EMBEDDING_DIMENSIONS.
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of text chunks.

        Args:
            texts: List of input strings.

        Returns:
            list[list[float]]: List of embedding vectors.
        """
        pass


class GeminiEmbedder(Embedder):
    """Embedder leveraging Google GenAI SDK (text-embedding-004)."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.timeout_seconds = timeout_seconds
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured for embeddings.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single string."""
        if not text.strip():
            return [0.0] * settings.EMBEDDING_DIMENSIONS

        batch_result = await self.embed_batch([text])
        return batch_result[0] if batch_result else [0.0] * settings.EMBEDDING_DIMENSIONS

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings concurrently or in batch."""
        clean_texts = [t.strip() for t in texts if t.strip()]
        if not clean_texts:
            return [[0.0] * settings.EMBEDDING_DIMENSIONS for _ in texts]

        client = self._get_client()

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.embed_content,
                    model=self.model_name,
                    contents=clean_texts,  # type: ignore[arg-type]
                ),
                timeout=self.timeout_seconds,
            )

            if not response.embeddings:
                raise ValueError("No embeddings returned by Gemini embed_content API.")

            return [list(emb.values or []) for emb in response.embeddings]

        except Exception as exc:
            logger.warning("Gemini embedding generation failed: %s", exc)
            raise


class MockEmbedder(Embedder):
    """Deterministic mock embedder for tests producing normalized 768-dim vectors."""

    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    async def embed_text(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic unit-length vector based on MD5 text hash."""
        if not text.strip():
            return [0.0] * self.dimensions

        hasher = hashlib.md5(text.encode("utf-8")).digest()
        # Seed values from hash bytes
        raw_vals = [
            float((hasher[i % len(hasher)] ^ ((i * 7) & 0xFF)) - 128)
            for i in range(self.dimensions)
        ]
        norm = math.sqrt(sum(v * v for v in raw_vals)) or 1.0
        return [round(v / norm, 6) for v in raw_vals]


_default_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Retrieve or lazily initialize global default embedder."""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = GeminiEmbedder()
    return _default_embedder


def set_embedder(embedder: Embedder | None) -> None:
    """Override default embedder for testing."""
    global _default_embedder
    _default_embedder = embedder
