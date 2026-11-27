"""
Advanced hybrid search router — standalone /search endpoint
exposing keyword, semantic, and hybrid (RRF) modes.

The content router embeds /content/search, but this module
provides shared search utilities importable by any router.
"""
from __future__ import annotations

import time
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, CurrentUser
from app.core.database import get_db
from app.models.database import ContentItem
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultSchema,
    ContentItemSchema,
    SearchType,
)
from app.services.vector_service import VectorService, get_vector_service

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def universal_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    vector_service: VectorService = Depends(get_vector_service),
    _user: CurrentUser = Depends(get_current_user),
) -> SearchResponse:
    """
    Universal hybrid search over all content.

    ## Search Modes

    ### keyword
    Uses PostgreSQL `ts_vector` / `plainto_tsquery` for full-text matching.
    Best for exact term matching, phrase queries, and Boolean logic.

    ### semantic
    Uses pgvector cosine similarity on `text-embedding-3-small` embeddings
    (1536 dimensions). Best for conceptual/paraphrase queries.

    ### hybrid (default)
    Applies **Reciprocal Rank Fusion (RRF)**:

        score = Σ 1 / (k + rank_i)

    where `k` (default 60) is the RRF constant that controls the influence
    of lower-ranked results. Both keyword and semantic retrieval run over
    `top_k * 2` candidates, then scores are fused and re-ranked.

    ## Filters
    Applied before retrieval to narrow the candidate pool.
    """
    from app.routers.content import (
        _keyword_search,
        _semantic_search,
        _hybrid_search,
    )

    start = time.perf_counter()

    # Build base filter
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

    if body.search_type == SearchType.keyword:
        results = await _keyword_search(db, body.query, base_filter, body.top_k)
    elif body.search_type == SearchType.semantic:
        results = await _semantic_search(db, body.query, base_filter, body.top_k, vector_service)
    else:
        results = await _hybrid_search(
            db, body.query, base_filter, body.top_k, body.rrf_k, vector_service
        )

    took_ms = int((time.perf_counter() - start) * 1000)

    return SearchResponse(
        results=results,
        query=body.query,
        search_type=body.search_type,
        total=len(results),
        took_ms=took_ms,
    )
