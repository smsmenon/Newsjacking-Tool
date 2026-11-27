# TADA Intelligence Platform — LangGraph Agent Workflows
## Deliverable 12 of 20

All agent code lives in `/agents/`. The main graph is defined in `/agents/graph.py`. Each node is an async Python function. State is persisted via `AsyncPostgresSaver` for fault tolerance and human-in-the-loop interruptions.

---

## Core Architecture

### Technology Stack
- **LangGraph** 0.2+ (stateful graph execution)
- **LangChain** 0.3+ (LLM abstractions)
- **OpenAI** GPT-4o-mini (extraction/classification) + GPT-4o (perspective/briefing)
- **Langfuse** (observability — traces, spans, cost tracking)
- **AsyncPostgresSaver** (state persistence + resumability)

### AgentState (shared across all nodes)

```python
# /agents/state.py
from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # --- Input ---
    content_ids: list[str]          # Raw content IDs to process
    run_id: str                     # Unique run identifier
    run_type: str                   # 'collection' | 'signal' | 'briefing' | 'content'

    # --- Content Processing ---
    raw_content: list[dict]         # Fetched raw content records
    processed_content: list[dict]   # After extraction
    embeddings_computed: bool

    # --- Signal Detection ---
    candidate_signals: list[dict]   # Unvalidated signal candidates
    validated_signals: list[dict]   # After multi-source validation
    signal_ids: list[str]           # IDs of stored signals

    # --- Trend Analysis ---
    trend_updates: list[dict]       # Trend frequency updates
    new_trends: list[dict]          # Newly detected trends

    # --- Competitive Intel ---
    competitor_events: list[dict]   # Detected competitor events
    positioning_gaps: list[dict]    # Identified TADA opportunities

    # --- Pain Points ---
    pain_points: list[dict]         # Extracted pain points

    # --- TADA Perspective ---
    insights: list[dict]            # Full TADA perspective objects
    insight_ids: list[str]

    # --- Recommendations ---
    recommendations: list[dict]     # Team-specific recommendations

    # --- Content Strategy ---
    content_ideas: list[dict]       # Generated content ideas
    content_calendar: Optional[dict]

    # --- Executive Briefing ---
    briefing: Optional[dict]        # Executive briefing output

    # --- Quality Assurance ---
    qa_passed: bool
    qa_issues: list[str]

    # --- Metadata ---
    errors: list[str]               # Non-fatal errors accumulated
    langfuse_trace_id: Optional[str]
    messages: Annotated[list, add_messages]  # For human-in-the-loop
```

---

## Graph 1 — Main Intelligence Pipeline

This is the primary graph that runs on every batch of new content.

```python
# /agents/graph.py (simplified structure)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("content_extractor", content_extraction_node)
graph.add_node("embedding_generator", embedding_node)
graph.add_node("signal_detector", signal_detection_node)
graph.add_node("multi_source_validator", validation_node)
graph.add_node("trend_updater", trend_update_node)
graph.add_node("tada_perspective", tada_perspective_node)
graph.add_node("recommendation_engine", recommendation_node)
graph.add_node("content_strategy", content_strategy_node)
graph.add_node("qa_reviewer", qa_node)
graph.add_node("repository_writer", repository_node)

# Define flow
graph.set_entry_point("content_extractor")
graph.add_edge("content_extractor", "embedding_generator")
graph.add_edge("embedding_generator", "signal_detector")
graph.add_conditional_edges(
    "signal_detector",
    route_after_signal_detection,
    {
        "signals_found": "multi_source_validator",
        "no_signals": "trend_updater",
    }
)
graph.add_edge("multi_source_validator", "trend_updater")
graph.add_edge("trend_updater", "tada_perspective")
graph.add_edge("tada_perspective", "recommendation_engine")
graph.add_edge("recommendation_engine", "content_strategy")
graph.add_edge("content_strategy", "qa_reviewer")
graph.add_conditional_edges(
    "qa_reviewer",
    route_after_qa,
    {
        "passed": "repository_writer",
        "failed": "tada_perspective",  # retry with feedback
    }
)
graph.add_edge("repository_writer", END)
```

### Flow Diagram

```
[content_extractor]
        │
        ▼
[embedding_generator]
        │
        ▼
[signal_detector] ──────────────────────────────┐
        │                                        │
   signals_found                            no_signals
        │                                        │
        ▼                                        │
[multi_source_validator]                         │
        │                                        │
        ▼                                        │
[trend_updater] ◄───────────────────────────────┘
        │
        ▼
[tada_perspective]  ◄────── (retry on QA fail)
        │
        ▼
[recommendation_engine]
        │
        ▼
[content_strategy]
        │
        ▼
[qa_reviewer]
        │
    ┌───┴────┐
  passed   failed
    │          │
    ▼          └──► [tada_perspective] (max 2 retries)
[repository_writer]
    │
   END
```

---

## Graph 2 — Competitive Intelligence Pipeline

Runs daily for each competitor.

```
[competitor_data_collector]
        │
        ▼
[change_detector]  ── no_change ──► END
        │
   change_detected
        │
        ▼
[competitive_intel_analyzer]
        │
        ▼
[positioning_gap_identifier]
        │
        ▼
[competitive_content_generator]
        │
        ▼
[repository_writer]
        │
       END
```

### Key Node: `competitive_intel_analyzer`

```python
async def competitive_intel_node(state: AgentState) -> AgentState:
    """
    Analyzes competitor content changes and extracts strategic intelligence.
    
    Input:  state.competitor_events (raw scraped content)
    Output: state.competitor_events (enriched with analysis)
            state.positioning_gaps (TADA opportunities identified)
    
    Model: GPT-4o (needs nuanced competitive reasoning)
    Prompt: /prompts/system-prompts.md → Competitive Intelligence Prompt
    
    LangGraph interrupt: After analysis, before storage
    (allows human to review before competitor event is logged)
    """
```

---

## Graph 3 — Executive Briefing Pipeline

Runs daily at 6 AM via n8n trigger.

```
[data_aggregator]
(collects top signals, trends, competitor events)
        │
        ▼
[market_sentiment_calculator]
(computes overall sentiment from last 48h content)
        │
        ▼
[executive_briefing_generator]
(GPT-4o, full briefing composition)
        │
        ▼
[briefing_formatter]
(structures into daily/weekly/monthly format)
        │
        ▼
[human_review_gate] ◄── INTERRUPT POINT
(pauses graph, creates review_item, waits for approval)
        │
    approved
        │
        ▼
[repository_writer]
        │
       END
```

### Human-in-the-Loop Implementation

```python
from langgraph.types import interrupt

async def human_review_gate(state: AgentState) -> AgentState:
    """
    Pauses graph execution and waits for human approval.
    Graph resumes when reviewer calls /api/v1/review/{id}/approve.
    """
    # Create review item in database
    review_id = await create_review_item(
        item_type="briefing",
        item_id=state["briefing"]["id"],
        status="under_review"
    )
    
    # Interrupt — graph pauses here
    human_decision = interrupt({
        "review_id": review_id,
        "action_required": "approve_briefing",
        "briefing_summary": state["briefing"]["summary"]
    })
    
    # Graph resumes here when human acts
    if human_decision["action"] == "approved":
        return {**state, "briefing": {**state["briefing"], "status": "approved"}}
    elif human_decision["action"] == "rejected":
        raise ValueError(f"Briefing rejected: {human_decision['reason']}")
    elif human_decision["action"] == "revise":
        # Trigger re-generation with feedback
        return {**state, "revision_feedback": human_decision["feedback"]}
```

---

## Graph 4 — Pain Point Detection Pipeline

Runs daily at 10 AM.

```
[social_content_fetcher]
(gets last 24h social content)
        │
        ▼
[pain_signal_filter]
(keyword pre-filter for efficiency)
        │
        ▼
[pain_point_extractor]
(LLM extracts structured pain points)
        │
        ▼
[pain_point_clusterer]
(groups similar pain points together)
        │
        ▼
[pain_point_scorer]
(severity + frequency scoring)
        │
        ▼
[repository_writer]
        │
       END (Mon-Thu)
        │
     Friday
        ▼
[weekly_report_generator]
        │
        ▼
[human_review_gate]
        │
       END
```

---

## Node Specifications

### Node: `content_extractor`

```
Purpose:  Extract structured information from raw article content
Model:    GPT-4o-mini (fast, cost-efficient for extraction)
Input:    raw_content records (title, content, source, url)
Output:   processed_content with all extracted fields
Timeout:  2 minutes per batch of 50
Cost:     ~$0.002 per article
```

**Extraction Schema:**
```json
{
  "short_summary": "2-3 sentence summary",
  "medium_summary": "1-2 paragraph summary",
  "executive_summary": "C-suite focused 1 paragraph",
  "keywords": ["tariff", "supply chain", "..."],
  "topics": ["Supply Chain", "Trade Policy"],
  "industries": ["Manufacturing", "Retail"],
  "companies": ["Apple", "TSMC"],
  "risks": ["supplier concentration", "cost increase"],
  "opportunities": ["reshoring", "domestic sourcing"],
  "disruptions": ["port delays", "tariff increase"],
  "geographies": ["United States", "China", "Mexico"],
  "technologies": ["AI", "demand sensing"],
  "sentiment": "negative|neutral|positive",
  "relevance_to_tada": 85
}
```

---

### Node: `signal_detector`

```
Purpose:  Identify meaningful signals from processed content batch
Model:    GPT-4o (requires strong pattern recognition)
Input:    processed_content batch (up to 50 articles)
Output:   candidate_signals list
Timeout:  5 minutes
Cost:     ~$0.05 per batch
```

**Signal Output Schema:**
```json
{
  "signals": [
    {
      "title": "Concise signal name",
      "description": "What is happening and why it matters",
      "signal_type": "trend|disruption|opportunity|risk|shift",
      "urgency": "critical|high|medium|low",
      "affected_industries": ["Manufacturing"],
      "affected_geographies": ["USA", "China"],
      "evidence_article_indices": [0, 3, 7],
      "confidence_rationale": "Why this signal is confident",
      "supply_chain_relevance": 92,
      "executive_importance": 85,
      "business_impact": 88,
      "technology_relevance": 40,
      "tada_alignment": 90
    }
  ]
}
```

---

### Node: `tada_perspective`

```
Purpose:  Apply TADA's Detect→Decide→Do lens to each validated signal
Model:    GPT-4o (requires deep strategic reasoning + TADA brand knowledge)
Input:    validated_signals
Output:   insights (full TADA perspective per signal)
Timeout:  3 minutes per signal
Cost:     ~$0.15 per signal
```

**Insight Output Schema:**
```json
{
  "what_happened": "Factual summary of the signal",
  "why_it_matters": "Business and strategic implications",
  "potential_impact": {
    "cost_impact": "12-18% increase in component costs",
    "timeline": "Effective August 1, 2026",
    "affected_segments": ["Tier 1 manufacturers", "Electronics OEMs"],
    "severity": "high"
  },
  "traditional_response": "How organizations typically respond (slowly, reactively)",
  "tada_response": "How TADA enables a better response (detect early, model scenarios, execute fast)",
  "detect_action": "What TADA detects in real-time",
  "decide_action": "What decisions TADA supports (scenario modeling, alternative sourcing)",
  "do_action": "What TADA executes automatically (supplier outreach, RFQ generation)",
  "expected_outcome": "Quantified business outcome (e.g., 3-week faster response, $2M cost avoidance)",
  "tada_value_prop": "One sentence TADA differentiation statement"
}
```

---

### Node: `recommendation_engine`

```
Purpose:  Generate team-specific actionable recommendations per signal
Model:    GPT-4o-mini
Input:    insights, validated_signals
Output:   recommendations (5 teams × N signals)
Timeout:  2 minutes
Cost:     ~$0.02 per signal
```

**Recommendation Teams:**
- `marketing` — Content, campaigns, positioning
- `sales` — Account targeting, talking points, outreach
- `leadership` — Strategic decisions, risk response
- `customer_success` — Account risk, expansion opportunities
- `product` — Feature prioritization, roadmap signals
- `partnership` — Alliance opportunities, channel plays

---

### Node: `qa_reviewer`

```
Purpose:  Quality gate before any output enters the review queue
Model:    GPT-4o-mini
Input:    insights, recommendations, content_ideas
Output:   qa_passed (bool), qa_issues (list)
Timeout:  1 minute
Cost:     ~$0.01 per batch
```

**QA Checklist:**
```
✓ TADA perspective is consistent with brand voice
✓ Detect→Decide→Do framework is clearly articulated
✓ Sources are cited (no hallucinated sources)
✓ Recommendations are actionable (not vague)
✓ Business outcome is quantified or estimable
✓ Content ideas are tied to source signals
✓ No competitor names in direct comparison without evidence
✓ Tone is authoritative, not alarmist
```

---

## Observability Configuration

### Langfuse Integration

```python
# /agents/observability.py
from langfuse.callback import CallbackHandler
from langfuse import Langfuse
import os

def get_langfuse_handler(run_id: str, run_type: str) -> CallbackHandler:
    """
    Create a per-request Langfuse handler.
    NEVER use a global singleton — creates trace contamination.
    """
    return CallbackHandler(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ["LANGFUSE_HOST"],
        trace_name=f"tada-{run_type}",
        tags=[run_type, "production"],
        metadata={"run_id": run_id}
    )

# Usage in each node:
async def signal_detection_node(state: AgentState) -> AgentState:
    handler = get_langfuse_handler(state["run_id"], "signal_detection")
    
    chain = signal_detection_chain.with_config(
        callbacks=[handler]
    )
    # LangGraph node name becomes Langfuse span name automatically
```

### Key Metrics Tracked in Langfuse
| Metric | Alert Threshold |
|--------|----------------|
| Signal detection latency | > 5 minutes |
| TADA perspective latency | > 3 minutes |
| Token cost per run | > $5 |
| Error rate | > 5% |
| QA pass rate | < 80% (prompt degradation signal) |

---

## Fault Tolerance

### Checkpoint Strategy
```python
# State is checkpointed after every node
# Enables resuming from any failure point

async with AsyncPostgresSaver.from_conn_string(DB_URL) as saver:
    compiled_graph = graph.compile(checkpointer=saver)
    
    # Resume from checkpoint on retry
    result = await compiled_graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": run_id}}
    )
```

### Retry Policy
```python
# Each LLM call uses exponential backoff
from langchain_core.runnables import RunnableRetry

chain_with_retry = chain.with_retry(
    retry_if_exception_type=(RateLimitError, APITimeoutError),
    wait_exponential_jitter=True,
    stop_after_attempt=3
)
```

### Dead Letter Queue
- Runs that fail after 3 retries → status = `failed` in `collection_jobs`
- Alert sent to `#tada-ops` Slack
- Failed content IDs stored for manual reprocessing
- Daily report of failed items to ops team

---

## Cost Control

### Model Assignment by Task
| Task | Model | Reason |
|------|-------|--------|
| Content extraction | gpt-4o-mini | High volume, structured output |
| Signal detection | gpt-4o | Needs strong pattern recognition |
| TADA perspective | gpt-4o | Brand-critical, strategic reasoning |
| Recommendations | gpt-4o-mini | Template-driven, lower complexity |
| Content ideas | gpt-4o-mini | Creative but formulaic |
| Executive briefing | gpt-4o | Leadership-facing, highest quality |
| QA review | gpt-4o-mini | Checklist-based, lower complexity |
| Pain point extraction | gpt-4o-mini | High volume social content |

### Monthly Cost Estimates (500 articles/day)
| Task | Volume | Tokens | Cost/Month |
|------|--------|--------|------------|
| Extraction | 15,000/mo | 2K avg | ~$9 |
| Signal detection | 300 batches | 10K avg | ~$45 |
| TADA perspective | 150 signals | 3K avg | ~$68 |
| Recommendations | 150 signals | 2K avg | ~$6 |
| Content ideas | 150 signals | 2K avg | ~$6 |
| Briefings | 30/mo | 5K avg | ~$23 |
| QA | 300 runs | 1K avg | ~$5 |
| **Total** | | | **~$162/mo** |

Set OpenAI hard spend limit at $300/month as safety ceiling.
