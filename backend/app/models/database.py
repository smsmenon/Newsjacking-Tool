"""
SQLAlchemy ORM models for TADA Intelligence Platform.
Uses pgvector for embedding columns.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


# ─── Sources ──────────────────────────────────────────────────────────────────
class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    topic_tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    health_status: Mapped[str] = mapped_column(String(20), nullable=False, default="healthy")
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    articles_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetch_frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    content_items: Mapped[List["ContentItem"]] = relationship("ContentItem", back_populates="source_rel")

    __table_args__ = (
        Index("ix_sources_health_status", "health_status"),
        Index("ix_sources_active", "active"),
    )


# ─── Content Items ────────────────────────────────────────────────────────────
class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Full-text search vector (populated by DB trigger)
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    source_rel: Mapped[Optional["Source"]] = relationship("Source", back_populates="content_items")
    entities: Mapped[List["ContentEntityLink"]] = relationship("ContentEntityLink", back_populates="content")
    signal_links: Mapped[List["SignalContentLink"]] = relationship("SignalContentLink", back_populates="content")

    __table_args__ = (
        Index("ix_content_items_status", "status"),
        Index("ix_content_items_topic", "topic"),
        Index("ix_content_items_collected_at", "collected_at"),
        Index("ix_content_items_relevance_score", "relevance_score"),
        Index("ix_content_items_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_content_items_embedding", "embedding", postgresql_using="ivfflat",
              postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


# ─── Signals ──────────────────────────────────────────────────────────────────
class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    langgraph_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    content_links: Mapped[List["SignalContentLink"]] = relationship("SignalContentLink", back_populates="signal")
    insight_links: Mapped[List["InsightSignalLink"]] = relationship("InsightSignalLink", back_populates="signal")
    reviews: Mapped[List["ReviewRecord"]] = relationship(
        "ReviewRecord", primaryjoin="and_(ReviewRecord.item_type=='signal', foreign(ReviewRecord.item_id)==Signal.id)"
    )

    __table_args__ = (
        Index("ix_signals_status", "status"),
        Index("ix_signals_signal_type", "signal_type"),
        Index("ix_signals_detected_at", "detected_at"),
        Index("ix_signals_strength", "strength"),
    )


class SignalContentLink(Base):
    __tablename__ = "signal_content_links"

    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), primary_key=True)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True)

    signal: Mapped["Signal"] = relationship("Signal", back_populates="content_links")
    content: Mapped["ContentItem"] = relationship("ContentItem", back_populates="signal_links")


# ─── Trends ───────────────────────────────────────────────────────────────────
class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    momentum: Mapped[str] = mapped_column(String(30), nullable=False, default="stable")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    timeline_points: Mapped[List["TrendTimelinePoint"]] = relationship("TrendTimelinePoint", back_populates="trend", order_by="TrendTimelinePoint.date")

    __table_args__ = (
        Index("ix_trends_momentum", "momentum"),
        Index("ix_trends_status", "status"),
        Index("ix_trends_topic", "topic"),
    )


class TrendTimelinePoint(Base):
    __tablename__ = "trend_timeline_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    trend_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trends.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notable_events: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    trend: Mapped["Trend"] = relationship("Trend", back_populates="timeline_points")

    __table_args__ = (
        UniqueConstraint("trend_id", "date", name="uq_trend_timeline_date"),
        Index("ix_trend_timeline_trend_date", "trend_id", "date"),
    )


# ─── Insights ─────────────────────────────────────────────────────────────────
class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tada_perspective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    signal_links: Mapped[List["InsightSignalLink"]] = relationship("InsightSignalLink", back_populates="insight")
    recommendations: Mapped[List["Recommendation"]] = relationship("Recommendation", back_populates="insight")

    __table_args__ = (
        Index("ix_insights_status", "status"),
        Index("ix_insights_priority", "priority"),
        Index("ix_insights_insight_type", "insight_type"),
    )


class InsightSignalLink(Base):
    __tablename__ = "insight_signal_links"

    insight_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("insights.id", ondelete="CASCADE"), primary_key=True)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), primary_key=True)

    insight: Mapped["Insight"] = relationship("Insight", back_populates="signal_links")
    signal: Mapped["Signal"] = relationship("Signal", back_populates="insight_links")


# ─── Recommendations ──────────────────────────────────────────────────────────
class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    insight_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    team: Mapped[str] = mapped_column(String(30), nullable=False)
    effort_estimate: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    impact_estimate: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    insight: Mapped[Optional["Insight"]] = relationship("Insight", back_populates="recommendations")

    __table_args__ = (
        Index("ix_recommendations_status", "status"),
        Index("ix_recommendations_team", "team"),
        Index("ix_recommendations_priority", "priority"),
    )


# ─── Content Ideas ────────────────────────────────────────────────────────────
class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    insight_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="idea")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    target_audience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    estimated_effort_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_content_ideas_status", "status"),
        Index("ix_content_ideas_scheduled_date", "scheduled_date"),
        Index("ix_content_ideas_topic", "topic"),
    )


# ─── Competitors ──────────────────────────────────────────────────────────────
class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="secondary")
    tracking_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    event_count_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    events: Mapped[List["CompetitorEvent"]] = relationship("CompetitorEvent", back_populates="competitor")

    __table_args__ = (
        Index("ix_competitors_tier", "tier"),
        Index("ix_competitors_tracking_status", "tracking_status"),
    )


class CompetitorEvent(Base):
    __tablename__ = "competitor_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    competitor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    significance: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="events")

    __table_args__ = (
        Index("ix_competitor_events_competitor_id", "competitor_id"),
        Index("ix_competitor_events_detected_at", "detected_at"),
    )


# ─── Executive Briefings ──────────────────────────────────────────────────────
class ExecutiveBriefing(Base):
    __tablename__ = "executive_briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    competitor_activity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    market_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    key_signal_ids: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    key_insight_ids: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_executive_briefings_date", "date"),
    )


# ─── Entities (Knowledge Graph) ───────────────────────────────────────────────
class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    content_links: Mapped[List["ContentEntityLink"]] = relationship("ContentEntityLink", back_populates="entity")
    outgoing: Mapped[List["EntityRelationship"]] = relationship("EntityRelationship", foreign_keys="EntityRelationship.source_entity_id", back_populates="source_entity")
    incoming: Mapped[List["EntityRelationship"]] = relationship("EntityRelationship", foreign_keys="EntityRelationship.target_entity_id", back_populates="target_entity")

    __table_args__ = (
        UniqueConstraint("name", "entity_type", name="uq_entity_name_type"),
        Index("ix_entities_entity_type", "entity_type"),
        Index("ix_entities_mention_count", "mention_count"),
        Index("ix_entities_embedding", "embedding", postgresql_using="ivfflat",
              postgresql_with={"lists": 50}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class ContentEntityLink(Base):
    __tablename__ = "content_entity_links"

    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    content: Mapped["ContentItem"] = relationship("ContentItem", back_populates="entities")
    entity: Mapped["Entity"] = relationship("Entity", back_populates="content_links")


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[source_entity_id], back_populates="outgoing")
    target_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[target_entity_id], back_populates="incoming")

    __table_args__ = (
        UniqueConstraint("source_entity_id", "target_entity_id", "relationship_type", name="uq_entity_relationship"),
        Index("ix_entity_relationships_source", "source_entity_id"),
        Index("ix_entity_relationships_target", "target_entity_id"),
    )


# ─── Review Records ───────────────────────────────────────────────────────────
class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)  # signal, insight, content, trend
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # approve, reject, request_changes
    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_review_records_item", "item_type", "item_id"),
        Index("ix_review_records_created_at", "created_at"),
    )


# ─── Alerts ───────────────────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    channels_sent: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    related_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    related_item_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    dedup_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_dedup_key", "dedup_key"),
    )
