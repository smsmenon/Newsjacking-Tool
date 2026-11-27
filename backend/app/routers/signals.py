"""
Signals router — list, detail, and review endpoints.
"""
from __future__ import annotations

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, CurrentUser
from app.core.database import get_db
from app.models.database import Signal, ReviewRecord, SignalContentLink
from app.models.schemas import (
    PaginationMeta,
    ReviewRecordSchema,
    ReviewRequestSchema,
    SignalDetailSchema,
    SignalListResponse,
    SignalSchema,
    SignalStatus,
)

router = APIRouter()


def _paginate(total: int, page: int, page_size: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )


# ─── List ─────────────────────────────────────────────────────────────────────
@router.get("", response_model=SignalListResponse)
async def list_signals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("detected_at"),
    sort_order: str = Query("desc"),
    signal_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    min_strength: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> SignalListResponse:
    """List signals with filtering and pagination."""
    allowed_sort = {"detected_at", "strength", "confidence", "created_at"}
    if sort_by not in allowed_sort:
        sort_by = "detected_at"

    filters = []
    if signal_type:
        filters.append(Signal.signal_type == signal_type)
    if status:
        filters.append(Signal.status == status)
    if topic:
        filters.append(Signal.topic == topic)
    if min_strength is not None:
        filters.append(Signal.strength >= min_strength)
    if min_confidence is not None:
        filters.append(Signal.confidence >= min_confidence)

    where = and_(*filters) if filters else None

    count_q = select(func.count()).select_from(Signal)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    order_col = getattr(Signal, sort_by, Signal.detected_at)
    order_expr = desc(order_col) if sort_order == "desc" else order_col

    q = select(Signal)
    if where is not None:
        q = q.where(where)
    q = q.order_by(order_expr).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return SignalListResponse(
        items=[SignalSchema.model_validate(r) for r in rows],
        meta=_paginate(total, page, page_size),
    )


# ─── Detail ───────────────────────────────────────────────────────────────────
@router.get("/{signal_id}", response_model=SignalDetailSchema)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> SignalDetailSchema:
    """Get a signal with its source content items, linked insights, and review history."""
    q = (
        select(Signal)
        .where(Signal.id == signal_id)
        .options(
            selectinload(Signal.content_links).selectinload(SignalContentLink.content),
            selectinload(Signal.insight_links),
        )
    )
    signal = (await db.execute(q)).scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Fetch review history
    reviews_q = (
        select(ReviewRecord)
        .where(
            and_(
                ReviewRecord.item_type == "signal",
                ReviewRecord.item_id == signal_id,
            )
        )
        .order_by(ReviewRecord.created_at)
    )
    reviews = (await db.execute(reviews_q)).scalars().all()

    detail = SignalDetailSchema.model_validate(signal)
    detail.review_history = [ReviewRecordSchema.model_validate(r) for r in reviews]
    return detail


# ─── Review ───────────────────────────────────────────────────────────────────
@router.post("/{signal_id}/review", response_model=SignalSchema)
async def review_signal(
    signal_id: UUID,
    body: ReviewRequestSchema,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SignalSchema:
    """Submit a review action (approve / reject / request_changes) on a signal."""
    signal = await db.get(Signal, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Map review action → signal status
    STATUS_MAP = {
        "approve": "approved",
        "reject": "rejected",
        "request_changes": "pending_review",
    }
    signal.status = STATUS_MAP[body.action]

    # Record the review
    record = ReviewRecord(
        item_type="signal",
        item_id=signal_id,
        action=body.action,
        reviewer_id=user.user_id,
        reviewer_name=user.name,
        notes=body.notes,
        reason=body.reason,
    )
    db.add(record)
    await db.commit()
    await db.refresh(signal)

    return SignalSchema.model_validate(signal)
