"""LLM information extraction service and factory."""

from app.services.extraction.client import LLMClient
from app.services.extraction.gemini_client import GeminiLLMClient

_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Retrieve or create the global default LLMClient instance."""
    global _default_client
    if _default_client is None:
        _default_client = GeminiLLMClient()
    return _default_client


def set_llm_client(client: LLMClient | None) -> None:
    """Override the global LLMClient (useful for testing or dependency injection)."""
    global _default_client
    _default_client = client


__all__ = ["LLMClient", "GeminiLLMClient", "get_llm_client", "set_llm_client"]
