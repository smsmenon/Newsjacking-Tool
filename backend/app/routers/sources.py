"""Sources router."""
from __future__ import annotations
import math
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Source
from app.models.schemas import (
    PaginationMeta,
    SourceDiscoverRequest,
    SourceDiscoverResponse,
    SourceListResponse,
    SourceSchema,
)

router = APIRouter()


@router.get("", response_model=SourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    health_status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> SourceListResponse:
    filters = []
    if health_status:
        filters.append(Source.health_status == health_status)
    if source_type:
        filters.append(Source.source_type == source_type)
    if active is not None:
        filters.append(Source.active == active)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(Source)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(Source).order_by(Source.name)
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return SourceListResponse(
        items=[SourceSchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.post("/discover", response_model=SourceDiscoverResponse, status_code=202)
async def suggest_source(
    body: SourceDiscoverRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> SourceDiscoverResponse:
    """Accept a source suggestion for human review (no DB write yet)."""
    suggestion_id = uuid4()
    # TODO: persist to a source_suggestions table and notify reviewers
    return SourceDiscoverResponse(
        id=suggestion_id,
        status="pending_review",
        message=f"Source suggestion accepted. Our team will review {body.url} within 48 hours.",
    )
