"""
Pydantic v2 request/response schemas for TADA Intelligence Platform.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


# ─── Shared ───────────────────────────────────────────────────────────────────
class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# ─── Enums ────────────────────────────────────────────────────────────────────
class ContentStatus(str, Enum):
    new = "new"
    processing = "processing"
    reviewed = "reviewed"
    archived = "archived"


class SignalType(str, Enum):
    trend_emergence = "trend_emergence"
    competitor_move = "competitor_move"
    regulation = "regulation"
    technology_shift = "technology_shift"
    market_signal = "market_signal"
    sentiment_shift = "sentiment_shift"


class SignalStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"


class TrendMomentum(str, Enum):
    accelerating = "accelerating"
    stable = "stable"
    decelerating = "decelerating"
    emerging = "emerging"
    declining = "declining"


class TrendStatus(str, Enum):
    active = "active"
    archived = "archived"
    watching = "watching"


class InsightType(str, Enum):
    market_opportunity = "market_opportunity"
    competitive_threat = "competitive_threat"
    content_gap = "content_gap"
    audience_shift = "audience_shift"
    technology_adoption = "technology_adoption"


class InsightStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    actioned = "actioned"


class Priority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RecommendationStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    dismissed = "dismissed"


class RecommendationActionType(str, Enum):
    create_content = "create_content"
    update_content = "update_content"
    competitor_response = "competitor_response"
    campaign = "campaign"
    partnership = "partnership"
    research = "research"


class TeamType(str, Enum):
    content = "content"
    marketing = "marketing"
    product = "product"
    executive = "executive"
    research = "research"


class EffortLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ContentType(str, Enum):
    blog_post = "blog_post"
    white_paper = "white_paper"
    case_study = "case_study"
    video = "video"
    podcast = "podcast"
    infographic = "infographic"
    social = "social"
    email = "email"
    webinar = "webinar"
    report = "report"


class ContentIdeaStatus(str, Enum):
    idea = "idea"
    approved = "approved"
    in_production = "in_production"
    published = "published"
    archived = "archived"


class CompetitorTier(str, Enum):
    primary = "primary"
    secondary = "secondary"
    emerging = "emerging"


class CompetitorTrackingStatus(str, Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class CompetitorEventType(str, Enum):
    product_launch = "product_launch"
    pricing_change = "pricing_change"
    partnership = "partnership"
    funding = "funding"
    content_publish = "content_publish"
    hiring = "hiring"
    acquisition = "acquisition"
    marketing_campaign = "marketing_campaign"


class Significance(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EntityType(str, Enum):
    person = "person"
    organization = "organization"
    technology = "technology"
    concept = "concept"
    product = "product"
    event = "event"
    location = "location"


class RelationshipType(str, Enum):
    competes_with = "competes_with"
    partners_with = "partners_with"
    acquires = "acquires"
    uses = "uses"
    mentions = "mentions"
    related_to = "related_to"
    part_of = "part_of"


class ReviewItemType(str, Enum):
    signal = "signal"
    insight = "insight"
    content = "content"
    trend = "trend"


class ReviewAction(str, Enum):
    approve = "approve"
    reject = "reject"
    request_changes = "request_changes"


class SourceType(str, Enum):
    rss_feed = "rss_feed"
    website = "website"
    api = "api"
    social = "social"
    newsletter = "newsletter"
    podcast = "podcast"


class SourceHealthStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    failed = "failed"
    paused = "paused"


class AlertType(str, Enum):
    breaking_signal = "breaking_signal"
    competitor_move = "competitor_move"
    trend_spike = "trend_spike"
    review_overdue = "review_overdue"
    system_health = "system_health"


class AlertSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class AlertChannel(str, Enum):
    slack = "slack"
    email = "email"
    teams = "teams"


class SearchType(str, Enum):
    keyword = "keyword"
    semantic = "semantic"
    hybrid = "hybrid"


class CalendarPeriod(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


# ─── Content Schemas ──────────────────────────────────────────────────────────
class EntityRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    entity_type: EntityType


class SignalRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    signal_type: SignalType


class InsightRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    insight_type: InsightType


class RecommendationRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    action_type: RecommendationActionType


class ContentItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    url: str
    source: str
    topic: str
    summary: Optional[str] = None
    relevance_score: float
    sentiment_score: Optional[float] = None
    status: ContentStatus
    published_at: Optional[datetime] = None
    collected_at: datetime
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    word_count: Optional[int] = None


class ContentDetailSchema(ContentItemSchema):
    full_content: Optional[str] = None
    entities: List[EntityRef] = Field(default_factory=list)
    signals: List[SignalRef] = Field(default_factory=list)
    embedding_model: Optional[str] = None


class ContentListResponse(BaseModel):
    items: List[ContentItemSchema]
    meta: PaginationMeta


# ─── Search Schemas ───────────────────────────────────────────────────────────
class SearchFilters(BaseModel):
    source: Optional[List[str]] = None
    topic: Optional[List[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    search_type: SearchType = SearchType.hybrid
    filters: Optional[SearchFilters] = None
    top_k: int = Field(20, ge=1, le=100)
    rrf_k: int = Field(60, description="RRF constant k")


class SearchResultSchema(ContentItemSchema):
    search_score: float
    keyword_rank: Optional[int] = None
    semantic_rank: Optional[int] = None
    matched_excerpt: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResultSchema]
    query: str
    search_type: SearchType
    total: int
    took_ms: int


# ─── Signal Schemas ───────────────────────────────────────────────────────────
class ReviewRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    reviewer_id: str
    reviewer_name: str
    notes: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime


class SignalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    signal_type: SignalType
    strength: float
    confidence: float
    status: SignalStatus
    detected_at: datetime
    topic: Optional[str] = None
    source_count: int = 0
    tags: List[str] = Field(default_factory=list)


class TrendTimelinePointSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: datetime
    strength: float
    signal_count: int
    notable_events: List[str] = Field(default_factory=list)


class SignalDetailSchema(SignalSchema):
    sources: List[ContentItemSchema] = Field(default_factory=list)
    insights: List[InsightRef] = Field(default_factory=list)
    timeline: List[TrendTimelinePointSchema] = Field(default_factory=list)
    review_history: List[ReviewRecordSchema] = Field(default_factory=list)


class SignalListResponse(BaseModel):
    items: List[SignalSchema]
    meta: PaginationMeta


class ReviewRequestSchema(BaseModel):
    action: ReviewAction
    notes: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=500)


# ─── Trend Schemas ────────────────────────────────────────────────────────────
class TrendSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    topic: str
    momentum: TrendMomentum
    status: TrendStatus
    strength: float
    velocity: float
    first_detected_at: datetime
    last_updated_at: Optional[datetime] = None
    signal_count: int = 0
    tags: List[str] = Field(default_factory=list)


class TrendDetailSchema(TrendSchema):
    signals: List[SignalRef] = Field(default_factory=list)
    timeline: List[TrendTimelinePointSchema] = Field(default_factory=list)
    related_trends: List["TrendSchema"] = Field(default_factory=list)


class TrendListResponse(BaseModel):
    items: List[TrendSchema]
    meta: PaginationMeta


class TrendTimelineResponse(BaseModel):
    trend_id: UUID
    period: str
    granularity: str
    data: List[TrendTimelinePointSchema]


# ─── Insight Schemas ──────────────────────────────────────────────────────────
class InsightSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    summary: str
    insight_type: InsightType
    priority: Priority
    status: InsightStatus
    confidence: float
    generated_at: datetime
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class InsightDetailSchema(InsightSchema):
    full_analysis: Optional[str] = None
    tada_perspective: Optional[str] = None
    supporting_signals: List[SignalRef] = Field(default_factory=list)
    supporting_content: List[ContentItemSchema] = Field(default_factory=list)
    recommendations: List[RecommendationRef] = Field(default_factory=list)
    review_history: List[ReviewRecordSchema] = Field(default_factory=list)


class InsightListResponse(BaseModel):
    items: List[InsightSchema]
    meta: PaginationMeta


# ─── Recommendation Schemas ───────────────────────────────────────────────────
class RecommendationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    action_type: RecommendationActionType
    priority: Priority
    status: RecommendationStatus
    team: TeamType
    effort_estimate: Optional[EffortLevel] = None
    impact_estimate: Optional[EffortLevel] = None
    due_date: Optional[date] = None
    created_at: datetime
    insight_id: Optional[UUID] = None


class RecommendationUpdateRequest(BaseModel):
    status: Optional[RecommendationStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[date] = None


class RecommendationListResponse(BaseModel):
    items: List[RecommendationSchema]
    meta: PaginationMeta


# ─── Content Idea Schemas ─────────────────────────────────────────────────────
class ContentIdeaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    content_type: ContentType
    status: ContentIdeaStatus
    priority: Priority
    target_audience: Optional[str] = None
    topic: str
    estimated_effort_days: Optional[int] = None
    scheduled_date: Optional[date] = None
    created_at: datetime
    tags: List[str] = Field(default_factory=list)
    insight_id: Optional[UUID] = None


class ContentIdeasListResponse(BaseModel):
    items: List[ContentIdeaSchema]
    meta: PaginationMeta


class CalendarEntry(BaseModel):
    date: date
    ideas: List[ContentIdeaSchema]


class ContentCalendarResponse(BaseModel):
    period: CalendarPeriod
    start_date: date
    end_date: date
    entries: List[CalendarEntry]
    total_items: int


# ─── Competitor Schemas ───────────────────────────────────────────────────────
class CompetitorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    domain: str
    description: Optional[str] = None
    tier: CompetitorTier
    tracking_status: CompetitorTrackingStatus
    last_event_at: Optional[datetime] = None
    event_count_30d: int = 0
    created_at: datetime


class CompetitorEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    competitor_id: UUID
    event_type: CompetitorEventType
    title: str
    description: Optional[str] = None
    significance: Significance
    source_url: Optional[str] = None
    detected_at: datetime


class CompetitorListResponse(BaseModel):
    items: List[CompetitorSchema]
    meta: PaginationMeta


class CompetitorEventsResponse(BaseModel):
    competitor: CompetitorSchema
    events: List[CompetitorEventSchema]
    meta: PaginationMeta


# ─── Executive Schemas ────────────────────────────────────────────────────────
class ActionItem(BaseModel):
    title: str
    owner: str
    due_date: Optional[date] = None
    priority: Priority


class ExecutiveBriefingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date: date
    headline: str
    summary: str
    key_signals: List[SignalRef] = Field(default_factory=list)
    key_insights: List[InsightRef] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    competitor_activity: Optional[str] = None
    market_context: Optional[str] = None
    generated_at: datetime


class TopicStat(BaseModel):
    topic: str
    count: int
    trend: str  # up, down, stable


class ExecutiveDashboard(BaseModel):
    period: str
    signals_total: int
    signals_new_24h: int
    insights_pending_review: int
    top_topics: List[TopicStat] = Field(default_factory=list)
    content_published_30d: int = 0
    competitor_events_7d: int = 0
    review_queue_size: int = 0
    health_score: float = 1.0


# ─── Knowledge Graph Schemas ──────────────────────────────────────────────────
class EntitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    entity_type: EntityType
    description: Optional[str] = None
    mention_count: int
    relevance_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    tags: List[str] = Field(default_factory=list)


class RelationshipSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_entity: EntityRef
    target_entity: EntityRef
    relationship_type: RelationshipType
    strength: float
    evidence_count: int


class EntityListResponse(BaseModel):
    items: List[EntitySchema]
    meta: PaginationMeta


class RelationshipListResponse(BaseModel):
    relationships: List[RelationshipSchema]
    total: int


class GraphSearchResponse(BaseModel):
    entities: List[EntitySchema]
    relationships: List[RelationshipSchema]
    query: str
    took_ms: int


# ─── Review Queue Schemas ─────────────────────────────────────────────────────
class ReviewQueueItem(BaseModel):
    id: UUID
    item_type: ReviewItemType
    item_id: UUID
    title: str
    priority: Priority
    submitted_at: datetime
    age_hours: int
    preview: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem]
    total: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    meta: PaginationMeta


class ApproveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)


class RejectRequest(BaseModel):
    reason: str = Field(..., max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)


class RequestChangesRequest(BaseModel):
    notes: str = Field(..., max_length=2000)


# ─── Source Schemas ───────────────────────────────────────────────────────────
class SourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    url: str
    source_type: SourceType
    topic_tags: List[str] = Field(default_factory=list)
    health_status: SourceHealthStatus
    last_fetched_at: Optional[datetime] = None
    articles_7d: int = 0
    fetch_frequency_minutes: int
    active: bool
    created_at: datetime


class SourceDiscoverRequest(BaseModel):
    url: str
    name: Optional[str] = None
    topic_tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class SourceDiscoverResponse(BaseModel):
    id: UUID
    status: str = "pending_review"
    message: str


class SourceListResponse(BaseModel):
    items: List[SourceSchema]
    meta: PaginationMeta


# ─── Analytics Schemas ────────────────────────────────────────────────────────
class TopicROI(BaseModel):
    topic: str
    signals: int
    content_produced: int


class ROIMetrics(BaseModel):
    period: str
    content_pieces_influenced: int
    signals_actioned: int
    time_saved_hours: float
    insights_generated: int
    recommendations_completed: int
    review_turnaround_hours_avg: float = 0.0
    top_performing_topics: List[TopicROI] = Field(default_factory=list)


class SignalsByType(BaseModel):
    date: date
    total: int
    by_type: Dict[str, int] = Field(default_factory=dict)


class SignalsOverTime(BaseModel):
    period: str
    granularity: str
    data: List[SignalsByType]


class TopicMomentum(BaseModel):
    topic: str
    signal_count: int
    content_count: int
    trend: str  # up, down, stable
    momentum: float


class TopTopics(BaseModel):
    period: str
    topics: List[TopicMomentum]


# ─── Alert Schemas ────────────────────────────────────────────────────────────
class AlertSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    channels_sent: List[AlertChannel] = Field(default_factory=list)
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    related_item_id: Optional[UUID] = None
    related_item_type: Optional[str] = None


class AlertListResponse(BaseModel):
    items: List[AlertSchema]
    meta: PaginationMeta


# ─── Webhook Schemas ──────────────────────────────────────────────────────────
class WebhookContentCollected(BaseModel):
    source_id: UUID
    url: str
    title: str
    content: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookSignalDetected(BaseModel):
    signal_type: SignalType
    title: str
    description: str
    strength: float = Field(..., ge=0.0, le=1.0)
    source_content_ids: List[UUID]
    langgraph_run_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookAlertTrigger(BaseModel):
    alert_type: AlertType
    title: str
    description: str
    severity: AlertSeverity
    channels: List[AlertChannel] = Field(default_factory=[AlertChannel.slack])
    related_item_id: Optional[UUID] = None
    related_item_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    received: bool = True
    id: UUID
    message: str = "Accepted"
