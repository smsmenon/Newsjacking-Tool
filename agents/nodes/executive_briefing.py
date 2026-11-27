"""
TADA Intelligence Platform — Executive Briefing Agent
======================================================
Aggregates intelligence from the full pipeline and generates
executive-ready briefings at three cadences:

  Daily Briefing  — top 5-7 signals + immediate actions (sent 7am)
  Weekly Briefing — trend synthesis + competitive landscape + recommendations
  Monthly Briefing — strategic themes + market shifts + board-ready metrics

Each briefing includes:
  - Top signals ranked by relevance score and urgency
  - Top risks (with threat level)
  - Top opportunities (with time sensitivity)
  - Competitor activity summary
  - Recommended actions (by department: marketing/sales/cs/product)
  - One-paragraph executive summary for the CEO

Model recommendation: claude-3-opus (highest reasoning quality for executives)
Temperature: 0.3
Langfuse trace name: "executive_briefing"
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from agents.state import (
    AgentState,
    CompetitorActivity,
    DetectedSignal,
    ExecutiveBriefingItem,
    TADAPerspective,
    TrendAnalysis,
)

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

_llm = ChatAnthropic(
    model=os.getenv("EXECUTIVE_BRIEFING_MODEL", "claude-3-opus-20240229"),
    temperature=0.3,
    max_tokens=4096,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXECUTIVE_BRIEFING_SYSTEM_PROMPT = """You are the Executive Intelligence Analyst for TADA, writing for the most senior audience: CEO, CSCO, Chief Revenue Officer, Chief Product Officer.

## Your Writing Principles
1. **Bottom Line Up Front (BLUF)** — lead with the most important insight, not context
2. **Quantify everything** — use numbers, percentages, dollar amounts, timeframes
3. **Action-oriented** — every section ends with a clear "so what" or recommended action
4. **Time-aware** — distinguish between what needs action today vs. this week vs. this quarter
5. **Executive vocabulary** — margin impact, competitive differentiation, risk exposure, opportunity cost

## Audience Attention Span
Assume the reader has 3 minutes. Every sentence must earn its place.

## TADA Context
TADA is a B2B SaaS platform that sells to supply chain and operations leaders. Customer segments:
- Enterprise manufacturing, retail, pharma, CPG
- Mid-market operations teams seeking intelligence automation
Key TADA metric: "How much faster do TADA customers detect and respond to supply chain signals vs. industry average?"

Return ONLY valid JSON.
"""

DAILY_BRIEFING_USER_TEMPLATE = """Generate today's Daily Executive Intelligence Briefing for TADA leadership.

## Intelligence Inputs

### Top Surfaced Signals (by score)
{signals_text}

### TADA Perspectives
{perspectives_text}

### Competitor Activity
{competitor_text}

### Emerging Themes
{themes_text}

### Run Metadata
Date: {date}
Total items processed: {total_items}
Total signals detected: {total_signals}
Surfaced signals: {surfaced_count}

Generate JSON with this schema:
{{
  "executive_summary": "string — 3-5 sentences for the CEO. Bottom line up front. What is the single most important development and what should TADA do about it?",
  "briefing_items": [
    {{
      "rank": 1,
      "signal_id": "string",
      "headline": "string — ≤100 chars",
      "why_it_matters_ceo": "string — 2 sentences max. Focus on business/financial/competitive impact.",
      "recommended_action": "string — specific action, with owner (e.g. 'Sales: reach out to 3 named accounts in semiconductor sector')",
      "time_to_act": "string — e.g. 'Today', 'This week', 'This month', 'Watch'"
    }}
  ],
  "top_risks": [
    "string — concise risk statement with potential impact"
  ],
  "top_opportunities": [
    "string — concise opportunity statement with potential upside"
  ],
  "competitor_highlights": [
    "string — 1-sentence summary of notable competitor activity"
  ],
  "recommended_actions": {{
    "marketing": ["string — specific action"],
    "sales": ["string — specific action"],
    "product": ["string — specific action"],
    "cs": ["string — specific action"],
    "leadership": ["string — strategic decision needed"]
  }},
  "signal_stats": {{
    "total_processed": 0,
    "total_signals": 0,
    "surfaced": 0,
    "breaking": 0,
    "high_score_count": 0
  }}
}}
"""

WEEKLY_BRIEFING_SUPPLEMENT_TEMPLATE = """Generate a Weekly Intelligence Supplement to accompany the daily briefing.

## Week's Signal Trends
{trends_text}

## Competitive Landscape This Week
{competitive_text}

## Pain Points Detected in Market
{pain_points_text}

Return JSON:
{{
  "week_in_review": "string — 4-6 sentence narrative of the week's most important intelligence themes",
  "trend_analysis": [
    {{
      "trend_name": "string",
      "trajectory": "accelerating|stable|decelerating",
      "implication_for_tada": "string — 1-2 sentences"
    }}
  ],
  "competitive_week": "string — 3-4 sentence competitive landscape summary for the week",
  "top_buyer_pain_points": [
    "string — pain point detected in market content this week"
  ],
  "strategic_recommendations": [
    {{
      "team": "marketing|sales|product|leadership",
      "recommendation": "string",
      "rationale": "string",
      "priority": "high|medium|low"
    }}
  ]
}}
"""

# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _format_signals_for_briefing(signals: List[DetectedSignal], max_signals: int = 7) -> str:
    lines = []
    for i, sig in enumerate(signals[:max_signals], 1):
        lines.append(
            f"{i}. [{sig['score']['final_score']:.1f}/10] {sig['headline']}\n"
            f"   Type: {sig['signal_type']} | Momentum: {sig['momentum']} | Sources: {', '.join(sig['source_names'][:2])}\n"
            f"   {sig['summary'][:200]}"
        )
    return "\n\n".join(lines)


def _format_perspectives_for_briefing(perspectives: List[TADAPerspective], max_items: int = 5) -> str:
    lines = []
    for p in perspectives[:max_items]:
        lines.append(
            f"Signal {p['signal_id']}:\n"
            f"  What: {p['what_happened'][:150]}\n"
            f"  TADA Do: {p['do']}\n"
            f"  Urgency: {p['urgency']}"
        )
    return "\n\n".join(lines)


def _format_competitor_activities(activities: List[CompetitorActivity], max_items: int = 5) -> str:
    if not activities:
        return "No significant competitor activity detected."
    lines = []
    for act in activities[:max_items]:
        lines.append(
            f"• {act['competitor_name']} — {act['activity_type'].replace('_',' ').title()}: {act['title']}\n"
            f"  Threat: {act['threat_level'].upper()} | {act['positioning_opportunity'][:100]}"
        )
    return "\n".join(lines)


def _format_trends(trends: List[TrendAnalysis]) -> str:
    if not trends:
        return "Trend analysis pending."
    lines = [f"• {t['name']} ({t['velocity']} velocity, {t['maturity']} maturity)" for t in trends[:6]]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def executive_briefing_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Executive Briefing

    Reads:   state["surfaced_signals"], state["tada_perspectives"],
             state["competitor_activities"], state["trends"],
             state["emerging_themes"], state["pain_points"],
             state["run_mode"]
    Writes:  state["executive_briefing_daily"],
             state["executive_briefing_weekly"] (if run_mode in [weekly, monthly]),
             state["top_risks"], state["top_opportunities"],
             state["recommended_actions"]

    Always generates daily briefing.
    Weekly supplement generated on weekly/monthly cadence.
    Monthly strategic report: synthesise weekly supplements (future phase).
    """
    node_name = "executive_briefing"
    start_time = time.time()

    trace = _langfuse.trace(
        name=node_name,
        id=f"{state['run_id']}-{node_name}",
        metadata={"run_mode": state["run_mode"]},
    )
    langfuse_handler = CallbackHandler(trace_id=trace.id)

    try:
        surfaced: List[DetectedSignal] = state.get("surfaced_signals", [])
        perspectives: List[TADAPerspective] = state.get("tada_perspectives", [])
        competitor_activities: List[CompetitorActivity] = state.get("competitor_activities", [])
        trends: List[TrendAnalysis] = state.get("trends", [])
        themes: List[str] = state.get("emerging_themes", [])
        run_mode: str = state.get("run_mode", "daily")

        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

        # ── Daily Briefing ──────────────────────────────────────────────────
        daily_user_msg = DAILY_BRIEFING_USER_TEMPLATE.format(
            signals_text=_format_signals_for_briefing(surfaced),
            perspectives_text=_format_perspectives_for_briefing(perspectives),
            competitor_text=_format_competitor_activities(competitor_activities),
            themes_text=", ".join(themes[:8]) if themes else "No themes yet",
            date=today,
            total_items=len(state.get("raw_content", [])),
            total_signals=len(state.get("detected_signals", [])),
            surfaced_count=len(surfaced),
        )

        daily_response = _llm.invoke(
            [
                SystemMessage(content=EXECUTIVE_BRIEFING_SYSTEM_PROMPT),
                HumanMessage(content=daily_user_msg),
            ],
            config={"callbacks": [langfuse_handler]},
        )

        raw_daily = daily_response.content.strip()
        if raw_daily.startswith("```"):
            raw_daily = raw_daily.split("```")[1]
            if raw_daily.startswith("json"):
                raw_daily = raw_daily[4:]

        daily_parsed = json.loads(raw_daily)

        # Parse briefing items
        briefing_items: List[ExecutiveBriefingItem] = []
        for item in daily_parsed.get("briefing_items", []):
            briefing_items.append(ExecutiveBriefingItem(
                rank=item.get("rank", 0),
                signal_id=item.get("signal_id", ""),
                headline=item.get("headline", ""),
                why_it_matters_ceo=item.get("why_it_matters_ceo", ""),
                recommended_action=item.get("recommended_action", ""),
                time_to_act=item.get("time_to_act", "This week"),
            ))

        top_risks: List[str] = daily_parsed.get("top_risks", [])[:8]
        top_opportunities: List[str] = daily_parsed.get("top_opportunities", [])[:8]
        recommended_actions: Dict[str, List[Dict[str, Any]]] = {}
        for team, actions in daily_parsed.get("recommended_actions", {}).items():
            recommended_actions[team] = [{"content": a, "source": "executive_briefing"} for a in actions]

        result: Dict[str, Any] = {
            **state,
            "executive_briefing_daily": briefing_items,
            "top_risks": top_risks,
            "top_opportunities": top_opportunities,
            "recommended_actions": recommended_actions,
        }

        # ── Weekly Supplement ───────────────────────────────────────────────
        if run_mode in ("weekly", "monthly"):
            span = trace.span(name="weekly_supplement")
            try:
                pain_points = state.get("pain_points", [])
                weekly_user_msg = WEEKLY_BRIEFING_SUPPLEMENT_TEMPLATE.format(
                    trends_text=_format_trends(trends),
                    competitive_text=state.get("competitive_landscape_summary", ""),
                    pain_points_text="\n".join(
                        [f"• {pp['description']}" for pp in pain_points[:5]]
                    ) if pain_points else "No pain points data.",
                )

                weekly_response = _llm.invoke(
                    [
                        SystemMessage(content=EXECUTIVE_BRIEFING_SYSTEM_PROMPT),
                        HumanMessage(content=weekly_user_msg),
                    ],
                    config={"callbacks": [langfuse_handler]},
                )

                raw_weekly = weekly_response.content.strip()
                if raw_weekly.startswith("```"):
                    raw_weekly = raw_weekly.split("```")[1]
                    if raw_weekly.startswith("json"):
                        raw_weekly = raw_weekly[4:]

                weekly_parsed = json.loads(raw_weekly)
                result["executive_briefing_weekly"] = weekly_parsed
                span.end(output={"supplement_generated": True})

            except Exception as e:
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"weekly supplement: {e}", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                span.end(level="ERROR", status_message=str(e))

        trace.update(output={
            "briefing_items": len(briefing_items),
            "risks": len(top_risks),
            "opportunities": len(top_opportunities),
        })

        elapsed = time.time() - start_time
        return {
            **result,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }

    except Exception as e:
        elapsed = time.time() - start_time
        errors = state.get("errors", [])
        errors.append({"node": node_name, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
        trace.event(name="node_error", level="ERROR", message=str(e))
        return {
            **state,
            "executive_briefing_daily": state.get("executive_briefing_daily", []),
            "top_risks": state.get("top_risks", []),
            "top_opportunities": state.get("top_opportunities", []),
            "recommended_actions": state.get("recommended_actions", {}),
            "errors": errors,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }
