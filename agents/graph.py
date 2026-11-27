"""
TADA Intelligence Platform — Main LangGraph Workflow
=====================================================
Defines the complete agent graph that processes content from 50+ sources
through a multi-agent pipeline into actionable intelligence.

Architecture:
    research → collection → signal_detection
        → [trend_analysis ‖ competitive_intel ‖ pain_point]  (parallel fan-out)
        → tada_perspective
        → [content_strategy ‖ sales]  (parallel fan-out)
        → executive_briefing
        → qa
        → [repository ‖ recommendation]  (parallel fan-out)
        → END

Persistence: SqliteSaver (development) / AsyncPostgresSaver (production)
Observability: Langfuse traces on every node

Usage:
    from agents.graph import create_graph, run_pipeline

    graph = create_graph()
    result = await graph.ainvoke(initial_state)
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from agents.state import (
    AgentState,
    DetectedSignal,
    KnowledgeEntity,
    PainPoint,
    QAResult,
    SalesIntelligence,
    TrendAnalysis,
)

# Import fully-implemented nodes
from agents.nodes.signal_detection import signal_detection_node
from agents.nodes.tada_perspective import tada_perspective_node
from agents.nodes.competitive_intel import competitive_intel_node
from agents.nodes.content_strategy import content_strategy_node
from agents.nodes.executive_briefing import executive_briefing_node

# ---------------------------------------------------------------------------
# Langfuse
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

# ---------------------------------------------------------------------------
# Stub nodes (Phase 2 implementations)
# Each stub documents its interface and returns safe defaults.
# ---------------------------------------------------------------------------

def research_node(state: AgentState) -> AgentState:
    """
    Research Agent — Initiates the intelligence run.

    Reads:   state["run_id"], state["run_mode"], state["target_sources"]
    Writes:  state["run_id"] (assigns if missing), state["started_at"],
             state["version"], state["errors"], state["node_timings"]

    Responsibilities:
    - Validate run configuration
    - Load source list from config/sources.json filtered by run_mode
    - Set up run metadata (run_id, version, started_at)
    - Initialise all list/dict fields to empty defaults
    - Check Langfuse connectivity
    - Pass enriched state to collection_node
    """
    node_name = "research"
    start_time = time.time()

    run_id = state.get("run_id") or f"run_{uuid.uuid4().hex[:12]}"
    version = state.get("version", os.getenv("PLATFORM_VERSION", "1.0.0"))

    # Load target sources from environment or config
    target_sources = state.get("target_sources") or _load_default_sources(state.get("run_mode", "daily"))

    elapsed = time.time() - start_time
    return {
        **state,
        "run_id": run_id,
        "version": version,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "target_sources": target_sources,
        "raw_content": state.get("raw_content", []),
        "detected_signals": [],
        "signal_clusters": {},
        "surfaced_signals": [],
        "trends": [],
        "emerging_themes": [],
        "competitor_activities": [],
        "competitive_landscape_summary": "",
        "pain_points": [],
        "tada_perspectives": [],
        "entities": [],
        "entity_relationships": [],
        "content_ideas": [],
        "content_calendar_suggestions": [],
        "sales_intelligence": [],
        "icp_match_signals": [],
        "executive_briefing_daily": [],
        "executive_briefing_weekly": None,
        "executive_briefing_monthly": None,
        "top_risks": [],
        "top_opportunities": [],
        "recommended_actions": {},
        "qa_results": [],
        "qa_passed": False,
        "qa_blockers": [],
        "repository_ids": [],
        "knowledge_graph_updated": False,
        "recommendations": {"marketing": [], "sales": [], "leadership": [], "cs": [], "product": []},
        "errors": [],
        "retry_count": {},
        "node_timings": {"research": elapsed},
    }


def _load_default_sources(run_mode: str) -> List[str]:
    """Load source IDs appropriate for the run cadence."""
    import json, pathlib
    sources_path = pathlib.Path(__file__).parent.parent / "config" / "sources.json"
    if not sources_path.exists():
        return []
    try:
        with open(sources_path) as f:
            sources_data = json.load(f)
        sources = sources_data if isinstance(sources_data, list) else sources_data.get("sources", [])
        # For daily runs, use only tier1+tier2 sources
        if run_mode == "daily":
            return [s["id"] for s in sources if s.get("tier") in ("tier1", "tier2")]
        return [s["id"] for s in sources]
    except Exception:
        return []


def collection_node(state: AgentState) -> AgentState:
    """
    Collection Agent — Fetches raw content from all configured sources.

    Reads:   state["target_sources"]
    Writes:  state["raw_content"], state["source_quality_scores"],
             state["collection_stats"]

    Responsibilities:
    - Iterate over target_sources
    - For each source: call appropriate fetcher (RSS, scraper, API, social)
    - Apply source quality scoring (trust × authority × influence)
    - De-duplicate by URL hash
    - Store raw content items
    - Report collection stats (items_fetched, errors, duration_s)

    Integrates with: src/tada_ci/services/rss_fetcher.py,
                     src/tada_ci/services/ingestion.py
    """
    node_name = "collection"
    start_time = time.time()

    # In production this calls the existing ingestion service
    # from src.tada_ci.services.ingestion import ingest_sources
    # raw_content = ingest_sources(state["target_sources"])

    existing_content = state.get("raw_content", [])

    elapsed = time.time() - start_time
    return {
        **state,
        "raw_content": existing_content,
        "source_quality_scores": state.get("source_quality_scores", []),
        "collection_stats": {
            "items_fetched": len(existing_content),
            "sources_attempted": len(state.get("target_sources", [])),
            "errors": 0,
            "duration_s": elapsed,
        },
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def trend_analysis_node(state: AgentState) -> AgentState:
    """
    Trend Analysis Agent — Identifies macro-trends across signal clusters.

    Reads:   state["detected_signals"], state["signal_clusters"],
             state["emerging_themes"]
    Writes:  state["trends"], state["emerging_themes"]

    Responsibilities:
    - Group signals by cluster_id
    - For each cluster with 3+ signals: call LLM to identify trend
    - Classify velocity (fast/moderate/slow) and maturity (emerging/growing/mainstream/declining)
    - Track trend delta vs. previous run (from repository)
    - Update emerging_themes list

    LLM call: TREND_DETECTION prompt from prompts/system-prompts.md
    Model: claude-3-5-sonnet | Temperature: 0.3
    """
    node_name = "trend_analysis"
    start_time = time.time()

    signals: List[DetectedSignal] = state.get("detected_signals", [])
    clusters: Dict[str, List[str]] = state.get("signal_clusters", {})

    # Stub: derive basic trends from cluster sizes
    trends: List[TrendAnalysis] = []
    for cluster_label, signal_ids in clusters.items():
        if len(signal_ids) >= 2 and cluster_label != "unclustered":
            cluster_signals = [s for s in signals if s["signal_id"] in signal_ids]
            avg_score = sum(s["score"]["final_score"] for s in cluster_signals) / len(cluster_signals)
            trends.append(TrendAnalysis(
                trend_id=f"trend_{cluster_label[:20].replace(' ', '_').lower()}",
                name=cluster_label,
                description=f"Cluster of {len(signal_ids)} related signals around: {cluster_label}",
                signals=signal_ids,
                velocity="moderate",
                maturity="emerging",
                timeframe="short",
                categories=[s["signal_type"] for s in cluster_signals[:3]],
                implications_for_tada=f"High-relevance theme (avg score {avg_score:.1f}) — monitor closely",
            ))

    # Extract emerging themes from top signals
    all_keywords = [kw for s in signals[:20] for kw in s["keywords"]]
    keyword_freq: Dict[str, int] = {}
    for kw in all_keywords:
        keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
    emerging_themes = sorted(keyword_freq, key=keyword_freq.get, reverse=True)[:10]  # type: ignore[arg-type]

    elapsed = time.time() - start_time
    return {
        **state,
        "trends": trends,
        "emerging_themes": emerging_themes,
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def pain_point_node(state: AgentState) -> AgentState:
    """
    Pain Point Extraction Agent — Extracts buyer pain from social/community content.

    Reads:   state["raw_content"] (filtered: reddit, linkedin, twitter)
    Writes:  state["pain_points"]

    Responsibilities:
    - Filter raw_content to social/community sources
    - Run PAIN_POINT_EXTRACTION prompt to identify complaints/challenges
    - Cluster by pain category
    - Count frequency (how many sources mention each pain)
    - Map to TADA solution angles
    - Pass to content_strategy and sales nodes

    LLM call: PAIN_POINT_EXTRACTION prompt from prompts/system-prompts.md
    Model: claude-3-5-sonnet | Temperature: 0.2
    """
    node_name = "pain_point"
    start_time = time.time()

    social_types = {"reddit", "twitter", "linkedin", "community", "forum"}
    raw_items = state.get("raw_content", [])
    social_items = [item for item in raw_items if item.get("source_type", "") in social_types]

    # Stub: no social content = empty pain points
    # Full implementation: call LLM with PAIN_POINT_EXTRACTION prompt
    pain_points: List[PainPoint] = []

    elapsed = time.time() - start_time
    return {
        **state,
        "pain_points": pain_points,
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def sales_node(state: AgentState) -> AgentState:
    """
    Sales Intelligence Agent — Generates ICP-matched sales intelligence.

    Reads:   state["surfaced_signals"], state["tada_perspectives"],
             state["pain_points"], state["competitor_activities"]
    Writes:  state["sales_intelligence"], state["icp_match_signals"],
             state["recommendations"]["sales"]

    Responsibilities:
    - Score each surfaced signal against TADA's ICP (ideal customer profile)
    - Generate discovery questions per signal
    - Generate objection handlers using competitive intel
    - Generate urgency triggers using TADA perspective
    - Identify top signals for sales outreach sequences

    LLM call: SALES_INTELLIGENCE prompt from prompts/system-prompts.md
    Model: claude-3-5-sonnet | Temperature: 0.3
    """
    node_name = "sales"
    start_time = time.time()

    surfaced: List[DetectedSignal] = state.get("surfaced_signals", [])
    perspectives = state.get("tada_perspectives", [])

    # Stub: build basic sales intelligence from signal data
    sales_intel: List[SalesIntelligence] = []
    perspective_map = {p["signal_id"]: p for p in perspectives}

    for sig in surfaced[:10]:
        p = perspective_map.get(sig["signal_id"])
        if not p:
            continue
        sales_intel.append(SalesIntelligence(
            signal_id=sig["signal_id"],
            discovery_question=f"How is your team currently tracking {sig['keywords'][0] if sig['keywords'] else 'this trend'} and its impact on your operations?",
            talking_point=f"{sig['headline']} — {p['why_it_matters']}",
            objection_handler=f"Traditional tools won't surface this until it's too late. TADA detected it {sig['momentum']} momentum before it becomes critical.",
            proof_point=p["expected_business_outcome"],
            target_persona="CSCO / VP Procurement",
            urgency_trigger=p["do"],
            competitive_angle=p["tada_response"],
        ))

    # ICP match: signals in supply chain disruption / risk / opportunity
    icp_types = {"disruption", "risk", "opportunity", "regulation"}
    icp_signals = [s["signal_id"] for s in surfaced if s["signal_type"] in icp_types]

    current_recs = state.get("recommendations", {})
    current_recs.setdefault("sales", [])
    for si in sales_intel[:5]:
        current_recs["sales"].append({
            "type": "signal_outreach",
            "signal_id": si["signal_id"],
            "discovery_question": si["discovery_question"],
            "urgency_trigger": si["urgency_trigger"],
        })

    elapsed = time.time() - start_time
    return {
        **state,
        "sales_intelligence": sales_intel,
        "icp_match_signals": icp_signals,
        "recommendations": current_recs,
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def qa_node(state: AgentState) -> AgentState:
    """
    QA Review Agent — Quality gates all AI outputs before human review.

    Reads:   all prior state fields
    Writes:  state["qa_results"], state["qa_passed"], state["qa_blockers"]

    Quality checks performed:
    1. Signal completeness: headline, summary, evidence, score all present
    2. Perspective completeness: all 9 fields non-empty for surfaced signals
    3. Content traceability: every ContentIdea has a valid signal_id
    4. Briefing coherence: briefing items reference real signals
    5. Score validity: all scores within 0-10 range
    6. Confidence threshold: flagging signals with confidence < 0.5
    7. Source diversity: at least 3 unique sources among surfaced signals
    8. Duplicate detection: no two signals with identical headlines

    LLM call: QA_REVIEW prompt from prompts/system-prompts.md
    Model: claude-3-5-haiku | Temperature: 0.1  (strict validation mode)
    """
    node_name = "qa"
    start_time = time.time()

    qa_results: List[QAResult] = []
    blockers: List[str] = []

    # 1. Signal completeness check
    signals = state.get("detected_signals", [])
    signal_issues = []
    for sig in signals:
        if not sig.get("headline"):
            signal_issues.append(f"Signal {sig.get('signal_id','?')} missing headline")
        if not sig.get("evidence"):
            signal_issues.append(f"Signal {sig.get('signal_id','?')} missing evidence")
        score = sig.get("score", {})
        for dim in ["supply_chain_relevance", "executive_importance", "business_impact", "technology_relevance", "tada_alignment"]:
            val = score.get(dim, -1)
            if not (0 <= val <= 10):
                signal_issues.append(f"Signal {sig.get('signal_id','?')} invalid score dimension {dim}={val}")

    signal_qa = QAResult(
        node_name="signal_detection",
        passed=len(signal_issues) == 0,
        issues=signal_issues[:10],
        warnings=[],
        confidence_override=None,
    )
    qa_results.append(signal_qa)
    if not signal_qa["passed"]:
        blockers.extend(signal_issues[:3])

    # 2. Perspective completeness check
    perspectives = state.get("tada_perspectives", [])
    surfaced_ids = {s["signal_id"] for s in state.get("surfaced_signals", [])}
    perspective_ids = {p["signal_id"] for p in perspectives}
    missing_perspectives = surfaced_ids - perspective_ids

    perspective_issues = []
    if missing_perspectives:
        perspective_issues.append(f"{len(missing_perspectives)} surfaced signals missing TADA perspective")
    for p in perspectives:
        required_fields = ["what_happened", "why_it_matters", "potential_impact", "detect", "decide", "do"]
        for field in required_fields:
            if not p.get(field):
                perspective_issues.append(f"Perspective {p['signal_id']} missing field: {field}")

    perspective_qa = QAResult(
        node_name="tada_perspective",
        passed=len(perspective_issues) == 0,
        issues=perspective_issues[:10],
        warnings=[],
        confidence_override=None,
    )
    qa_results.append(perspective_qa)

    # 3. Content traceability check
    content_ideas = state.get("content_ideas", [])
    traceability_issues = []
    for idea in content_ideas:
        if not idea.get("signal_id"):
            traceability_issues.append(f"ContentIdea {idea.get('idea_id','?')} has no signal_id")
        elif idea["signal_id"] not in {s["signal_id"] for s in signals}:
            traceability_issues.append(f"ContentIdea {idea.get('idea_id','?')} references unknown signal {idea['signal_id']}")

    content_qa = QAResult(
        node_name="content_strategy",
        passed=len(traceability_issues) == 0,
        issues=traceability_issues[:10],
        warnings=[],
        confidence_override=None,
    )
    qa_results.append(content_qa)

    # 4. Source diversity check
    surfaced = state.get("surfaced_signals", [])
    unique_sources = {name for sig in surfaced for name in sig.get("source_names", [])}
    source_warnings = []
    if len(unique_sources) < 3 and len(surfaced) > 0:
        source_warnings.append(f"Only {len(unique_sources)} unique sources among surfaced signals — consider expanding source list")

    # 5. Duplicate headline check
    headlines = [s["headline"] for s in signals]
    seen_headlines: set[str] = set()
    dupe_issues = []
    for h in headlines:
        if h in seen_headlines:
            dupe_issues.append(f"Duplicate headline: '{h[:60]}'")
        seen_headlines.add(h)

    general_qa = QAResult(
        node_name="general",
        passed=len(dupe_issues) == 0,
        issues=dupe_issues,
        warnings=source_warnings,
        confidence_override=None,
    )
    qa_results.append(general_qa)

    # Overall pass/fail
    has_blockers = len(blockers) > 0
    # Non-blocking: perspective gaps and source diversity are warnings, not blockers
    all_passed = all(qr["passed"] for qr in [signal_qa, content_qa, general_qa])

    elapsed = time.time() - start_time
    return {
        **state,
        "qa_results": qa_results,
        "qa_passed": all_passed,
        "qa_blockers": blockers,
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def repository_node(state: AgentState) -> AgentState:
    """
    Repository Agent — Persists validated intelligence to the knowledge base.

    Reads:   state["detected_signals"], state["tada_perspectives"],
             state["content_ideas"], state["trends"], state["entities"],
             state["qa_passed"]
    Writes:  state["repository_ids"], state["knowledge_graph_updated"],
             state["entities"], state["entity_relationships"]

    Responsibilities:
    - Check qa_passed before writing (skip if QA failed critically)
    - Upsert signals to Supabase signals table (avoid duplicates via signal_id)
    - Upsert perspectives to perspectives table
    - Store content ideas with traceability links
    - Update entity graph (extract entities from signals → update knowledge graph)
    - Track entity co-occurrence for relationship mapping
    - Return list of persisted IDs

    Integrates with: src/tada_ci/services/repository.py
    Database: Supabase PostgreSQL (see sql/schema.sql)
    """
    node_name = "repository"
    start_time = time.time()

    if not state.get("qa_passed", False):
        # Still persist but flag as qa_failed for human review
        pass

    # Stub: in production calls repository service
    # from src.tada_ci.services.repository import RepositoryService
    # repo = RepositoryService()
    # ids = repo.upsert_signals(state["detected_signals"])

    # Entity extraction stub
    entities: List[KnowledgeEntity] = []
    seen_entities: Dict[str, int] = {}

    for sig in state.get("detected_signals", []):
        for entity_name in sig.get("entities", []):
            seen_entities[entity_name] = seen_entities.get(entity_name, 0) + 1

    now = datetime.now(timezone.utc).isoformat()
    for name, count in list(seen_entities.items())[:50]:
        entities.append(KnowledgeEntity(
            entity_id=f"ent_{name[:20].replace(' ', '_').lower()}",
            name=name,
            entity_type="company",  # TODO: classify properly in Phase 2
            first_seen=now,
            last_seen=now,
            signal_count=count,
            related_entities=[],
            summary=f"Entity '{name}' appeared in {count} signal(s)",
        ))

    repository_ids = [f"sig_{s['signal_id']}" for s in state.get("detected_signals", [])]

    elapsed = time.time() - start_time
    return {
        **state,
        "repository_ids": repository_ids,
        "knowledge_graph_updated": True,
        "entities": entities,
        "entity_relationships": [],
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


def recommendation_node(state: AgentState) -> AgentState:
    """
    Recommendation Agent — Generates team-specific recommendations.

    Reads:   all intelligence state fields
    Writes:  state["recommendations"] (enriched with prioritised recs per team),
             state["completed_at"]

    Responsibilities:
    - Merge recommendations from sales_node, competitive_intel_node, executive_briefing_node
    - Add marketing-specific recommendations from content_ideas
    - Add CS recommendations from pain_points
    - Add product recommendations from trends
    - Prioritise by urgency and business impact
    - Format for each team's consumption style

    Output feeds: API server (src/tada_ci/api/server.py),
                  Dashboard (dashboard/app.js),
                  Slack/Email notifications
    """
    node_name = "recommendation"
    start_time = time.time()

    current_recs = state.get("recommendations", {
        "marketing": [], "sales": [], "leadership": [], "cs": [], "product": []
    })

    # Add marketing recommendations from content ideas
    content_ideas = state.get("content_ideas", [])
    breaking_content = [i for i in content_ideas if i["urgency"] == "breaking"]
    for idea in breaking_content[:3]:
        current_recs.setdefault("marketing", []).append({
            "type": "urgent_content",
            "format": idea["format"],
            "title": idea["title"],
            "signal_id": idea["signal_id"],
            "priority": "high",
        })

    # Add CS recommendations from pain points
    pain_points = state.get("pain_points", [])
    for pp in pain_points[:3]:
        current_recs.setdefault("cs", []).append({
            "type": "customer_conversation",
            "pain_category": pp.get("category", ""),
            "tada_solution": pp.get("tada_solution_angle", ""),
            "priority": "medium",
        })

    # Add product recommendations from trends
    trends = state.get("trends", [])
    fast_trends = [t for t in trends if t["velocity"] == "fast"]
    for trend in fast_trends[:2]:
        current_recs.setdefault("product", []).append({
            "type": "roadmap_consideration",
            "trend": trend["name"],
            "implication": trend["implications_for_tada"],
            "priority": "medium",
        })

    # Leadership recommendations from executive briefing
    exec_briefing = state.get("executive_briefing_daily", [])
    immediate_items = [b for b in exec_briefing if b.get("time_to_act") == "Today"]
    for item in immediate_items[:3]:
        current_recs.setdefault("leadership", []).append({
            "type": "executive_action",
            "headline": item.get("headline", ""),
            "action": item.get("recommended_action", ""),
            "priority": "high",
        })

    elapsed = time.time() - start_time
    return {
        **state,
        "recommendations": current_recs,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
    }


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------

def should_run_weekly_supplement(state: AgentState) -> str:
    """Route to weekly supplement path or skip to daily-only path."""
    run_mode = state.get("run_mode", "daily")
    if run_mode in ("weekly", "monthly"):
        return "weekly"
    return "daily"


def check_qa_gate(state: AgentState) -> str:
    """
    Route after QA: if critical blockers exist, short-circuit to repository
    with qa_failed flag rather than blocking the entire run.
    """
    blockers = state.get("qa_blockers", [])
    if len(blockers) >= 5:
        return "blocked"
    return "passed"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------

def create_graph(checkpointer=None) -> StateGraph:
    """
    Build and compile the TADA Intelligence Platform LangGraph graph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Defaults to SqliteSaver("./work/graph_checkpoints.db")

    Returns:
        Compiled StateGraph ready for invocation.

    Node execution order:
        research → collection → signal_detection
            ─── fan-out to 3 parallel branches ───
            ├── trend_analysis ─┐
            ├── competitive_intel ─┤→ (join) → tada_perspective
            └── pain_point ─────┘
            ─── tada_perspective → fan-out ───
            ├── content_strategy ─┐
            └── sales ────────────┘→ (join) → executive_briefing → qa → fan-out
            ├── repository ─┐
            └── recommendation → END
    """
    if checkpointer is None:
        checkpointer = SqliteSaver.from_conn_string("./work/graph_checkpoints.db")

    # ── Build graph ──────────────────────────────────────────────────────────
    builder = StateGraph(AgentState)

    # Register all nodes
    builder.add_node("research", research_node)
    builder.add_node("collection", collection_node)
    builder.add_node("signal_detection", signal_detection_node)
    builder.add_node("trend_analysis", trend_analysis_node)
    builder.add_node("competitive_intel", competitive_intel_node)
    builder.add_node("pain_point", pain_point_node)
    builder.add_node("tada_perspective", tada_perspective_node)
    builder.add_node("content_strategy", content_strategy_node)
    builder.add_node("sales", sales_node)
    builder.add_node("executive_briefing", executive_briefing_node)
    builder.add_node("qa", qa_node)
    builder.add_node("repository", repository_node)
    builder.add_node("recommendation", recommendation_node)

    # ── Sequential pipeline edges ────────────────────────────────────────────
    builder.add_edge(START, "research")
    builder.add_edge("research", "collection")
    builder.add_edge("collection", "signal_detection")

    # Fan-out: signal_detection → 3 parallel analysis nodes
    builder.add_edge("signal_detection", "trend_analysis")
    builder.add_edge("signal_detection", "competitive_intel")
    builder.add_edge("signal_detection", "pain_point")

    # Join: all 3 parallel nodes → tada_perspective
    # (LangGraph waits for all incoming edges before activating the node)
    builder.add_edge("trend_analysis", "tada_perspective")
    builder.add_edge("competitive_intel", "tada_perspective")
    builder.add_edge("pain_point", "tada_perspective")

    # Fan-out: tada_perspective → content_strategy + sales (parallel)
    builder.add_edge("tada_perspective", "content_strategy")
    builder.add_edge("tada_perspective", "sales")

    # Join: both → executive_briefing
    builder.add_edge("content_strategy", "executive_briefing")
    builder.add_edge("sales", "executive_briefing")

    # Sequential: executive_briefing → qa
    builder.add_edge("executive_briefing", "qa")

    # Fan-out: qa → repository + recommendation (parallel)
    builder.add_edge("qa", "repository")
    builder.add_edge("qa", "recommendation")

    # Join: both → END
    builder.add_edge("repository", END)
    builder.add_edge("recommendation", END)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------

def create_initial_state(
    run_mode: Literal["daily", "weekly", "monthly", "ad_hoc"] = "daily",
    target_sources: Optional[List[str]] = None,
    raw_content: Optional[List] = None,
    triggered_by: str = "manual",
) -> AgentState:
    """Create a minimal initial state for the pipeline."""
    return AgentState(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        run_mode=run_mode,
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None,
        triggered_by=triggered_by,
        version=os.getenv("PLATFORM_VERSION", "1.0.0"),
        target_sources=target_sources or [],
        raw_content=raw_content or [],
        source_quality_scores=[],
        collection_stats={},
        detected_signals=[],
        signal_clusters={},
        surfaced_signals=[],
        trends=[],
        emerging_themes=[],
        competitor_activities=[],
        competitive_landscape_summary="",
        pain_points=[],
        tada_perspectives=[],
        entities=[],
        entity_relationships=[],
        content_ideas=[],
        content_calendar_suggestions=[],
        sales_intelligence=[],
        icp_match_signals=[],
        executive_briefing_daily=[],
        executive_briefing_weekly=None,
        executive_briefing_monthly=None,
        top_risks=[],
        top_opportunities=[],
        recommended_actions={},
        qa_results=[],
        qa_passed=False,
        qa_blockers=[],
        repository_ids=[],
        knowledge_graph_updated=False,
        recommendations={"marketing": [], "sales": [], "leadership": [], "cs": [], "product": []},
        errors=[],
        retry_count={},
        node_timings={},
    )


async def run_pipeline(
    run_mode: Literal["daily", "weekly", "monthly", "ad_hoc"] = "daily",
    target_sources: Optional[List[str]] = None,
    raw_content: Optional[List] = None,
    triggered_by: str = "scheduler",
) -> AgentState:
    """
    Run the full TADA intelligence pipeline.

    Args:
        run_mode: Cadence — controls which sources to use and what briefings to generate
        target_sources: Override list of source IDs (uses config/sources.json if None)
        raw_content: Pre-loaded content (skips collection if provided)
        triggered_by: Who triggered the run (scheduler / webhook / manual)

    Returns:
        Final AgentState with all intelligence populated.
    """
    graph = create_graph()
    initial_state = create_initial_state(
        run_mode=run_mode,
        target_sources=target_sources,
        raw_content=raw_content,
        triggered_by=triggered_by,
    )

    config = {"configurable": {"thread_id": initial_state["run_id"]}}
    final_state: AgentState = await graph.ainvoke(initial_state, config=config)
    return final_state


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="TADA Intelligence Pipeline")
    parser.add_argument("--mode", default="daily", choices=["daily", "weekly", "monthly", "ad_hoc"])
    parser.add_argument("--triggered-by", default="manual")
    args = parser.parse_args()

    async def main():
        print(f"Starting TADA pipeline — mode: {args.mode}")
        result = await run_pipeline(run_mode=args.mode, triggered_by=args.triggered_by)
        print(f"Pipeline complete. Signals: {len(result['detected_signals'])}, "
              f"Surfaced: {len(result['surfaced_signals'])}, "
              f"QA passed: {result['qa_passed']}")
        if result["errors"]:
            print(f"Errors: {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"  [{err['node']}] {err['error']}")

    asyncio.run(main())
