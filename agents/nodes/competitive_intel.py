"""
TADA Intelligence Platform — Competitive Intelligence Agent
===========================================================
Monitors competitor content (websites, press releases, LinkedIn announcements)
to detect:
  - Product launches and feature updates
  - Partnership and integration announcements
  - Acquisitions and M&A activity
  - Messaging and positioning shifts
  - Pricing changes
  - Key hiring signals (VP/C-level)
  - Analyst mentions / award wins

Produces:
  - List of CompetitorActivity objects
  - Competitive landscape summary narrative
  - Positioning opportunities for TADA

Model recommendation: claude-3-5-sonnet
Temperature: 0.2
Langfuse trace name: "competitive_intel"
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from agents.state import AgentState, CompetitorActivity, RawContentItem

# ---------------------------------------------------------------------------
# Known TADA competitors (extend via config/competitors.json)
# ---------------------------------------------------------------------------

KNOWN_COMPETITORS: List[str] = [
    "Resilinc", "Everstream Analytics", "Craft.co", "riskmethods",
    "Elementum", "E2open", "Kinaxis", "o9 Solutions", "Blue Yonder",
    "SAP IBP", "Oracle SCM", "FourKites", "project44", "Descartes",
    "Coupa", "Jaggaer", "GEP SMART", "Ivalua", "Zycus",
    "Llamasoft", "LLamasoft", "Optilogic", "Logility",
]

COMPETITOR_DOMAINS: List[str] = [
    "resilinc.com", "everstream.ai", "craft.co", "riskmethods.net",
    "elementum.com", "e2open.com", "kinaxis.com", "o9solutions.com",
    "blueyonder.com", "sap.com", "oracle.com", "fourkites.com",
    "project44.com", "descartes.com", "coupa.com", "jaggaer.com",
    "gep.com", "ivalua.com", "zycus.com", "logility.com",
]

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

_llm = ChatAnthropic(
    model=os.getenv("COMPETITIVE_INTEL_MODEL", "claude-3-5-sonnet-20241022"),
    temperature=0.2,
    max_tokens=4096,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

COMPETITIVE_INTEL_SYSTEM_PROMPT = """You are the Competitive Intelligence Analyst for TADA, a supply chain content intelligence platform.

Your job is to analyse content items that mention TADA's competitors and extract structured competitive intelligence.

## TADA's Competitors (primary)
Supply chain risk/intelligence platforms: Resilinc, Everstream Analytics, Craft.co, riskmethods, Elementum
Supply chain planning: Kinaxis, o9 Solutions, Blue Yonder, SAP IBP, Oracle SCM
Logistics visibility: FourKites, project44, Descartes
Procurement: Coupa, Jaggaer, GEP SMART, Ivalua, Zycus

## Activity Types to Detect
- product_launch: New product, feature, module, or API release
- partnership: Technology integration, channel, or go-to-market partnership
- acquisition: M&A activity, acqui-hire
- messaging_shift: Changes in positioning, taglines, ICP targeting, or value proposition
- pricing: Pricing model changes, new tiers, freemium announcements
- funding: Investment rounds, IPO activity
- leadership: C-suite hire/departure that signals strategic direction
- analyst_recognition: Gartner Magic Quadrant, Forrester Wave, G2 awards

## Positioning Opportunities for TADA
After identifying competitor activity, assess whether it creates an opportunity:
- If competitor raised prices → TADA can highlight value proposition
- If competitor launched a feature TADA already has → TADA can claim leadership
- If competitor messaging shifted → TADA can differentiate on original strength
- If competitor had a public failure → TADA can offer stability narrative

Return ONLY valid JSON.
"""

COMPETITIVE_INTEL_USER_TEMPLATE = """Analyse the following content items for competitive intelligence about TADA's competitors.

Known competitors: {competitors}

Content batch ({n} items):
{content_batch}

Return JSON with this schema:
{{
  "activities": [
    {{
      "competitor_name": "string — exact name from known competitors list",
      "competitor_url": "string — their website domain",
      "activity_type": "product_launch|partnership|acquisition|messaging_shift|pricing|funding|leadership|analyst_recognition",
      "title": "string — ≤100 chars headline for this activity",
      "summary": "string — 2-3 sentence description of what happened",
      "detected_at": "string — ISO-8601 date from the source",
      "source_url": "string — URL of the source content",
      "positioning_opportunity": "string — 1-2 sentences on how TADA can respond/position",
      "threat_level": "high|medium|low"
    }}
  ],
  "competitive_landscape_summary": "string — 3-5 sentence narrative summarising the competitive environment based on this batch. Note key trends in competitor behaviour.",
  "tada_positioning_opportunities": [
    "string — specific actionable positioning opportunity for TADA sales/marketing"
  ]
}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_competitor_content(item: RawContentItem) -> bool:
    """Quick filter: does this item mention any known competitor?"""
    text = (item["title"] + " " + item["body"]).lower()
    return any(c.lower() in text for c in KNOWN_COMPETITORS + COMPETITOR_DOMAINS)


def _format_batch(items: List[RawContentItem], max_chars: int = 1200) -> str:
    parts = []
    for item in items:
        preview = item["body"][:max_chars].strip()
        parts.append(
            f"[ID:{item['id']}] {item['source_name']} | {item['published_at']}\n"
            f"TITLE: {item['title']}\nBODY: {preview}\nURL: {item['source_url']}"
        )
    return "\n---\n".join(parts)


def _validate_activity(raw: Dict[str, Any]) -> Optional[CompetitorActivity]:
    """Validate and coerce a raw activity dict."""
    try:
        valid_types = {
            "product_launch", "partnership", "acquisition", "messaging_shift",
            "pricing", "funding", "leadership", "analyst_recognition",
        }
        valid_threats = {"high", "medium", "low"}
        return CompetitorActivity(
            competitor_name=raw["competitor_name"],
            competitor_url=raw.get("competitor_url", ""),
            activity_type=raw.get("activity_type", "product_launch") if raw.get("activity_type") in valid_types else "product_launch",
            title=raw.get("title", "")[:200],
            summary=raw.get("summary", ""),
            detected_at=raw.get("detected_at", datetime.now(timezone.utc).isoformat()),
            source_url=raw.get("source_url", ""),
            positioning_opportunity=raw.get("positioning_opportunity", ""),
            threat_level=raw.get("threat_level", "medium") if raw.get("threat_level") in valid_threats else "medium",
        )
    except (KeyError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def competitive_intel_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Competitive Intelligence

    Reads:   state["raw_content"]
    Writes:  state["competitor_activities"],
             state["competitive_landscape_summary"]

    Strategy:
    1. Filter raw_content to items mentioning known competitors
    2. Batch-process competitor content through LLM
    3. Validate and de-duplicate activities
    4. Generate landscape summary
    5. Identify TADA positioning opportunities
    """
    node_name = "competitive_intel"
    start_time = time.time()

    trace = _langfuse.trace(
        name=node_name,
        id=f"{state['run_id']}-{node_name}",
        metadata={"run_mode": state["run_mode"]},
    )
    langfuse_handler = CallbackHandler(trace_id=trace.id)

    try:
        raw_items: List[RawContentItem] = state.get("raw_content", [])

        # Filter to competitor-relevant content
        competitor_items = [item for item in raw_items if _is_competitor_content(item)]
        trace.event(name="content_filtered", message=f"{len(competitor_items)}/{len(raw_items)} items are competitor-related")

        if not competitor_items:
            return {
                **state,
                "competitor_activities": [],
                "competitive_landscape_summary": "No competitor activity detected in current content batch.",
                "node_timings": {**state.get("node_timings", {}), node_name: time.time() - start_time},
            }

        # Process in batches of 10
        BATCH_SIZE = 10
        batches = [competitor_items[i: i + BATCH_SIZE] for i in range(0, len(competitor_items), BATCH_SIZE)]

        all_raw_activities: List[Dict[str, Any]] = []
        landscape_summaries: List[str] = []
        positioning_opportunities: List[str] = []

        for batch_idx, batch in enumerate(batches):
            span = trace.span(name=f"batch_{batch_idx}", input={"size": len(batch)})
            try:
                user_msg = COMPETITIVE_INTEL_USER_TEMPLATE.format(
                    competitors=", ".join(KNOWN_COMPETITORS),
                    n=len(batch),
                    content_batch=_format_batch(batch),
                )
                response = _llm.invoke(
                    [
                        SystemMessage(content=COMPETITIVE_INTEL_SYSTEM_PROMPT),
                        HumanMessage(content=user_msg),
                    ],
                    config={"callbacks": [langfuse_handler]},
                )

                raw_text = response.content.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]

                parsed = json.loads(raw_text)
                all_raw_activities.extend(parsed.get("activities", []))
                if summary := parsed.get("competitive_landscape_summary"):
                    landscape_summaries.append(summary)
                positioning_opportunities.extend(parsed.get("tada_positioning_opportunities", []))
                span.end(output={"activities_found": len(parsed.get("activities", []))})

            except Exception as e:
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"batch {batch_idx}: {e}", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                span.end(level="ERROR", status_message=str(e))

        # Validate activities
        seen: set[str] = set()
        activities: List[CompetitorActivity] = []
        for raw_act in all_raw_activities:
            act = _validate_activity(raw_act)
            if act:
                key = f"{act['competitor_name']}::{act['title']}"
                if key not in seen:
                    seen.add(key)
                    activities.append(act)

        # Sort by threat level
        threat_order = {"high": 0, "medium": 1, "low": 2}
        activities.sort(key=lambda a: threat_order.get(a["threat_level"], 99))

        # Merge landscape summaries
        landscape_summary = " ".join(landscape_summaries) if landscape_summaries else "Insufficient data for landscape summary."

        # Store positioning opportunities in recommendations
        current_recs = state.get("recommendations", {})
        current_recs.setdefault("sales", [])
        for opp in positioning_opportunities[:5]:
            current_recs["sales"].append({"type": "competitive_positioning", "content": opp})

        trace.update(output={"activities": len(activities), "high_threat": sum(1 for a in activities if a["threat_level"] == "high")})

        elapsed = time.time() - start_time
        return {
            **state,
            "competitor_activities": activities,
            "competitive_landscape_summary": landscape_summary,
            "recommendations": current_recs,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }

    except Exception as e:
        elapsed = time.time() - start_time
        errors = state.get("errors", [])
        errors.append({"node": node_name, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
        trace.event(name="node_error", level="ERROR", message=str(e))
        return {
            **state,
            "competitor_activities": state.get("competitor_activities", []),
            "competitive_landscape_summary": state.get("competitive_landscape_summary", ""),
            "errors": errors,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }
