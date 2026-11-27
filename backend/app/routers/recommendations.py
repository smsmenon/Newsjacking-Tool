"""Recommendations router."""
from __future__ import annotations
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Recommendation
from app.models.schemas import (
    PaginationMeta,
    RecommendationListResponse,
    RecommendationSchema,
    RecommendationUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    team: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> RecommendationListResponse:
    filters = []
    if team:
        filters.append(Recommendation.team == team)
    if priority:
        filters.append(Recommendation.priority == priority)
    if status:
        filters.append(Recommendation.status == status)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(Recommendation)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(Recommendation).order_by(desc(Recommendation.created_at))
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return RecommendationListResponse(
        items=[RecommendationSchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.patch("/{rec_id}", response_model=RecommendationSchema)
async def update_recommendation(
    rec_id: UUID,
    body: RecommendationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> RecommendationSchema:
    rec = await db.get(Recommendation, rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if body.status is not None:
        rec.status = body.status
    if body.notes is not None:
        rec.notes = body.notes
    if body.due_date is not None:
        rec.due_date = body.due_date
    await db.commit()
    await db.refresh(rec)
    return RecommendationSchema.model_validate(rec)
