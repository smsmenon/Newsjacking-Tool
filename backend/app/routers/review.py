"""Review queue router."""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Insight, ReviewRecord, Signal
from app.models.schemas import (
    ApproveRequest,
    PaginationMeta,
    RejectRequest,
    RequestChangesRequest,
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewRecordSchema,
)

router = APIRouter()


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    sort_by: str = Query("priority"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ReviewQueueResponse:
    """Return items awaiting human review, sorted by priority then age."""
    items: list[ReviewQueueItem] = []
    now = datetime.now(timezone.utc)

    async def _fetch_signals() -> list[ReviewQueueItem]:
        q = select(Signal).where(Signal.status == "pending_review")
        rows = (await db.execute(q)).scalars().all()
        result = []
        for s in rows:
            age = int((now - s.detected_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600)
            result.append(
                ReviewQueueItem(
                    id=s.id,
                    item_type="signal",
                    item_id=s.id,
                    title=s.title,
                    priority="high" if s.strength >= 0.7 else "medium",
                    submitted_at=s.detected_at,
                    age_hours=age,
                    preview=s.description[:200] if s.description else None,
                )
            )
        return result

    async def _fetch_insights() -> list[ReviewQueueItem]:
        q = select(Insight).where(Insight.status == "pending_review")
        rows = (await db.execute(q)).scalars().all()
        result = []
        for ins in rows:
            age = int((now - ins.generated_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600)
            result.append(
                ReviewQueueItem(
                    id=ins.id,
                    item_type="insight",
                    item_id=ins.id,
                    title=ins.title,
                    priority=ins.priority,
                    submitted_at=ins.generated_at,
                    age_hours=age,
                    preview=ins.summary[:200] if ins.summary else None,
                )
            )
        return result

    if item_type == "signal":
        items = await _fetch_signals()
    elif item_type == "insight":
        items = await _fetch_insights()
    else:
        items = await _fetch_signals() + await _fetch_insights()

    # Sort
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: (priority_order.get(x.priority, 9), -x.age_hours))

    total = len(items)
    by_type = {}
    for item in items:
        by_type[item.item_type] = by_type.get(item.item_type, 0) + 1

    start = (page - 1) * page_size
    page_items = items[start : start + page_size]

    return ReviewQueueResponse(
        items=page_items,
        total=total,
        by_type=by_type,
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


async def _record_review(
    db: AsyncSession,
    item_id: UUID,
    item_type: str,
    action: str,
    user,
    notes: Optional[str] = None,
    reason: Optional[str] = None,
) -> ReviewRecord:
    record = ReviewRecord(
        item_type=item_type,
        item_id=item_id,
        action=action,
        reviewer_id=user.user_id,
        reviewer_name=user.name,
        notes=notes,
        reason=reason,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def _resolve_item(db: AsyncSession, item_id: UUID):
    """Find the item (signal or insight) for a review queue id."""
    signal = await db.get(Signal, item_id)
    if signal:
        return "signal", signal
    insight = await db.get(Insight, item_id)
    if insight:
        return "insight", insight
    return None, None


@router.post("/{item_id}/approve", response_model=ReviewRecordSchema)
async def approve_item(
    item_id: UUID,
    body: ApproveRequest = ApproveRequest(),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReviewRecordSchema:
    item_type, item = await _resolve_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    item.status = "approved"
    record = await _record_review(db, item_id, item_type, "approve", user, notes=body.notes)
    return ReviewRecordSchema.model_validate(record)


@router.post("/{item_id}/reject", response_model=ReviewRecordSchema)
async def reject_item(
    item_id: UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReviewRecordSchema:
    item_type, item = await _resolve_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    item.status = "rejected"
    record = await _record_review(db, item_id, item_type, "reject", user, notes=body.notes, reason=body.reason)
    return ReviewRecordSchema.model_validate(record)


@router.post("/{item_id}/request-changes", response_model=ReviewRecordSchema)
async def request_changes(
    item_id: UUID,
    body: RequestChangesRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReviewRecordSchema:
    item_type, item = await _resolve_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    record = await _record_review(db, item_id, item_type, "request_changes", user, notes=body.notes)
    return ReviewRecordSchema.model_validate(record)
