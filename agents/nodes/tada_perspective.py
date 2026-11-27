"""
TADA Intelligence Platform — TADA Perspective Agent
====================================================
For each surfaced signal this agent generates a structured perspective
using TADA's "Detect → Decide → Do" philosophy:

  - What Happened            (objective summary)
  - Why It Matters           (relevance for supply chain leaders)
  - Potential Impact         (quantified where possible)
  - Traditional Response     (how companies typically react)
  - TADA Response            (how TADA-enabled companies react differently)
  - Detect → Decide → Do     (maps the signal to TADA's 3-step model)
  - Expected Business Outcome (measurable outcomes from the TADA approach)

Model recommendation: claude-3-5-sonnet or claude-3-opus
Temperature: 0.4  (needs some creativity for narratives, but still grounded)
Langfuse trace name: "tada_perspective"
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

from agents.state import AgentState, DetectedSignal, TADAPerspective

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

_llm = ChatAnthropic(
    model=os.getenv("TADA_PERSPECTIVE_MODEL", "claude-3-5-sonnet-20241022"),
    temperature=0.4,
    max_tokens=2048,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

TADA_PERSPECTIVE_SYSTEM_PROMPT = """You are TADA's Chief Intelligence Analyst. TADA is a content intelligence platform that helps supply chain and operations leaders move from reactive to proactive decision-making using the "Detect → Decide → Do" framework.

## TADA's Core Philosophy
Traditional organisations react to disruptions after they happen. TADA-enabled organisations:
- DETECT: Spot signals early before they become crises
- DECIDE: Make data-driven decisions with AI-synthesised intelligence
- DO: Execute targeted actions faster than competitors

## Your Voice
- Authoritative but accessible — write for a C-suite supply chain executive
- Specific — use numbers, timeframes, percentages where possible
- Provocative — make the reader feel the urgency without being alarmist
- Solutions-oriented — always end with what TADA enables the reader to DO

## Key Personas You Serve
- Chief Supply Chain Officer (CSCO)
- VP of Procurement
- Head of Operations
- Chief Risk Officer
- CEO/CFO (for major signals)

## TADA Differentiator
Traditional Response = manual monitoring, committee meetings, delayed decisions
TADA Response = automated detection → AI synthesis → immediate action recommendations

Return ONLY valid JSON — no markdown, no prose outside the JSON.
"""

TADA_PERSPECTIVE_USER_TEMPLATE = """Generate a TADA perspective for the following signal.

## Signal
Headline: {headline}
Type: {signal_type}
Summary: {summary}
Evidence: {evidence}
Sources: {sources}
Score: {score}
Momentum: {momentum}
Keywords: {keywords}
Entities: {entities}

## Context (other recent signals in the same cluster)
{cluster_context}

Return a JSON object with this exact schema:
{{
  "what_happened": "string — 2-3 sentences. Objective, factual description of the event/development. Include specific numbers, dates, companies where available.",
  "why_it_matters": "string — 2-3 sentences. Explain the business significance for supply chain executives. Connect to real operational/financial consequences.",
  "potential_impact": "string — 2-3 sentences. Quantify where possible (e.g. '$X billion market', 'X% cost increase', 'X-week lead time extension'). Cover both near-term and medium-term impact.",
  "traditional_response": "string — 1-2 sentences. How do most organisations currently handle this? Highlight the lag, cost, or risk of the status quo.",
  "tada_response": "string — 2-3 sentences. How does a TADA-enabled organisation respond differently? Be specific about speed, precision, and outcomes.",
  "detect": "string — 1 sentence. What specific signal would TADA detect, from which source types, how early?",
  "decide": "string — 1 sentence. What decision framework or analysis does TADA surface to the leadership team?",
  "do": "string — 1 sentence. What concrete action does TADA recommend and to whom?",
  "expected_business_outcome": "string — 2 sentences. Measurable business outcome when TADA's approach is used vs. the traditional approach. Include a metric or percentage where plausible.",
  "urgency": "immediate|this_week|this_month|watch"
}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_cluster_context(signal: DetectedSignal, all_signals: List[DetectedSignal]) -> str:
    """Return summaries of other signals in the same cluster."""
    cluster_id = signal.get("cluster_id")
    if not cluster_id:
        return "No additional context — this signal stands alone."

    related = [
        s for s in all_signals
        if s.get("cluster_id") == cluster_id and s["signal_id"] != signal["signal_id"]
    ]
    if not related:
        return "No additional context — this signal stands alone."

    lines = [f"- {s['headline']} ({s['source_names'][0] if s['source_names'] else 'unknown'})" for s in related[:4]]
    return "\n".join(lines)


def _call_llm_single(
    signal: DetectedSignal,
    cluster_context: str,
    langfuse_handler: CallbackHandler,
) -> Optional[TADAPerspective]:
    """Call LLM for a single signal and return parsed TADAPerspective."""
    user_msg = TADA_PERSPECTIVE_USER_TEMPLATE.format(
        headline=signal["headline"],
        signal_type=signal["signal_type"],
        summary=signal["summary"],
        evidence=signal["evidence"],
        sources=", ".join(signal["source_names"]),
        score=signal["score"]["final_score"],
        momentum=signal["momentum"],
        keywords=", ".join(signal["keywords"]),
        entities=", ".join(signal["entities"]),
        cluster_context=cluster_context,
    )

    response = _llm.invoke(
        [
            SystemMessage(content=TADA_PERSPECTIVE_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ],
        config={"callbacks": [langfuse_handler]},
    )

    raw_text = response.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    raw = json.loads(raw_text)

    valid_urgency = {"immediate", "this_week", "this_month", "watch"}
    urgency = raw.get("urgency", "this_month")
    if urgency not in valid_urgency:
        urgency = "this_month"

    return TADAPerspective(
        signal_id=signal["signal_id"],
        what_happened=raw.get("what_happened", ""),
        why_it_matters=raw.get("why_it_matters", ""),
        potential_impact=raw.get("potential_impact", ""),
        traditional_response=raw.get("traditional_response", ""),
        tada_response=raw.get("tada_response", ""),
        detect=raw.get("detect", ""),
        decide=raw.get("decide", ""),
        do=raw.get("do", ""),
        expected_business_outcome=raw.get("expected_business_outcome", ""),
        urgency=urgency,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Main node function
# ---------------------------------------------------------------------------

def tada_perspective_node(state: AgentState) -> AgentState:
    """
    LangGraph node: TADA Perspective

    Reads:   state["surfaced_signals"], state["detected_signals"]
    Writes:  state["tada_perspectives"]

    For each surfaced signal, generates a full TADA perspective
    (Detect → Decide → Do narrative + urgency classification).

    Processes signals sequentially to avoid rate limits; uses exponential
    back-off on failures and skips non-critical signals after 3 errors.
    """
    node_name = "tada_perspective"
    start_time = time.time()

    trace = _langfuse.trace(
        name=node_name,
        id=f"{state['run_id']}-{node_name}",
        metadata={"run_mode": state["run_mode"]},
    )
    langfuse_handler = CallbackHandler(trace_id=trace.id)

    try:
        surfaced: List[DetectedSignal] = state.get("surfaced_signals", [])
        all_signals: List[DetectedSignal] = state.get("detected_signals", [])

        if not surfaced:
            trace.event(name="no_surfaced_signals", level="WARNING")
            return {
                **state,
                "tada_perspectives": [],
                "node_timings": {**state.get("node_timings", {}), node_name: time.time() - start_time},
            }

        perspectives: List[TADAPerspective] = []
        consecutive_errors = 0

        for signal in surfaced:
            if consecutive_errors >= 3:
                # After 3 consecutive failures, skip remaining non-breaking signals
                if not signal.get("is_breaking"):
                    continue

            span = trace.span(name=f"perspective_{signal['signal_id']}", input={"headline": signal["headline"]})
            try:
                cluster_ctx = _get_cluster_context(signal, all_signals)
                perspective = _call_llm_single(signal, cluster_ctx, langfuse_handler)
                if perspective:
                    perspectives.append(perspective)
                    consecutive_errors = 0
                span.end(output={"urgency": perspective["urgency"] if perspective else "skipped"})
            except json.JSONDecodeError as je:
                consecutive_errors += 1
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"JSON parse error for {signal['signal_id']}: {je}",
                     "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                span.end(level="ERROR", status_message=str(je))
            except Exception as e:
                consecutive_errors += 1
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"Error for {signal['signal_id']}: {e}",
                     "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                span.end(level="ERROR", status_message=str(e))
                # Simple back-off
                time.sleep(min(2 ** consecutive_errors, 30))

        # Sort by urgency priority
        urgency_order = {"immediate": 0, "this_week": 1, "this_month": 2, "watch": 3}
        perspectives.sort(key=lambda p: urgency_order.get(p["urgency"], 99))

        trace.update(output={"perspectives_generated": len(perspectives)})

        elapsed = time.time() - start_time
        return {
            **state,
            "tada_perspectives": perspectives,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }

    except Exception as e:
        elapsed = time.time() - start_time
        errors = state.get("errors", [])
        errors.append({"node": node_name, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
        trace.event(name="node_error", level="ERROR", message=str(e))
        return {
            **state,
            "tada_perspectives": state.get("tada_perspectives", []),
            "errors": errors,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }
