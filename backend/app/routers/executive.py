"""Executive briefings and dashboard router."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import ExecutiveBriefing, Insight, ReviewRecord, Signal
from app.models.schemas import ExecutiveBriefingSchema, ExecutiveDashboard

router = APIRouter()


@router.get("/briefing/latest", response_model=ExecutiveBriefingSchema)
async def get_latest_briefing(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ExecutiveBriefingSchema:
    q = select(ExecutiveBriefing).order_by(ExecutiveBriefing.date.desc()).limit(1)
    briefing = (await db.execute(q)).scalar_one_or_none()
    if briefing is None:
        raise HTTPException(status_code=404, detail="No briefings found")
    return ExecutiveBriefingSchema.model_validate(briefing)


@router.get("/briefing/{briefing_date}", response_model=ExecutiveBriefingSchema)
async def get_briefing_by_date(
    briefing_date: date,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ExecutiveBriefingSchema:
    q = select(ExecutiveBriefing).where(
        func.date(ExecutiveBriefing.date) == briefing_date
    )
    briefing = (await db.execute(q)).scalar_one_or_none()
    if briefing is None:
        raise HTTPException(status_code=404, detail=f"No briefing for {briefing_date}")
    return ExecutiveBriefingSchema.model_validate(briefing)


@router.get("/dashboard", response_model=ExecutiveDashboard)
async def get_executive_dashboard(
    period: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ExecutiveDashboard:
    from datetime import datetime, timezone

    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    signals_total = (await db.execute(
        select(func.count()).select_from(Signal).where(Signal.detected_at >= cutoff)
    )).scalar_one()

    signals_24h = (await db.execute(
        select(func.count()).select_from(Signal).where(Signal.detected_at >= cutoff_24h)
    )).scalar_one()

    insights_pending = (await db.execute(
        select(func.count()).select_from(Insight).where(Insight.status == "pending_review")
    )).scalar_one()

    review_queue_size = (await db.execute(
        select(func.count()).select_from(Signal).where(Signal.status == "pending_review")
    )).scalar_one()

    return ExecutiveDashboard(
        period=period,
        signals_total=signals_total,
        signals_new_24h=signals_24h,
        insights_pending_review=insights_pending,
        review_queue_size=review_queue_size,
        health_score=1.0,
    )
