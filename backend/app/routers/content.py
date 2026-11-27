"""
Content router — list, detail, and hybrid search endpoints.
"""
from __future__ import annotations

import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, CurrentUser
from app.core.database import get_db
from app.models.database import ContentItem, ContentEntityLink, SignalContentLink
from app.models.schemas import (
    ContentDetailSchema,
    ContentItemSchema,
    ContentListResponse,
    PaginationMeta,
    SearchRequest,
    SearchResponse,
    SearchResultSchema,
    SearchType,
)
from app.services.vector_service import VectorService

router = APIRouter()


def _paginate(total: int, page: int, page_size: int) -> PaginationMeta:
    import math
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


# ─── List ─────────────────────────────────────────────────────────────────────
@router.get("", response_model=ContentListResponse)
async def list_content(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("collected_at"),
    sort_order: str = Query("desc"),
    source: Optional[List[str]] = Query(None),
    topic: Optional[List[str]] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ContentListResponse:
    """List content items with filtering and pagination."""
    # Allowlist sortable columns to prevent SQL injection
    allowed_sort = {"collected_at", "relevance_score", "published_at", "title", "created_at"}
    if sort_by not in allowed_sort:
        sort_by = "collected_at"

    filters = []
    if source:
        filters.append(ContentItem.source.in_(source))
    if topic:
        filters.append(ContentItem.topic.in_(topic))
    if status:
        filters.append(ContentItem.status == status)
    if date_from:
        filters.append(ContentItem.collected_at >= date_from)
    if date_to:
        filters.append(ContentItem.collected_at <= date_to)
    if min_score is not None:
        filters.append(ContentItem.relevance_score >= min_score)

    order_col = getattr(ContentItem, sort_by, ContentItem.collected_at)
    if sort_order == "asc":
        order_expr = order_col
    else:
        order_expr = desc(order_col)

    count_q = select(func.count()).select_from(ContentItem)
    if filters:
        count_q = count_q.where(and_(*filters))
    total = (await db.execute(count_q)).scalar_one()

    q = select(ContentItem)
    if filters:
        q = q.where(and_(*filters))
    q = q.order_by(order_expr).offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(q)).scalars().all()

    return ContentListResponse(
        items=[ContentItemSchema.model_validate(row) for row in rows],
        meta=_paginate(total, page, page_size),
    )


# ─── Search (must be before /{id} to avoid routing conflict) ──────────────────
@router.post("/search", response_model=SearchResponse)
async def search_content(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    vector_service: VectorService = Depends(),
    _user: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    """
    Hybrid search over content using:
    - keyword: PostgreSQL ts_vector full-text search
    - semantic: pgvector cosine similarity
    - hybrid: Reciprocal Rank Fusion combining both (default)
    """
    start = time.perf_counter()

    # Build base filter clause
    filter_clauses = []
    f = body.filters
    if f:
        if f.source:
            filter_clauses.append(ContentItem.source.in_(f.source))
        if f.topic:
            filter_clauses.append(ContentItem.topic.in_(f.topic))
        if f.date_from:
            filter_clauses.append(ContentItem.collected_at >= str(f.date_from))
        if f.date_to:
            filter_clauses.append(ContentItem.collected_at <= str(f.date_to))
        if f.min_score is not None:
            filter_clauses.append(ContentItem.relevance_score >= f.min_score)
        if f.status:
            filter_clauses.append(ContentItem.status.in_(f.status))

    base_filter = and_(*filter_clauses) if filter_clauses else text("TRUE")
    k = body.top_k
    rrf_k = body.rrf_k

    if body.search_type == SearchType.keyword:
        results = await _keyword_search(db, body.query, base_filter, k)
    elif body.search_type == SearchType.semantic:
        results = await _semantic_search(db, body.query, base_filter, k, vector_service)
    else:
        results = await _hybrid_search(db, body.query, base_filter, k, rrf_k, vector_service)

    took_ms = int((time.perf_counter() - start) * 1000)

    return SearchResponse(
        results=results,
        query=body.query,
        search_type=body.search_type,
        total=len(results),
        took_ms=took_ms,
    )


async def _keyword_search(
    db: AsyncSession,
    query: str,
    base_filter,
    k: int,
) -> List[SearchResultSchema]:
    """Full-text search using PostgreSQL ts_vector."""
    ts_query = func.plainto_tsquery("english", query)
    rank_expr = func.ts_rank_cd(ContentItem.search_vector, ts_query).label("rank")

    q = (
        select(ContentItem, rank_expr)
        .where(
            and_(
                base_filter,
                ContentItem.search_vector.op("@@")(ts_query),
            )
        )
        .order_by(desc(rank_expr))
        .limit(k)
    )
    rows = (await db.execute(q)).all()

    results = []
    for i, (item, rank) in enumerate(rows):
        schema = ContentItemSchema.model_validate(item)
        results.append(
            SearchResultSchema(
                **schema.model_dump(),
                search_score=float(rank),
                keyword_rank=i + 1,
                semantic_rank=None,
            )
        )
    return results


async def _semantic_search(
    db: AsyncSession,
    query: str,
    base_filter,
    k: int,
    vector_service: VectorService,
) -> List[SearchResultSchema]:
    """Vector cosine similarity search using pgvector."""
    embedding = await vector_service.embed_query(query)

    # pgvector cosine distance (<=>), lower = more similar
    distance_expr = ContentItem.embedding.cosine_distance(embedding).label("distance")

    q = (
        select(ContentItem, distance_expr)
        .where(
            and_(
                base_filter,
                ContentItem.embedding.is_not(None),
            )
        )
        .order_by(distance_expr)
        .limit(k)
    )
    rows = (await db.execute(q)).all()

    results = []
    for i, (item, distance) in enumerate(rows):
        schema = ContentItemSchema.model_validate(item)
        similarity = 1.0 - float(distance)
        results.append(
            SearchResultSchema(
                **schema.model_dump(),
                search_score=similarity,
                keyword_rank=None,
                semantic_rank=i + 1,
            )
        )
    return results


async def _hybrid_search(
    db: AsyncSession,
    query: str,
    base_filter,
    k: int,
    rrf_k: int,
    vector_service: VectorService,
) -> List[SearchResultSchema]:
    """
    Hybrid search using Reciprocal Rank Fusion (RRF).

    RRF score = sum(1 / (k + rank_i)) for each retrieval system i.
    Higher score = more relevant.
    """
    # 1. Keyword candidates (2x for RRF coverage)
    kw_results = await _keyword_search(db, query, base_filter, k * 2)
    # 2. Semantic candidates
    sem_results = await _semantic_search(db, query, base_filter, k * 2, vector_service)

    # Build rank maps: id -> rank (1-indexed)
    kw_ranks: dict[UUID, int] = {r.id: r.keyword_rank for r in kw_results if r.keyword_rank}
    sem_ranks: dict[UUID, int] = {r.id: r.semantic_rank for r in sem_results if r.semantic_rank}
    all_ids = set(kw_ranks) | set(sem_ranks)

    # Score lookup
    kw_lookup = {r.id: r for r in kw_results}
    sem_lookup = {r.id: r for r in sem_results}

    scored: list[tuple[float, UUID]] = []
    for item_id in all_ids:
        rrf_score = 0.0
        if item_id in kw_ranks:
            rrf_score += 1.0 / (rrf_k + kw_ranks[item_id])
        if item_id in sem_ranks:
            rrf_score += 1.0 / (rrf_k + sem_ranks[item_id])
        scored.append((rrf_score, item_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]

    results = []
    for final_rank, (score, item_id) in enumerate(top, 1):
        base = kw_lookup.get(item_id) or sem_lookup.get(item_id)
        if base is None:
            continue
        results.append(
            SearchResultSchema(
                **ContentItemSchema.model_validate(base).model_dump(),
                search_score=score,
                keyword_rank=kw_ranks.get(item_id),
                semantic_rank=sem_ranks.get(item_id),
            )
        )
    return results


# ─── Detail ───────────────────────────────────────────────────────────────────
@router.get("/{item_id}", response_model=ContentDetailSchema)
async def get_content(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ContentDetailSchema:
    """Get a content item with full text, linked entities and signals."""
    q = (
        select(ContentItem)
        .where(ContentItem.id == item_id)
    )
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Content item not found")

    return ContentDetailSchema.model_validate(item)
