"""Search schemas for keyword, semantic, and hybrid search results."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchMode(StrEnum):
    """Supported retrieval search modes."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SearchResultItem(BaseModel):
    """Individual matched document search result item."""

    model_config = ConfigDict(extra="ignore")

    document_id: UUID
    filename: str
    file_type: str
    status: str
    needs_review: bool
    supplier_name: str | None = None
    invoice_number: str | None = None
    total: Decimal | None = None
    currency: str | None = None
    invoice_date: str | None = None
    score: float = Field(default=0.0, description="Normalized relevance or RRF score")
    match_type: str = Field(default="keyword", description="keyword | semantic | hybrid")
    highlight: str | None = Field(default=None, description="Text snippet with match context")


class SearchResponse(BaseModel):
    """Search query response container."""

    model_config = ConfigDict(extra="ignore")

    query: str
    mode: SearchMode
    total_hits: int
    results: list[SearchResultItem]
