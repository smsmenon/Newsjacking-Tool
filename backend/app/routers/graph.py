"""Knowledge graph router — entities, relationships, graph search."""
from __future__ import annotations
import math
import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Entity, EntityRelationship
from app.models.schemas import (
    EntityListResponse,
    EntitySchema,
    GraphSearchResponse,
    PaginationMeta,
    RelationshipListResponse,
    RelationshipSchema,
)

router = APIRouter()


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    min_mentions: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> EntityListResponse:
    filters = []
    if entity_type:
        filters.append(Entity.entity_type == entity_type)
    if min_mentions:
        filters.append(Entity.mention_count >= min_mentions)

    where = and_(*filters) if filters else None
    count_q = select(func.count()).select_from(Entity)
    if where is not None:
        count_q = count_q.where(where)
    total = (await db.execute(count_q)).scalar_one()

    q = select(Entity).order_by(desc(Entity.mention_count))
    if where is not None:
        q = q.where(where)
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return EntityListResponse(
        items=[EntitySchema.model_validate(r) for r in rows],
        meta=PaginationMeta(
            page=page, page_size=page_size, total=total,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        ),
    )


@router.get("/relationships", response_model=RelationshipListResponse)
async def get_relationships(
    entity_id: Optional[UUID] = Query(None),
    relationship_type: Optional[str] = Query(None),
    min_strength: Optional[float] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> RelationshipListResponse:
    filters = []
    if entity_id:
        filters.append(
            (EntityRelationship.source_entity_id == entity_id)
            | (EntityRelationship.target_entity_id == entity_id)
        )
    if relationship_type:
        filters.append(EntityRelationship.relationship_type == relationship_type)
    if min_strength is not None:
        filters.append(EntityRelationship.strength >= min_strength)

    q = (
        select(EntityRelationship)
        .options(
            selectinload(EntityRelationship.source_entity),
            selectinload(EntityRelationship.target_entity),
        )
        .order_by(desc(EntityRelationship.strength))
        .limit(limit)
    )
    if filters:
        q = q.where(and_(*filters))

    rows = (await db.execute(q)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(EntityRelationship))).scalar_one()

    return RelationshipListResponse(
        relationships=[RelationshipSchema.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/search", response_model=GraphSearchResponse)
async def search_graph(
    q: str = Query(..., min_length=1),
    entity_types: Optional[List[str]] = Query(None),
    include_relationships: bool = Query(True),
    depth: int = Query(1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> GraphSearchResponse:
    start = time.perf_counter()

    filters = [Entity.name.ilike(f"%{q}%")]
    if entity_types:
        filters.append(Entity.entity_type.in_(entity_types))

    entity_q = select(Entity).where(and_(*filters)).order_by(desc(Entity.mention_count)).limit(20)
    entities = (await db.execute(entity_q)).scalars().all()

    relationships: List[EntityRelationship] = []
    if include_relationships and entities:
        entity_ids = [e.id for e in entities]
        rel_q = (
            select(EntityRelationship)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(
                (EntityRelationship.source_entity_id.in_(entity_ids))
                | (EntityRelationship.target_entity_id.in_(entity_ids))
            )
            .limit(50)
        )
        relationships = (await db.execute(rel_q)).scalars().all()

    took_ms = int((time.perf_counter() - start) * 1000)

    return GraphSearchResponse(
        entities=[EntitySchema.model_validate(e) for e in entities],
        relationships=[RelationshipSchema.model_validate(r) for r in relationships],
        query=q,
        took_ms=took_ms,
    )
