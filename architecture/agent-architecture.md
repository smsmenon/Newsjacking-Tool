# TADA Content Intelligence Platform — AI Agent Architecture

**Version:** 1.0.0
**Date:** 2026-06-16

This document defines all 13 specialized AI agents that power the TADA intelligence pipeline. Each agent is built with LangGraph, runs as a stateful graph with checkpointing, and communicates with others through the shared PostgreSQL state store and FastAPI event bus.

---

## Agent Framework Conventions

### Base Agent Structure

Every agent follows this structure:

```python
# apps/agents/src/tada_agents/agents/base.py

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    """Base state shared across all agent graphs."""
    run_id: str                          # Unique run identifier
    triggered_by: str                    # "cron" | "webhook" | "api" | "agent"
    input: dict                          # Agent-specific input
    output: dict                         # Agent-specific output
    errors: Annotated[list, operator.add] # Accumulated errors
    metadata: dict                       # Timing, token counts, etc.

class BaseAgent:
    def __init__(self, agent_name: str, model: str = "gpt-4o"):
        self.name = agent_name
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.langfuse = Langfuse()
        self.trace = None

    def start_trace(self, run_id: str, input: dict):
        self.trace = self.langfuse.trace(
            name=self.name,
            id=run_id,
            input=input,
            tags=["tada", self.name]
        )

    def end_trace(self, output: dict):
        if self.trace:
            self.trace.update(output=output)
```

### Inter-Agent Communication Pattern

Agents communicate through three mechanisms:

1. **Database state** — Agent A writes to PostgreSQL; Agent B reads on next graph step
2. **n8n webhook triggers** — n8n calls FastAPI `/webhooks/n8n` which spawns next agent
3. **Direct graph chaining** — Within a single LangGraph graph, nodes call other nodes

### LLM Assignment Policy

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| Complex reasoning (perspective, strategy) | `gpt-4o` | Quality critical |
| Extraction, classification, summarization | `gpt-4o-mini` | Cost-efficient |
| Embeddings | `text-embedding-3-large` | Best semantic fidelity |
| Long-form document processing | `gpt-4o` with 128k context | PDF, transcripts |

---

## Agent 1: Collection Agent

**Role:** The ingestion workhorse. Fetches raw content from all 50+ configured sources on schedule, deduplicates, validates, and hands off to the extraction pipeline.

**Trigger Conditions:**
- n8n cron: every 15 minutes for RSS/API sources
- n8n cron: every 4 hours for web scraping targets
- n8n cron: every 30 minutes for social media sources
- Manual API trigger: `POST /agents/run?agent=collection&source_id={id}`

**Input:**
```python
{
    "source_ids": ["uuid", ...],   # Specific sources or empty for "all active"
    "since": "2026-06-16T00:00:00Z",  # Fetch since timestamp
    "max_items_per_source": 50
}
```

**Output:**
```python
{
    "items_fetched": 342,
    "items_new": 87,
    "items_duplicate": 255,
    "items_quarantined": 12,
    "raw_content_ids": ["uuid", ...],  # New items queued for extraction
    "source_health": {
        "source_uuid": {"status": "ok", "latency_ms": 234},
        ...
    }
}
```

**Tools:**
- `fetch_rss(url, since)` → list of items
- `fetch_api(endpoint, params, auth)` → list of items
- `scrape_web(url, selector)` → structured content (Playwright)
- `fetch_social(platform, query, since)` → list of posts
- `transcribe_audio(url)` → text (Whisper API)
- `extract_pdf(url)` → text (pdfplumber)
- `fingerprint_check(sha256)` → bool (already seen?)
- `store_raw_content(item, source_id)` → raw_content_id

**LangGraph Definition:**
```python
from langgraph.graph import StateGraph, END

class CollectionState(AgentState):
    sources: list[dict]
    current_source_index: int
    fetched_items: list[dict]
    new_item_ids: list[str]

def collection_graph():
    graph = StateGraph(CollectionState)

    graph.add_node("load_sources", load_active_sources)
    graph.add_node("fetch_source", fetch_single_source)
    graph.add_node("deduplicate", check_fingerprints)
    graph.add_node("quality_gate", apply_source_quality_score)
    graph.add_node("store_content", persist_raw_content)
    graph.add_node("trigger_extraction", emit_extraction_webhook)

    graph.set_entry_point("load_sources")
    graph.add_edge("load_sources", "fetch_source")
    graph.add_conditional_edges(
        "fetch_source",
        route_source_type,  # rss | api | web | social | audio | pdf
        {
            "rss": "deduplicate",
            "api": "deduplicate",
            "web": "deduplicate",
            "social": "deduplicate",
            "audio": "deduplicate",
            "pdf": "deduplicate",
            "done": "trigger_extraction"
        }
    )
    graph.add_edge("deduplicate", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        lambda s: "store" if s["quality_score"] >= 40 else "quarantine",
        {"store": "store_content", "quarantine": "fetch_source"}
    )
    graph.add_edge("store_content", "fetch_source")
    graph.add_edge("trigger_extraction", END)

    return graph.compile(checkpointer=postgres_checkpointer)
```

**Error Handling:** Failed source fetches logged with retry count. After 3 failures, source flagged as `degraded`. Source health dashboard updated.

---

## Agent 2: Research Agent

**Role:** Deep-dive researcher invoked on demand. Unlike the Collection Agent (breadth), the Research Agent goes deep on a specific topic, company, or question.

**Trigger Conditions:**
- Manual API trigger: `POST /agents/run?agent=research&topic={topic}`
- Invoked by Signal Detection Agent when signal lacks sufficient context
- Invoked by Executive Briefing Agent for background enrichment

**Input:**
```python
{
    "topic": "string",             # What to research
    "depth": "shallow|deep",       # shallow: 5 sources, deep: 20+ sources
    "context": "string",           # Why this research is needed
    "existing_signal_id": "uuid"   # Optional: enrich existing signal
}
```

**Output:**
```python
{
    "research_summary": "string",
    "key_findings": ["string", ...],
    "sources_consulted": [{"url": "...", "title": "...", "relevance": 0.87}, ...],
    "entities_discovered": [{"name": "...", "type": "company|person|product"}],
    "related_signal_ids": ["uuid", ...],
    "content_item_ids": ["uuid", ...]  # Stored in knowledge base
}
```

**Tools:**
- `web_search(query, num_results)` → search results
- `read_page(url)` → full page content
- `semantic_search_knowledge(query, top_k)` → existing knowledge
- `fetch_pdf(url)` → document text
- `extract_entities(text)` → entity list
- `store_research_content(content, topic)` → content_item_id

**LangGraph Definition:**
```python
class ResearchState(AgentState):
    topic: str
    depth: str
    search_results: list[dict]
    pages_read: list[dict]
    findings: list[str]
    entities: list[dict]

def research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("plan_research", create_research_plan)      # LLM: plan queries
    graph.add_node("search_web", execute_searches)             # Tool: web_search
    graph.add_node("read_pages", fetch_page_content)           # Tool: read_page
    graph.add_node("search_existing", query_knowledge_base)    # Tool: semantic_search
    graph.add_node("synthesize", synthesize_findings)          # LLM: gpt-4o synthesis
    graph.add_node("extract_entities", run_entity_extraction)  # LLM: entity extraction
    graph.add_node("store_results", persist_research)          # Tool: store content

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "search_existing")
    graph.add_edge("search_existing", "search_web")
    graph.add_edge("search_web", "read_pages")
    graph.add_edge("read_pages", "synthesize")
    graph.add_edge("synthesize", "extract_entities")
    graph.add_edge("extract_entities", "store_results")
    graph.add_edge("store_results", END)

    return graph.compile(checkpointer=postgres_checkpointer)
```

---

## Agent 3: Signal Detection Agent

**Role:** The core intelligence engine. Analyzes structured content items to detect meaningful market signals — events, trends, disruptions, risks, and opportunities. The most critical agent in the pipeline.

**Trigger Conditions:**
- Webhook from Collection Agent after new content is stored
- Batch job: every 60 minutes processes any unprocessed content items

**Input:**
```python
{
    "content_item_ids": ["uuid", ...],
    "batch_size": 50
}
```

**Output:**
```python
{
    "signals_detected": [
        {
            "content_item_id": "uuid",
            "signal_type": "funding|acquisition|product_launch|regulation|executive_change|market_shift|risk|opportunity",
            "event_category": "string",
            "detection_confidence": 0.87,
            "signal_summary": "string",
            "key_entities": ["company_name", "person_name"],
            "signal_id": "uuid"   # Stored in DB
        }
    ],
    "items_processed": 50,
    "signals_found": 8,
    "low_confidence_count": 3
}
```

**Tools:**
- `classify_signal_type(text, entities)` → signal_type + confidence
- `detect_anomaly(content_item_id, baseline_window_days)` → anomaly_score
- `match_signal_pattern(embedding, pattern_library)` → match_score
- `query_entity_history(entity_name, lookback_days)` → history
- `store_signal(signal_data)` → signal_id
- `trigger_validation(signal_id)` → fires Multi-Source Validation

**LangGraph Definition:**
```python
class SignalDetectionState(AgentState):
    content_items: list[dict]
    current_item: dict
    detected_signals: list[dict]
    processed_count: int

def signal_detection_graph():
    graph = StateGraph(SignalDetectionState)

    graph.add_node("load_items", load_content_batch)
    graph.add_node("extract_context", build_signal_context)    # Fetch entity history
    graph.add_node("classify_type", classify_signal)           # LLM: gpt-4o-mini
    graph.add_node("anomaly_check", run_anomaly_detection)     # Statistical check
    graph.add_node("pattern_match", match_known_patterns)      # Vector similarity
    graph.add_node("compute_confidence", aggregate_confidence) # Weighted confidence
    graph.add_node("store_signal", persist_validated_signal)
    graph.add_node("trigger_downstream", fire_validation_webhook)

    graph.set_entry_point("load_items")
    graph.add_edge("load_items", "extract_context")
    graph.add_edge("extract_context", "classify_type")
    graph.add_edge("classify_type", "anomaly_check")
    graph.add_edge("anomaly_check", "pattern_match")
    graph.add_edge("pattern_match", "compute_confidence")
    graph.add_conditional_edges(
        "compute_confidence",
        lambda s: "store" if s["confidence"] >= 0.65 else "archive_low",
        {"store": "store_signal", "archive_low": "load_items"}
    )
    graph.add_edge("store_signal", "trigger_downstream")
    graph.add_edge("trigger_downstream", "load_items")

    return graph.compile(checkpointer=postgres_checkpointer)
```

---

## Agent 4: Trend Agent

**Role:** Tracks signal frequency, momentum, and velocity over time to identify emerging trends. Maintains the Trend Timeline data.

**Trigger Conditions:**
- Cron: every 60 minutes
- Triggered by Signal Detection Agent when new signal detected

**Input:**
```python
{
    "lookback_window_days": 30,
    "min_signal_count": 3,           # Minimum signals to form a trend
    "signal_ids": ["uuid", ...]      # Optional: specific signals to analyze
}
```

**Output:**
```python
{
    "trends_updated": [
        {
            "trend_id": "uuid",
            "topic": "AI in Supply Chain Visibility",
            "frequency_per_day": 4.2,
            "momentum_score": 0.73,    # 0-1, rate of change
            "velocity_score": 0.15,    # acceleration
            "direction": "rising",
            "signal_count": 28,
            "first_seen_at": "2026-05-01T00:00:00Z"
        }
    ],
    "new_trends_created": 2,
    "trends_archived": 1    # Fallen below threshold
}
```

**Tools:**
- `query_signal_frequency(topic, window_days)` → frequency data
- `compute_momentum(frequency_series)` → momentum_score
- `compute_velocity(momentum_series)` → velocity_score
- `cluster_signals_by_topic(signal_ids)` → topic clusters
- `upsert_trend(trend_data)` → trend_id
- `store_trend_datapoint(trend_id, date, count)` → void

**LangGraph Definition:**
```python
def trend_graph():
    graph = StateGraph(TrendState)

    graph.add_node("load_recent_signals", fetch_recent_signals)
    graph.add_node("cluster_topics", run_topic_clustering)     # Embeddings + k-means
    graph.add_node("compute_metrics", calculate_trend_metrics)
    graph.add_node("classify_direction", determine_trend_direction)  # LLM + heuristic
    graph.add_node("upsert_trends", save_trend_data)
    graph.add_node("archive_cold", archive_inactive_trends)

    graph.set_entry_point("load_recent_signals")
    graph.add_edge("load_recent_signals", "cluster_topics")
    graph.add_edge("cluster_topics", "compute_metrics")
    graph.add_edge("compute_metrics", "classify_direction")
    graph.add_edge("classify_direction", "upsert_trends")
    graph.add_edge("upsert_trends", "archive_cold")
    graph.add_edge("archive_cold", END)

    return graph.compile(checkpointer=postgres_checkpointer)
```

---

## Agent 5: Competitive Intelligence Agent

**Role:** Monitors competitor activity, tracks product launches, pricing changes, personnel moves, partnership announcements, and messaging shifts. Maintains competitor profiles.

**Trigger Conditions:**
- Cron: every 4 hours
- On-demand: `POST /agents/run?agent=competitive&competitor_id={id}`

**Input:**
```python
{
    "competitor_ids": ["uuid", ...],   # Empty = all active competitors
    "lookback_hours": 24
}
```

**Output:**
```python
{
    "competitor_activities": [
        {
            "competitor_id": "uuid",
            "competitor_name": "Acme Corp",
            "activity_type": "product_launch|pricing_change|partnership|exec_hire|content_publish|funding",
            "summary": "string",
            "significance": "high|medium|low",
            "source_url": "string",
            "activity_id": "uuid"
        }
    ],
    "total_activities": 12,
    "high_significance_count": 3
}
```

**Tools:**
- `search_competitor_mentions(competitor_name, lookback_hours)` → mentions
- `diff_website_content(competitor_url, previous_snapshot)` → changes
- `analyze_competitor_content(text, competitor_profile)` → activity classification
- `store_competitor_activity(activity_data)` → activity_id
- `update_competitor_profile(competitor_id, new_data)` → void

---

## Agent 6: Pain Point Agent

**Role:** Mines community platforms (Reddit, LinkedIn, Twitter/X) to detect genuine customer pain points, frustrations, unmet needs, and buying signals related to TADA's market.

**Trigger Conditions:**
- Cron: every 2 hours for Reddit and Twitter/X
- Cron: every 4 hours for LinkedIn

**Input:**
```python
{
    "platforms": ["reddit", "twitter", "linkedin"],
    "subreddits": ["supplychain", "logistics", "procurement", ...],
    "keywords": ["supply chain visibility", "inventory management", "3PL", ...],
    "lookback_hours": 4
}
```

**Output:**
```python
{
    "pain_points": [
        {
            "platform": "reddit",
            "source_url": "string",
            "pain_point_category": "visibility|cost|speed|complexity|technology|trust",
            "description": "string",
            "sentiment_score": -0.72,      # -1 to 1
            "urgency_score": 0.85,          # 0 to 1
            "company_size_signal": "enterprise|mid-market|smb|unknown",
            "buying_signal": true,
            "tada_relevance_score": 0.91
        }
    ],
    "aggregate_themes": ["lack of real-time visibility", "ERP integration failures"],
    "pain_point_count": 47
}
```

**Tools:**
- `fetch_reddit_posts(subreddits, keywords, since)` → posts + comments
- `fetch_twitter_mentions(keywords, since)` → tweets
- `fetch_linkedin_posts(keywords, since)` → posts (via Proxycurl)
- `classify_pain_point(text)` → category + urgency
- `compute_sentiment(text)` → score
- `detect_buying_signals(text, context)` → bool + signal_type
- `store_pain_point(pain_point_data)` → pain_point_id

---

## Agent 7: TADA Perspective Agent

**Role:** The most strategically important agent. Takes a validated, scored signal and generates TADA's proprietary six-part insight frame. Uses gpt-4o with carefully engineered prompts that encode TADA's voice, methodology, and market positioning.

**Trigger Conditions:**
- Webhook from Relevance Scoring service when signal score >= 45
- Manual trigger for any signal regardless of score

**Input:**
```python
{
    "signal_id": "uuid",
    "signal_data": {
        "signal_type": "string",
        "summary": "string",
        "entities": [...],
        "relevance_score": 78.4,
        "trend_context": {...},
        "pain_point_context": {...},
        "competitive_context": {...}
    },
    "reviewer_feedback": "string | null"   # Set on revision cycles
}
```

**Output:**
```python
{
    "insight_id": "uuid",
    "title": "string",
    "what_is_happening": "string",         # Clear statement of the event/shift
    "why_it_matters": "string",            # Strategic significance
    "business_impact": "string",           # Quantified/qualified impact
    "traditional_response": "string",      # How incumbents/competitors respond
    "tada_response": "string",             # TADA's differentiated positioning
    "detect_decide_do": {
        "detect": "string",                # What signal to watch
        "decide": "string",                # What decision framework to apply
        "do": "string"                     # Concrete action to take
    },
    "confidence_score": 0.88,
    "draft_status": "DRAFT"
}
```

**Tools:**
- `fetch_signal_full_context(signal_id)` → full signal + all enrichments
- `query_similar_insights(embedding, top_k)` → past insights for consistency
- `fetch_tada_positioning(topic)` → TADA's known positioning on topic
- `generate_perspective(context, feedback)` → LLM (gpt-4o) six-part frame
- `validate_ddd_consistency(detect, decide, do)` → consistency check
- `store_draft_insight(insight_data)` → insight_id
- `trigger_review_queue(insight_id)` → fires review notification

**System Prompt Architecture:**
The perspective generation uses a layered prompt:
1. **System prompt layer** — TADA's identity, voice, core values, D-D-D framework explanation
2. **Context layer** — Signal data, trend context, competitive context, pain point data
3. **Consistency layer** — Past related insights (vector search) to maintain consistency
4. **Instruction layer** — Specific output format requirements per section

**LangGraph Definition:**
```python
def perspective_graph():
    graph = StateGraph(PerspectiveState)

    graph.add_node("load_full_context", fetch_all_signal_context)
    graph.add_node("search_past_insights", semantic_search_similar)
    graph.add_node("load_tada_positioning", fetch_positioning_docs)
    graph.add_node("generate_perspective", llm_generate_six_parts)     # gpt-4o
    graph.add_node("validate_ddd", check_ddd_logical_consistency)
    graph.add_node("qa_check", invoke_qa_agent)
    graph.add_node("store_draft", persist_draft_insight)
    graph.add_node("trigger_review", notify_review_system)

    graph.set_entry_point("load_full_context")
    graph.add_edge("load_full_context", "search_past_insights")
    graph.add_edge("search_past_insights", "load_tada_positioning")
    graph.add_edge("load_tada_positioning", "generate_perspective")
    graph.add_edge("generate_perspective", "validate_ddd")
    graph.add_conditional_edges(
        "validate_ddd",
        lambda s: "qa_check" if s["ddd_consistent"] else "generate_perspective",
        {"qa_check": "qa_check", "generate_perspective": "generate_perspective"}
    )
    graph.add_edge("qa_check", "store_draft")
    graph.add_edge("store_draft", "trigger_review")
    graph.add_edge("trigger_review", END)

    return graph.compile(checkpointer=postgres_checkpointer)
```

---

## Agent 8: Content Strategy Agent

**Role:** Translates approved insights into a content strategy — mapping each insight to appropriate formats, audiences, and channels.

**Trigger Conditions:**
- Webhook from Human Review System when insight is APPROVED
- Weekly trigger for calendar planning cycle

**Input:**
```python
{
    "insight_id": "uuid",
    "insight_data": {...},
    "calendar_constraints": {
        "week_of": "2026-06-16",
        "existing_slots": [...]
    }
}
```

**Output:**
```python
{
    "content_plan": [
        {
            "content_type": "linkedin_post|article|newsletter_section|executive_briefing|sales_brief",
            "title": "string",
            "key_angle": "string",
            "target_persona": "marketing|sales|leadership|cs|product|general",
            "suggested_week": "2026-06-23",
            "priority": "high|medium|low",
            "estimated_effort": "small|medium|large",
            "outline": ["string", ...],
            "calendar_entry_id": "uuid"    # Created in DB
        }
    ]
}
```

**Tools:**
- `fetch_approved_insight(insight_id)` → full insight
- `query_calendar_availability(week_of, persona)` → available slots
- `classify_content_formats(insight_type, impact_score)` → recommended formats
- `generate_content_outline(insight, format, persona)` → outline (gpt-4o-mini)
- `store_calendar_entry(entry_data)` → calendar_entry_id

---

## Agent 9: Sales Intelligence Agent

**Role:** Extracts sales-specific intelligence from signals and insights. Generates talking points, objection-handling frameworks, competitive positioning, and opportunity signals for the sales team.

**Trigger Conditions:**
- Webhook from Recommendation Agent when insight contains high sales relevance
- Weekly trigger for sales briefing compilation

**Input:**
```python
{
    "insight_id": "uuid",
    "sales_context": {
        "active_opportunities": [...],   # Optional CRM context
        "target_industries": ["manufacturing", "retail"],
        "competitor_presence": ["Acme Corp", ...]
    }
}
```

**Output:**
```python
{
    "sales_intelligence": {
        "opportunity_signal": "string",          # Why this creates a sales opportunity
        "talking_points": ["string", ...],       # 3-5 concrete talking points
        "objection_handling": [
            {"objection": "string", "response": "string"}
        ],
        "competitive_differentiation": "string", # TADA vs. competitors in this context
        "urgency_framing": "string",             # Why act now
        "target_personas": ["string", ...],      # Who to talk to (buyer personas)
        "suggested_follow_up": "string"          # Next step recommendation
    }
}
```

**Tools:**
- `generate_talking_points(insight, sales_context)` → talking points (gpt-4o)
- `fetch_competitor_positioning(competitor_ids)` → positioning data
- `identify_urgency_triggers(signal_data)` → urgency framing
- `store_sales_intelligence(data, insight_id)` → record_id

---

## Agent 10: Executive Briefing Agent

**Role:** Compiles daily and weekly executive briefings. Aggregates top signals, risks, opportunities, and trends into a concise, action-oriented document for senior leadership.

**Trigger Conditions:**
- Cron: Daily at 7:00 AM for daily briefing
- Cron: Monday 7:00 AM for weekly briefing
- Manual: `POST /agents/run?agent=executive_briefing&type=weekly`

**Input:**
```python
{
    "briefing_type": "daily|weekly",
    "date": "2026-06-16",
    "audience": ["CEO", "CRO", "CPO"],   # Tailor to audience roles
    "lookback_days": 1                    # 1 for daily, 7 for weekly
}
```

**Output:**
```python
{
    "briefing": {
        "title": "TADA Intelligence Briefing — Week of June 16, 2026",
        "executive_summary": "string",     # 150-word max
        "top_risks": [
            {"risk": "string", "severity": "high|medium|low", "recommended_action": "string"}
        ],
        "top_opportunities": [
            {"opportunity": "string", "potential": "string", "recommended_action": "string"}
        ],
        "key_trends": [
            {"trend": "string", "momentum": "rising|stable|falling", "implication": "string"}
        ],
        "competitive_moves": [
            {"competitor": "string", "activity": "string", "implications": "string"}
        ],
        "decisions_required": [
            {"decision": "string", "urgency": "string", "context": "string"}
        ],
        "full_brief_html": "string"        # Formatted HTML for email/PDF
    },
    "insight_ids_included": ["uuid", ...],
    "briefing_id": "uuid"
}
```

**Tools:**
- `fetch_top_insights(lookback_days, top_n, min_relevance)` → insights
- `fetch_top_risks(lookback_days)` → risk signals
- `fetch_top_opportunities(lookback_days)` → opportunity signals
- `fetch_trending_topics(lookback_days)` → trending signals
- `fetch_competitor_activities(lookback_days)` → competitive moves
- `compile_briefing(sections, audience)` → LLM compilation (gpt-4o)
- `render_briefing_html(briefing_data)` → HTML string
- `store_executive_briefing(briefing)` → briefing_id

---

## Agent 11: QA Agent

**Role:** Quality assurance reviewer that validates insight accuracy, consistency, factual grounding, and alignment with TADA's voice and methodology before routing to human review.

**Trigger Conditions:**
- Automatically invoked by TADA Perspective Agent before draft is stored
- Invoked by Content Strategy Agent on generated outlines
- Can be manually triggered on any insight

**Input:**
```python
{
    "content_type": "insight|content_outline|briefing",
    "content_id": "uuid",
    "content": {...}
}
```

**Output:**
```python
{
    "qa_result": "pass|fail|needs_revision",
    "quality_score": 0.88,               # 0-1
    "issues_found": [
        {
            "severity": "critical|major|minor",
            "category": "factual|consistency|tone|completeness|ddd_logic",
            "description": "string",
            "suggestion": "string"
        }
    ],
    "auto_fixes_applied": ["string", ...],
    "approved_for_review": true
}
```

**Tools:**
- `check_factual_grounding(claim, sources)` → grounded/ungrounded
- `check_ddd_logic(detect, decide, do)` → consistent/inconsistent
- `check_tada_voice(text, voice_guidelines)` → alignment score
- `check_consistency_with_past(text, similar_insights)` → consistency score
- `auto_fix_minor_issues(text, issues)` → corrected text (gpt-4o-mini)

---

## Agent 12: Repository Agent

**Role:** Manages the permanent Knowledge Repository. Handles storage, indexing, entity extraction, knowledge graph updates, and search index maintenance.

**Trigger Conditions:**
- Webhook from Human Review System when insight is PUBLISHED
- Nightly sync job for index optimization

**Input:**
```python
{
    "insight_id": "uuid",
    "action": "publish|archive|update_graph|reindex"
}
```

**Output:**
```python
{
    "knowledge_item_id": "uuid",
    "entities_extracted": [{"name": "string", "type": "string", "entity_id": "uuid"}],
    "relationships_created": [
        {"source_entity": "string", "target_entity": "string", "relationship": "string"}
    ],
    "search_indexed": true,
    "graph_updated": true
}
```

**Tools:**
- `store_knowledge_item(insight_data)` → knowledge_item_id
- `extract_entities_for_graph(text)` → entity list
- `upsert_entities(entities)` → entity_ids
- `create_relationships(entity_pairs, relationship_type)` → relationship_ids
- `update_embedding_index(knowledge_item_id, embedding)` → void
- `invalidate_search_cache(tags)` → void

---

## Agent 13: Recommendation Agent

**Role:** Generates structured, persona-specific strategic recommendations from framed insights. Produces actionable outputs for Marketing, Sales, Leadership, Customer Success, and Product teams.

**Trigger Conditions:**
- Invoked by TADA Perspective Agent after insight framing
- Weekly batch for pending insights without recommendations

**Input:**
```python
{
    "insight_id": "uuid",
    "personas": ["marketing", "sales", "leadership", "cs", "product"],  # All 5 by default
    "insight_data": {...},
    "competitive_context": {...},
    "pain_point_context": {...}
}
```

**Output:**
```python
{
    "recommendations": {
        "marketing": {
            "priority": "high",
            "actions": [
                {
                    "action": "string",
                    "rationale": "string",
                    "timeline": "immediate|this_week|this_month|this_quarter",
                    "effort": "low|medium|high"
                }
            ],
            "messaging_opportunity": "string",
            "content_angle": "string"
        },
        "sales": {
            "priority": "high",
            "actions": [...],
            "pipeline_impact": "string",
            "target_accounts": "string"
        },
        "leadership": {
            "priority": "medium",
            "actions": [...],
            "strategic_implication": "string",
            "risk_if_ignored": "string"
        },
        "cs": {
            "priority": "medium",
            "actions": [...],
            "retention_risk": "string",
            "expansion_opportunity": "string"
        },
        "product": {
            "priority": "low",
            "actions": [...],
            "roadmap_implication": "string",
            "competitive_gap": "string"
        }
    },
    "recommendation_ids": ["uuid", ...]
}
```

**Tools:**
- `fetch_persona_context(persona_name)` → persona profile + current priorities
- `generate_persona_recommendations(insight, persona, context)` → recommendations (gpt-4o)
- `prioritize_recommendations(recs, business_context)` → priority-ranked list
- `store_recommendations(recommendations, insight_id)` → recommendation_ids

---

## Agent Interaction Matrix

| Agent | Triggers | Called By | Calls |
|-------|----------|-----------|-------|
| Collection | n8n cron | n8n | Signal Detection |
| Research | API/manual | Signal Detection, Executive Briefing | — |
| Signal Detection | Collection webhook | Collection | Trend, Multi-Source Validation |
| Trend | Cron/Signal webhook | n8n, Signal Detection | — |
| Competitive Intel | Cron | n8n | — |
| Pain Point | Cron | n8n | — |
| TADA Perspective | Relevance threshold | Relevance Service | QA, Recommendation |
| Content Strategy | Review approval | n8n | Calendar Service |
| Sales Intelligence | Recommendation | Recommendation | — |
| Executive Briefing | Cron | n8n | QA, Repository |
| QA | Perspective Agent | Perspective, Content Strategy | — |
| Repository | Review approval | n8n webhook | — |
| Recommendation | Perspective completion | Perspective | Content Strategy, Sales |

---

## LangGraph Checkpointing

All agents use PostgreSQL-backed checkpointing for:
- Resumability after failures
- Audit trail of every agent step
- Human-in-the-loop interruption points
- Replay capability for debugging

```python
# apps/agents/src/tada_agents/checkpointer/postgres_checkpointer.py

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def get_checkpointer():
    return await AsyncPostgresSaver.from_conn_string(
        settings.TADA_DB_URL,
        schema="langgraph_checkpoints"
    )
```

Human-in-the-loop interrupt points:
- **TADA Perspective Agent** — interrupts before `trigger_review` node, allows analyst to preview
- **Executive Briefing Agent** — interrupts before `store_executive_briefing`, allows editor review
- **Research Agent** — interrupts after `plan_research`, allows scope adjustment
