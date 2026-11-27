"""Trends router."""
from __future__ import annotations

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Trend, TrendTimelinePoint
from app.models.schemas import (
    PaginationMeta,
    TrendDetailSchema,
    TrendListResponse,
    TrendSchema,
    TrendTimelinePointSchema,
    TrendTimelineResponse,
)

router = APIRouter()


@router.get("", response_model=TrendListResponse)
async def list_trends(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    momentum: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    min_strength: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TrendListResponse:
    filters = []
    if momentum:
        filters.append(Trend.momentum == momentum)
    if status:
        filters.append(Trend.status == status)
    if topic:
        filters.append(Trend.topic == topic)
    if min_strength is not None:
        filters.append(Trend.strength >= min_strength)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(Trend)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(Trend).order_by(desc(Trend.strength))
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return TrendListResponse(
        items=[TrendSchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.get("/{trend_id}", response_model=TrendDetailSchema)
async def get_trend(
    trend_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TrendDetailSchema:
    q = (
        select(Trend)
        .where(Trend.id == trend_id)
        .options(selectinload(Trend.timeline_points))
    )
    trend = (await db.execute(q)).scalar_one_or_none()
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    return TrendDetailSchema.model_validate(trend)


@router.get("/{trend_id}/timeline", response_model=TrendTimelineResponse)
async def get_trend_timeline(
    trend_id: UUID,
    period: str = Query("30d"),
    granularity: str = Query("daily"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TrendTimelineResponse:
    trend = await db.get(Trend, trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")

    q = (
        select(TrendTimelinePoint)
        .where(TrendTimelinePoint.trend_id == trend_id)
        .order_by(TrendTimelinePoint.date)
    )
    points = (await db.execute(q)).scalars().all()
    return TrendTimelineResponse(
        trend_id=trend_id,
        period=period,
        granularity=granularity,
        data=[TrendTimelinePointSchema.model_validate(p) for p in points],
    )
