"""
TADA Intelligence Platform — Shared Agent State
================================================
Single TypedDict that flows through the entire LangGraph graph.
Every node reads from and writes to this state object.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


# ---------------------------------------------------------------------------
# Sub-structures (dicts, not dataclasses, so they survive JSON serialisation)
# ---------------------------------------------------------------------------

class RawContentItem(TypedDict):
    """A single piece of raw content fetched from a source."""
    id: str
    source_name: str
    source_type: str          # rss | linkedin | twitter | reddit | podcast | report
    source_url: str
    title: str
    body: str
    author: Optional[str]
    published_at: str         # ISO-8601
    fetched_at: str           # ISO-8601
    language: str             # ISO 639-1
    word_count: int
    metadata: Dict[str, Any]


class SourceQualityScore(TypedDict):
    source_name: str
    trust_score: float        # 0-10
    authority_score: float    # 0-10
    influence_score: float    # 0-10
    composite_score: float    # weighted
    tier: Literal["tier1", "tier2", "tier3"]
    rationale: str


class SignalScore(TypedDict):
    supply_chain_relevance: float   # 0-10
    executive_importance: float     # 0-10
    business_impact: float          # 0-10
    technology_relevance: float     # 0-10
    tada_alignment: float           # 0-10
    final_score: float              # weighted composite


class DetectedSignal(TypedDict):
    signal_id: str
    headline: str
    signal_type: str              # disruption | trend | opportunity | risk | regulation | innovation
    summary: str
    evidence: str                 # direct quotes or paraphrased evidence
    source_ids: List[str]         # links back to RawContentItem.id
    source_names: List[str]
    first_seen: str               # ISO-8601
    score: SignalScore
    confidence: float             # 0-1
    momentum: str                 # rising | stable | declining
    keywords: List[str]
    entities: List[str]           # companies, geographies, technologies
    cluster_id: Optional[str]     # signals grouped into clusters
    is_breaking: bool
    is_validated: bool            # confirmed across multiple sources


class TrendAnalysis(TypedDict):
    trend_id: str
    name: str
    description: str
    signals: List[str]            # signal_ids
    velocity: str                 # fast | moderate | slow
    maturity: str                 # emerging | growing | mainstream | declining
    timeframe: str                # short | medium | long
    categories: List[str]
    implications_for_tada: str


class TADAPerspective(TypedDict):
    signal_id: str
    what_happened: str
    why_it_matters: str
    potential_impact: str
    traditional_response: str
    tada_response: str
    detect: str
    decide: str
    do: str
    expected_business_outcome: str
    urgency: Literal["immediate", "this_week", "this_month", "watch"]


class CompetitorActivity(TypedDict):
    competitor_name: str
    competitor_url: str
    activity_type: str       # product_launch | partnership | acquisition | messaging_shift | pricing | hiring
    title: str
    summary: str
    detected_at: str
    source_url: str
    positioning_opportunity: str
    threat_level: str        # high | medium | low


class PainPoint(TypedDict):
    pain_id: str
    category: str            # operational | technology | cost | compliance | talent | visibility
    description: str
    frequency: int           # how many sources mention it
    source_ids: List[str]
    verbatim_quotes: List[str]
    affected_personas: List[str]
    tada_solution_angle: str


class ContentIdea(TypedDict):
    idea_id: str
    format: str              # linkedin_post | article | newsletter | webinar | podcast | sales_deck_slide
    title: str
    hook: str
    outline: Optional[List[str]]
    key_message: str
    cta: str
    signal_id: str           # traceability: which signal spawned this
    target_audience: str     # marketing | sales | cs | leadership | product
    estimated_reach: str     # niche | moderate | broad
    urgency: str             # evergreen | timely | breaking


class SalesIntelligence(TypedDict):
    signal_id: str
    discovery_question: str
    talking_point: str
    objection_handler: str
    proof_point: str
    target_persona: str
    urgency_trigger: str
    competitive_angle: str


class ExecutiveBriefingItem(TypedDict):
    rank: int
    signal_id: str
    headline: str
    why_it_matters_ceo: str
    recommended_action: str
    time_to_act: str


class QAResult(TypedDict):
    node_name: str
    passed: bool
    issues: List[str]
    warnings: List[str]
    confidence_override: Optional[float]


class KnowledgeEntity(TypedDict):
    entity_id: str
    name: str
    entity_type: str         # company | technology | regulation | person | geography | concept
    first_seen: str
    last_seen: str
    signal_count: int
    related_entities: List[str]
    summary: str


# ---------------------------------------------------------------------------
# Primary AgentState — the single source of truth across all graph nodes
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """
    Shared state object for the TADA Intelligence Platform LangGraph workflow.

    Flow:
        research → collection → signal_detection → trend_analysis
            → competitive_intel (parallel) → pain_point (parallel)
            → tada_perspective → content_strategy → sales
            → executive_briefing → qa → repository → recommendation

    All fields are Optional so nodes can operate on partial state.
    """

    # ── Run metadata ──────────────────────────────────────────────────────
    run_id: str
    run_mode: Literal["daily", "weekly", "monthly", "ad_hoc"]
    started_at: str
    completed_at: Optional[str]
    triggered_by: str          # scheduler | webhook | manual
    version: str               # platform version

    # ── Research / Collection ─────────────────────────────────────────────
    target_sources: List[str]               # source ids from sources.json
    raw_content: List[RawContentItem]
    source_quality_scores: List[SourceQualityScore]
    collection_stats: Dict[str, Any]        # items_fetched, errors, duration_s

    # ── Signal Detection ──────────────────────────────────────────────────
    detected_signals: List[DetectedSignal]
    signal_clusters: Dict[str, List[str]]   # cluster_id → [signal_ids]
    surfaced_signals: List[DetectedSignal]  # score >= 7 or breaking

    # ── Trend Analysis ────────────────────────────────────────────────────
    trends: List[TrendAnalysis]
    emerging_themes: List[str]

    # ── Competitive Intelligence ──────────────────────────────────────────
    competitor_activities: List[CompetitorActivity]
    competitive_landscape_summary: str

    # ── Pain Points ───────────────────────────────────────────────────────
    pain_points: List[PainPoint]

    # ── TADA Perspective ──────────────────────────────────────────────────
    tada_perspectives: List[TADAPerspective]

    # ── Entity Extraction / Knowledge Graph ───────────────────────────────
    entities: List[KnowledgeEntity]
    entity_relationships: List[Dict[str, str]]   # {source, target, relation}

    # ── Content Strategy ──────────────────────────────────────────────────
    content_ideas: List[ContentIdea]
    content_calendar_suggestions: List[Dict[str, Any]]

    # ── Sales Intelligence ────────────────────────────────────────────────
    sales_intelligence: List[SalesIntelligence]
    icp_match_signals: List[str]            # signal_ids most relevant to ICP

    # ── Executive Briefing ────────────────────────────────────────────────
    executive_briefing_daily: List[ExecutiveBriefingItem]
    executive_briefing_weekly: Optional[Dict[str, Any]]
    executive_briefing_monthly: Optional[Dict[str, Any]]
    top_risks: List[str]
    top_opportunities: List[str]
    recommended_actions: List[Dict[str, str]]

    # ── QA ────────────────────────────────────────────────────────────────
    qa_results: List[QAResult]
    qa_passed: bool
    qa_blockers: List[str]

    # ── Repository / Knowledge Base ───────────────────────────────────────
    repository_ids: List[str]        # IDs of items persisted to Supabase
    knowledge_graph_updated: bool

    # ── Recommendations ───────────────────────────────────────────────────
    recommendations: Dict[str, List[Dict[str, Any]]]
    # keys: marketing | sales | leadership | cs | product

    # ── Error Handling ────────────────────────────────────────────────────
    errors: List[Dict[str, str]]     # {node, error, timestamp}
    retry_count: Dict[str, int]      # node → retry count
    node_timings: Dict[str, float]   # node → elapsed seconds
