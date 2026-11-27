"""Content ideas and calendar router."""
from __future__ import annotations
import math
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import ContentIdea
from app.models.schemas import (
    CalendarEntry,
    CalendarPeriod,
    ContentCalendarResponse,
    ContentIdeasListResponse,
    ContentIdeaSchema,
    PaginationMeta,
)

router = APIRouter()


@router.get("/content-ideas", response_model=ContentIdeasListResponse)
async def list_content_ideas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ContentIdeasListResponse:
    filters = []
    if content_type:
        filters.append(ContentIdea.content_type == content_type)
    if status:
        filters.append(ContentIdea.status == status)
    if topic:
        filters.append(ContentIdea.topic == topic)
    if priority:
        filters.append(ContentIdea.priority == priority)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(ContentIdea)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(ContentIdea).order_by(desc(ContentIdea.created_at))
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return ContentIdeasListResponse(
        items=[ContentIdeaSchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.get("/content-calendar", response_model=ContentCalendarResponse)
async def get_content_calendar(
    period: str = Query("monthly"),
    start_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ContentCalendarResponse:
    today = start_date or date.today()
    period_enum = CalendarPeriod(period)

    if period_enum == CalendarPeriod.weekly:
        # Start of current week (Monday)
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period_enum == CalendarPeriod.monthly:
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    else:  # quarterly
        quarter = (today.month - 1) // 3
        start = date(today.year, quarter * 3 + 1, 1)
        quarter_end_month = min(start.month + 2, 12)
        end = date(today.year, quarter_end_month, 28) + timedelta(days=4)
        end = end.replace(day=1) - timedelta(days=1)

    q = (
        select(ContentIdea)
        .where(
            and_(
                ContentIdea.scheduled_date >= start,
                ContentIdea.scheduled_date <= end,
            )
        )
        .order_by(ContentIdea.scheduled_date)
    )
    ideas = (await db.execute(q)).scalars().all()

    # Group by date
    date_map: dict[date, list] = {}
    for idea in ideas:
        d = idea.scheduled_date.date() if hasattr(idea.scheduled_date, "date") else idea.scheduled_date
        if d:
            if d not in date_map:
                date_map[d] = []
            date_map[d].append(ContentIdeaSchema.model_validate(idea))

    entries = [
        CalendarEntry(date=d, ideas=date_ideas)
        for d, date_ideas in sorted(date_map.items())
    ]

    return ContentCalendarResponse(
        period=period_enum,
        start_date=start,
        end_date=end,
        entries=entries,
        total_items=len(ideas),
    )
