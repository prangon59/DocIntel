"""Search API endpoints supporting keyword, semantic, and hybrid search with faceted filters."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.document import DocumentStatus
from app.schemas.search import SearchMode, SearchResponse
from app.services.search.service import search_documents

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search ingested documents using keyword, semantic, or hybrid (RRF) retrieval.",
)
async def search(
    q: str = Query("", description="Search query string"),
    mode: SearchMode = Query(SearchMode.HYBRID, description="Retrieval mode: keyword | semantic | hybrid"),
    supplier: str | None = Query(None, description="Filter by supplier / vendor name"),
    date_from: date | None = Query(None, description="Filter by invoice date >= date_from"),
    date_to: date | None = Query(None, description="Filter by invoice date <= date_to"),
    needs_review: bool | None = Query(None, description="Filter by review status"),
    min_total: Decimal | None = Query(None, description="Filter by minimum invoice total"),
    max_total: Decimal | None = Query(None, description="Filter by maximum invoice total"),
    doc_status: DocumentStatus | None = Query(None, alias="status", description="Filter by document status"),
    limit: int = Query(20, ge=1, le=100, description="Results limit"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    """Execute search across ingested document text and extracted metadata."""
    return await search_documents(
        db=db,
        query=q,
        mode=mode,
        supplier=supplier,
        date_from=date_from,
        date_to=date_to,
        needs_review=needs_review,
        min_total=min_total,
        max_total=max_total,
        status=doc_status,
        limit=limit,
        offset=offset,
    )
