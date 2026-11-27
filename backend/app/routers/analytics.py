"""Analytics router — ROI, signals-over-time, top-topics."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import ContentIdea, Insight, Recommendation, Signal
from app.models.schemas import ROIMetrics, SignalsOverTime, TopTopics

router = APIRouter()

PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


@router.get("/roi", response_model=ROIMetrics)
async def get_roi_metrics(
    period: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ROIMetrics:
    days = PERIOD_DAYS.get(period, 30)
    cutoff = date.today() - timedelta(days=days)

    signals_actioned = (
        await db.execute(
            select(func.count()).select_from(Signal).where(
                Signal.status == "approved",
                Signal.detected_at >= str(cutoff),
            )
        )
    ).scalar_one()

    insights_generated = (
        await db.execute(
            select(func.count()).select_from(Insight).where(
                Insight.generated_at >= str(cutoff)
            )
        )
    ).scalar_one()

    recs_completed = (
        await db.execute(
            select(func.count()).select_from(Recommendation).where(
                Recommendation.status == "completed",
                Recommendation.updated_at >= str(cutoff),
            )
        )
    ).scalar_one()

    return ROIMetrics(
        period=period,
        content_pieces_influenced=recs_completed,
        signals_actioned=signals_actioned,
        time_saved_hours=round(signals_actioned * 2.5, 1),  # estimate: 2.5h per signal
        insights_generated=insights_generated,
        recommendations_completed=recs_completed,
        review_turnaround_hours_avg=4.0,
        top_performing_topics=[],
    )


@router.get("/signals-over-time", response_model=SignalsOverTime)
async def get_signals_over_time(
    period: str = Query("30d"),
    granularity: str = Query("daily"),
    signal_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> SignalsOverTime:
    days = PERIOD_DAYS.get(period, 30)
    cutoff = date.today() - timedelta(days=days)

    trunc_map = {"daily": "day", "weekly": "week", "monthly": "month"}
    trunc = trunc_map.get(granularity, "day")

    q_text = text(f"""
        SELECT date_trunc(:trunc, detected_at)::date AS bucket,
               signal_type,
               count(*) AS cnt
        FROM signals
        WHERE detected_at >= :cutoff
        {f"AND signal_type = :signal_type" if signal_type else ""}
        GROUP BY bucket, signal_type
        ORDER BY bucket
    """)
    params: dict = {"trunc": trunc, "cutoff": str(cutoff)}
    if signal_type:
        params["signal_type"] = signal_type

    rows = (await db.execute(q_text, params)).fetchall()

    # Aggregate into date buckets
    bucket_map: dict[date, dict] = {}
    for row in rows:
        d = row.bucket
        if d not in bucket_map:
            bucket_map[d] = {"date": d, "total": 0, "by_type": {}}
        bucket_map[d]["total"] += row.cnt
        bucket_map[d]["by_type"][row.signal_type] = row.cnt

    data = sorted(bucket_map.values(), key=lambda x: x["date"])

    return SignalsOverTime(period=period, granularity=granularity, data=data)


@router.get("/top-topics", response_model=TopTopics)
async def get_top_topics(
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TopTopics:
    days = PERIOD_DAYS.get(period, 30)
    cutoff = date.today() - timedelta(days=days)

    q = text("""
        SELECT topic, count(*) AS signal_count
        FROM signals
        WHERE detected_at >= :cutoff AND topic IS NOT NULL
        GROUP BY topic
        ORDER BY signal_count DESC
        LIMIT :limit
    """)
    rows = (await db.execute(q, {"cutoff": str(cutoff), "limit": limit})).fetchall()

    topics = [
        {
            "topic": r.topic,
            "signal_count": r.signal_count,
            "content_count": 0,
            "trend": "stable",
            "momentum": 0.5,
        }
        for r in rows
    ]

    return TopTopics(period=period, topics=topics)
