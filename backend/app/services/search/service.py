"""Search service implementing keyword, semantic, and hybrid (Reciprocal Rank Fusion) search."""

import math
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentStatus
from app.models.embedding import Embedding
from app.models.extraction import Extraction
from app.schemas.search import SearchMode, SearchResponse, SearchResultItem
from app.services.search.embedder import get_embedder


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _matches_extraction_filters(ext: Extraction | None, filters: dict[str, Any]) -> bool:
    """Check if extraction satisfies structured filters."""
    if filters.get("supplier") and (not ext or not ext.supplier_name or filters["supplier"].lower() not in ext.supplier_name.lower()):
        return False
    if filters.get("date_from") and (not ext or not ext.invoice_date or ext.invoice_date < filters["date_from"]):
        return False
    if filters.get("date_to") and (not ext or not ext.invoice_date or ext.invoice_date > filters["date_to"]):
        return False
    if filters.get("min_total") and (not ext or ext.total is None or ext.total < filters["min_total"]):
        return False
    return not (filters.get("max_total") and (not ext or ext.total is None or ext.total > filters["max_total"]))


def _extract_highlight(text: str, query: str, window: int = 120) -> str:
    """Extract snippet highlighting surrounding query occurrence."""
    if not text:
        return ""
    q_lower = query.lower()
    t_lower = text.lower()
    pos = t_lower.find(q_lower)
    if pos == -1:
        return text[:window] + ("..." if len(text) > window else "")
    start = max(0, pos - 40)
    end = min(len(text), pos + len(query) + 80)
    snippet = text[start:end].strip()
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


async def search_documents(
    db: AsyncSession,
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    supplier: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    needs_review: bool | None = None,
    min_total: Decimal | None = None,
    max_total: Decimal | None = None,
    status: DocumentStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> SearchResponse:
    """Execute keyword, semantic, or hybrid search with structured filters."""
    query_clean = query.strip()

    if mode == SearchMode.KEYWORD:
        ranked_items = await _execute_keyword_search(
            db,
            query_clean,
            supplier=supplier,
            date_from=date_from,
            date_to=date_to,
            needs_review=needs_review,
            min_total=min_total,
            max_total=max_total,
            status=status,
        )
    elif mode == SearchMode.SEMANTIC:
        ranked_items = await _execute_semantic_search(
            db,
            query_clean,
            supplier=supplier,
            date_from=date_from,
            date_to=date_to,
            needs_review=needs_review,
            min_total=min_total,
            max_total=max_total,
            status=status,
        )
    else:  # Hybrid (Reciprocal Rank Fusion)
        ranked_items = await _execute_hybrid_search(
            db,
            query_clean,
            supplier=supplier,
            date_from=date_from,
            date_to=date_to,
            needs_review=needs_review,
            min_total=min_total,
            max_total=max_total,
            status=status,
        )

    total_hits = len(ranked_items)
    paginated = ranked_items[offset : offset + limit]

    return SearchResponse(
        query=query,
        mode=mode,
        total_hits=total_hits,
        results=paginated,
    )


async def _execute_keyword_search(
    db: AsyncSession,
    query: str,
    **filters: Any,
) -> list[SearchResultItem]:
    """Execute keyword text and metadata search."""
    stmt = (
        select(Document)
        .options(
            selectinload(Document.extractions),
            selectinload(Document.pages),
        )
        .order_by(Document.created_at.desc())
    )

    if filters.get("status"):
        stmt = stmt.where(Document.status == filters["status"])
    if filters.get("needs_review") is not None:
        stmt = stmt.where(Document.needs_review == filters["needs_review"])

    results = (await db.execute(stmt)).scalars().all()
    items: list[SearchResultItem] = []
    q_lower = query.lower()

    for doc in results:
        ext = doc.extractions[0] if doc.extractions else None
        if not _matches_extraction_filters(ext, filters):
            continue

        # Check match in filename, raw text, or metadata
        matched = False
        highlight = None
        score = 0.0

        if not q_lower:
            # Empty query acts as a filter-only query
            matched = True
            score = 1.0
        else:
            if q_lower in doc.filename.lower():
                matched = True
                score += 3.0
                highlight = f"Filename: {doc.filename}"

            if ext:
                if ext.supplier_name and q_lower in ext.supplier_name.lower():
                    matched = True
                    score += 5.0
                    highlight = f"Supplier: {ext.supplier_name}"
                if ext.invoice_number and q_lower in ext.invoice_number.lower():
                    matched = True
                    score += 5.0
                    highlight = f"Invoice #: {ext.invoice_number}"

            for page in doc.pages:
                if page.raw_text and q_lower in page.raw_text.lower():
                    matched = True
                    score += 2.0
                    if not highlight:
                        highlight = _extract_highlight(page.raw_text, query)

        if matched:
            items.append(
                SearchResultItem(
                    document_id=doc.id,
                    filename=doc.filename,
                    file_type=doc.file_type,
                    status=doc.status.value,
                    needs_review=doc.needs_review,
                    supplier_name=ext.supplier_name if ext else None,
                    invoice_number=ext.invoice_number if ext else None,
                    total=ext.total if ext else None,
                    currency=ext.currency if ext else None,
                    invoice_date=str(ext.invoice_date) if ext and ext.invoice_date else None,
                    score=round(score, 3),
                    match_type="keyword",
                    highlight=highlight,
                )
            )

    items.sort(key=lambda x: x.score, reverse=True)
    return items


async def _execute_semantic_search(
    db: AsyncSession,
    query: str,
    **filters: Any,
) -> list[SearchResultItem]:
    """Execute vector semantic search over chunk embeddings."""
    if not query:
        return await _execute_keyword_search(db, query, **filters)

    embedder = get_embedder()
    query_vector = await embedder.embed_text(query)

    # Load embeddings and documents
    stmt = (
        select(Embedding)
        .options(
            selectinload(Embedding.document).selectinload(Document.extractions),
            selectinload(Embedding.document).selectinload(Document.pages),
        )
    )
    embeddings = (await db.execute(stmt)).scalars().all()

    # Score chunks and group by document ID
    doc_best_scores: dict[UUID, tuple[float, Embedding]] = {}
    for emb in embeddings:
        sim = _cosine_similarity(query_vector, emb.embedding)
        doc_id = emb.document_id
        if doc_id not in doc_best_scores or sim > doc_best_scores[doc_id][0]:
            doc_best_scores[doc_id] = (sim, emb)

    items: list[SearchResultItem] = []
    for _doc_id, (sim, best_emb) in doc_best_scores.items():
        doc = best_emb.document
        if not doc:
            continue

        # Filters
        if filters.get("status") and doc.status != filters["status"]:
            continue
        if filters.get("needs_review") is not None and doc.needs_review != filters["needs_review"]:
            continue

        ext = doc.extractions[0] if doc.extractions else None
        if not _matches_extraction_filters(ext, filters):
            continue

        highlight = _extract_highlight(best_emb.chunk_text, query)

        items.append(
            SearchResultItem(
                document_id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                status=doc.status.value,
                needs_review=doc.needs_review,
                supplier_name=ext.supplier_name if ext else None,
                invoice_number=ext.invoice_number if ext else None,
                total=ext.total if ext else None,
                currency=ext.currency if ext else None,
                invoice_date=str(ext.invoice_date) if ext and ext.invoice_date else None,
                score=round(sim, 4),
                match_type="semantic",
                highlight=highlight,
            )
        )

    items.sort(key=lambda x: x.score, reverse=True)
    return items


async def _execute_hybrid_search(
    db: AsyncSession,
    query: str,
    **filters: Any,
) -> list[SearchResultItem]:
    """Combine keyword and semantic search via Reciprocal Rank Fusion (RRF)."""
    k_constant = 60

    keyword_results = await _execute_keyword_search(db, query, **filters)
    semantic_results = await _execute_semantic_search(db, query, **filters)

    # RRF scoring dictionary: {doc_id: combined_score}
    rrf_scores: dict[UUID, float] = {}
    doc_map: dict[UUID, SearchResultItem] = {}
    matched_modes: dict[UUID, set[str]] = {}

    for rank, item in enumerate(keyword_results, start=1):
        rrf_scores[item.document_id] = rrf_scores.get(item.document_id, 0.0) + (1.0 / (k_constant + rank))
        doc_map[item.document_id] = item
        matched_modes.setdefault(item.document_id, set()).add("keyword")

    for rank, item in enumerate(semantic_results, start=1):
        rrf_scores[item.document_id] = rrf_scores.get(item.document_id, 0.0) + (1.0 / (k_constant + rank))
        if item.document_id not in doc_map:
            doc_map[item.document_id] = item
        matched_modes.setdefault(item.document_id, set()).add("semantic")

    combined: list[SearchResultItem] = []
    for doc_id, score in rrf_scores.items():
        base_item = doc_map[doc_id]
        modes = matched_modes[doc_id]
        match_type = "hybrid" if len(modes) > 1 else list(modes)[0]

        combined.append(
            SearchResultItem(
                document_id=base_item.document_id,
                filename=base_item.filename,
                file_type=base_item.file_type,
                status=base_item.status,
                needs_review=base_item.needs_review,
                supplier_name=base_item.supplier_name,
                invoice_number=base_item.invoice_number,
                total=base_item.total,
                currency=base_item.currency,
                invoice_date=base_item.invoice_date,
                score=round(score, 5),
                match_type=match_type,
                highlight=base_item.highlight,
            )
        )

    combined.sort(key=lambda x: x.score, reverse=True)
    return combined
