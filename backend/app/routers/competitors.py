"""Competitors router."""
from __future__ import annotations
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Competitor, CompetitorEvent
from app.models.schemas import (
    CompetitorEventsResponse,
    CompetitorListResponse,
    CompetitorEventSchema,
    CompetitorSchema,
    PaginationMeta,
)

router = APIRouter()


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tier: Optional[str] = Query(None),
    tracking_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> CompetitorListResponse:
    filters = []
    if tier:
        filters.append(Competitor.tier == tier)
    if tracking_status:
        filters.append(Competitor.tracking_status == tracking_status)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(Competitor)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(Competitor).order_by(Competitor.name)
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return CompetitorListResponse(
        items=[CompetitorSchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.get("/{competitor_id}/events", response_model=CompetitorEventsResponse)
async def get_competitor_events(
    competitor_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    significance: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> CompetitorEventsResponse:
    competitor = await db.get(Competitor, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")

    filters = [CompetitorEvent.competitor_id == competitor_id]
    if event_type:
        filters.append(CompetitorEvent.event_type == event_type)
    if significance:
        filters.append(CompetitorEvent.significance == significance)
    if date_from:
        filters.append(CompetitorEvent.detected_at >= date_from)

    where = and_(*filters)
    total = (await db.execute(select(func.count()).select_from(CompetitorEvent).where(where))).scalar_one()
    q = (
        select(CompetitorEvent)
        .where(where)
        .order_by(desc(CompetitorEvent.detected_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = (await db.execute(q)).scalars().all()

    return CompetitorEventsResponse(
        competitor=CompetitorSchema.model_validate(competitor),
        events=[CompetitorEventSchema.model_validate(e) for e in events],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )
