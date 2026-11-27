"""
TADA Intelligence Platform — Signal Detection Agent
=====================================================
Takes processed/collected content and:
  1. Identifies discrete signals using structured LLM output
  2. Clusters related signals by topic
  3. Scores each signal across 5 dimensions
  4. Validates signals across multiple sources
  5. Returns SignalOutput enriched with confidence, strength, momentum

Model recommendation: claude-3-5-sonnet  (or gpt-4o)
Temperature: 0.2  (low — we want structured, deterministic output)
Langfuse trace name: "signal_detection"
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langfuse import Langfuse
from langfuse.callback import CallbackHandler

from agents.state import AgentState, DetectedSignal, RawContentItem, SignalScore

# ---------------------------------------------------------------------------
# Langfuse observability
# ---------------------------------------------------------------------------

_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

_llm = ChatAnthropic(
    model=os.getenv("SIGNAL_DETECTION_MODEL", "claude-3-5-sonnet-20241022"),
    temperature=0.2,
    max_tokens=4096,
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
)

# ---------------------------------------------------------------------------
# System prompt (inline; canonical version lives in prompts/system-prompts.md)
# ---------------------------------------------------------------------------

SIGNAL_DETECTION_SYSTEM_PROMPT = """You are the Signal Detection Agent for TADA, a supply chain intelligence platform.

Your job is to identify DISCRETE, ACTIONABLE SIGNALS from a batch of content items. A signal is a specific development that could meaningfully affect supply chain leaders, executives, or businesses that TADA serves.

## Signal Types
- disruption: Supply chain disruptions, geopolitical events, natural disasters affecting logistics
- trend: Emerging patterns in technology adoption, buyer behaviour, market shifts
- opportunity: New market openings, budget releases, procurement cycles, buying signals
- risk: Regulatory changes, tariffs, cyber threats, financial instability
- regulation: New laws, compliance requirements, government policies
- innovation: New technologies, methodologies, platforms relevant to supply chain

## Scoring Dimensions (0–10 each)
- supply_chain_relevance: How directly does this affect supply chain operations?
- executive_importance: Would a C-suite supply chain executive care about this?
- business_impact: Does this create or destroy significant business value?
- technology_relevance: Does this involve technology TADA's clients use or evaluate?
- tada_alignment: How well does this match TADA's "Detect → Decide → Do" use case?

## Weighted Final Score
final_score = (supply_chain_relevance × 0.30) + (executive_importance × 0.20) + (business_impact × 0.20) + (technology_relevance × 0.15) + (tada_alignment × 0.15)

## Output Rules
- Only emit signals with final_score ≥ 5.0
- A breaking signal (is_breaking=true) is surfaced regardless of score
- Each signal must reference at least one source_id
- evidence must include a direct quote or specific data point
- momentum: "rising" if multiple recent sources confirm it, "declining" if it is being superseded, "stable" otherwise
- cluster signals on the same topic/event under the same cluster_label

Return ONLY valid JSON — no markdown, no prose.
"""

SIGNAL_DETECTION_USER_TEMPLATE = """Analyse the following {n} content items and identify all meaningful signals.

Content batch:
{content_batch}

Return a JSON object with this exact schema:
{{
  "signals": [
    {{
      "headline": "string — ≤120 chars, punchy, specific",
      "signal_type": "disruption|trend|opportunity|risk|regulation|innovation",
      "summary": "string — 2-3 sentence summary of the signal",
      "evidence": "string — direct quote or specific data point from the source",
      "source_ids": ["list of content item IDs that support this signal"],
      "source_names": ["list of source names"],
      "keywords": ["list of 5-10 keywords"],
      "entities": ["companies, geographies, technologies mentioned"],
      "cluster_label": "string — short label for grouping related signals (e.g. 'Port congestion Asia', 'AI in procurement')",
      "is_breaking": false,
      "confidence": 0.85,
      "momentum": "rising|stable|declining",
      "score": {{
        "supply_chain_relevance": 8.5,
        "executive_importance": 7.0,
        "business_impact": 7.5,
        "technology_relevance": 6.0,
        "tada_alignment": 8.0,
        "final_score": 7.6
      }}
    }}
  ],
  "processing_notes": "string — any observations about the batch quality or coverage gaps"
}}
"""


# ---------------------------------------------------------------------------
# Core processing helpers
# ---------------------------------------------------------------------------

def _format_content_batch(items: List[RawContentItem], max_chars_per_item: int = 1500) -> str:
    """Serialise content items to a compact string the LLM can parse."""
    lines = []
    for item in items:
        body_preview = item["body"][:max_chars_per_item].strip()
        lines.append(
            f"[ID:{item['id']}] SOURCE:{item['source_name']} ({item['source_type']}) "
            f"DATE:{item['published_at']}\n"
            f"TITLE: {item['title']}\n"
            f"BODY: {body_preview}\n"
            f"URL: {item['source_url']}\n"
        )
    return "\n---\n".join(lines)


def _make_signal_id(headline: str) -> str:
    """Deterministic but unique signal ID."""
    digest = hashlib.sha256(headline.encode()).hexdigest()[:12]
    return f"sig_{digest}"


def _compute_final_score(score: Dict[str, float]) -> float:
    """Apply TADA's weighted scoring formula."""
    return round(
        score["supply_chain_relevance"] * 0.30
        + score["executive_importance"] * 0.20
        + score["business_impact"] * 0.20
        + score["technology_relevance"] * 0.15
        + score["tada_alignment"] * 0.15,
        2,
    )


def _validate_signal(raw: Dict[str, Any]) -> Optional[DetectedSignal]:
    """Validate and normalise a raw signal dict from the LLM."""
    try:
        score_raw = raw.get("score", {})
        score: SignalScore = {
            "supply_chain_relevance": float(score_raw.get("supply_chain_relevance", 0)),
            "executive_importance": float(score_raw.get("executive_importance", 0)),
            "business_impact": float(score_raw.get("business_impact", 0)),
            "technology_relevance": float(score_raw.get("technology_relevance", 0)),
            "tada_alignment": float(score_raw.get("tada_alignment", 0)),
            "final_score": 0.0,
        }
        score["final_score"] = _compute_final_score(score)

        if score["final_score"] < 5.0 and not raw.get("is_breaking", False):
            return None  # filter low-relevance signals

        return DetectedSignal(
            signal_id=_make_signal_id(raw["headline"]),
            headline=raw["headline"][:200],
            signal_type=raw.get("signal_type", "trend"),
            summary=raw.get("summary", ""),
            evidence=raw.get("evidence", ""),
            source_ids=raw.get("source_ids", []),
            source_names=raw.get("source_names", []),
            first_seen=datetime.now(timezone.utc).isoformat(),
            score=score,
            confidence=float(raw.get("confidence", 0.7)),
            momentum=raw.get("momentum", "stable"),
            keywords=raw.get("keywords", [])[:10],
            entities=raw.get("entities", [])[:15],
            cluster_id=raw.get("cluster_label"),
            is_breaking=bool(raw.get("is_breaking", False)),
            is_validated=len(raw.get("source_ids", [])) >= 2,
        )
    except (KeyError, ValueError, TypeError):
        return None


def _cluster_signals(signals: List[DetectedSignal]) -> Dict[str, List[str]]:
    """Group signal_ids by cluster_id."""
    clusters: Dict[str, List[str]] = {}
    for sig in signals:
        cid = sig.get("cluster_id") or "unclustered"
        clusters.setdefault(cid, []).append(sig["signal_id"])
    return clusters


def _call_llm_batch(
    items: List[RawContentItem],
    langfuse_handler: CallbackHandler,
) -> List[Dict[str, Any]]:
    """Send one batch of content to the LLM and parse the response."""
    content_str = _format_content_batch(items)
    user_msg = SIGNAL_DETECTION_USER_TEMPLATE.format(
        n=len(items),
        content_batch=content_str,
    )

    response = _llm.invoke(
        [
            SystemMessage(content=SIGNAL_DETECTION_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ],
        config={"callbacks": [langfuse_handler]},
    )

    raw_text = response.content.strip()
    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    parsed = json.loads(raw_text)
    return parsed.get("signals", [])


# ---------------------------------------------------------------------------
# Main node function — entry point for LangGraph
# ---------------------------------------------------------------------------

def signal_detection_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Signal Detection

    Reads:   state["raw_content"], state["source_quality_scores"]
    Writes:  state["detected_signals"], state["signal_clusters"],
             state["surfaced_signals"]

    Processing:
    1. Chunk raw_content into batches of 15 items (LLM context management)
    2. For each batch, call LLM with structured output prompt
    3. Parse, validate, score and de-duplicate signals
    4. Cluster signals by topic
    5. Filter surfaced signals (score >= 7 or is_breaking)
    6. Record node timing and any errors
    """
    node_name = "signal_detection"
    start_time = time.time()

    # Observability
    trace = _langfuse.trace(
        name=node_name,
        id=f"{state['run_id']}-{node_name}",
        metadata={"run_mode": state["run_mode"], "version": state["version"]},
    )
    langfuse_handler = CallbackHandler(trace_id=trace.id)

    try:
        raw_items: List[RawContentItem] = state.get("raw_content", [])
        if not raw_items:
            trace.event(name="no_content", level="WARNING", message="No raw content to process")
            return {
                **state,
                "detected_signals": [],
                "signal_clusters": {},
                "surfaced_signals": [],
                "node_timings": {**state.get("node_timings", {}), node_name: time.time() - start_time},
            }

        # Batch processing: 15 items per LLM call to stay within context limits
        BATCH_SIZE = 15
        batches = [raw_items[i: i + BATCH_SIZE] for i in range(0, len(raw_items), BATCH_SIZE)]

        all_raw_signals: List[Dict[str, Any]] = []
        for batch_idx, batch in enumerate(batches):
            trace.span(name=f"batch_{batch_idx}", input={"size": len(batch)})
            try:
                raw_sigs = _call_llm_batch(batch, langfuse_handler)
                all_raw_signals.extend(raw_sigs)
            except json.JSONDecodeError as je:
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"JSON parse error batch {batch_idx}: {je}", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
            except Exception as e:
                state.setdefault("errors", []).append(
                    {"node": node_name, "error": f"LLM error batch {batch_idx}: {e}", "timestamp": datetime.now(timezone.utc).isoformat()}
                )

        # Validate, score, de-duplicate
        seen_ids: set[str] = set()
        validated_signals: List[DetectedSignal] = []
        for raw_sig in all_raw_signals:
            sig = _validate_signal(raw_sig)
            if sig and sig["signal_id"] not in seen_ids:
                seen_ids.add(sig["signal_id"])
                validated_signals.append(sig)

        # Sort by final_score descending
        validated_signals.sort(key=lambda s: s["score"]["final_score"], reverse=True)

        # Cluster
        clusters = _cluster_signals(validated_signals)

        # Surfaced: score >= 7 or breaking
        surfaced = [s for s in validated_signals if s["score"]["final_score"] >= 7.0 or s["is_breaking"]]

        trace.event(
            name="signals_detected",
            level="DEFAULT",
            message=f"Detected {len(validated_signals)} signals, {len(surfaced)} surfaced",
        )
        trace.update(
            output={
                "total_signals": len(validated_signals),
                "surfaced": len(surfaced),
                "clusters": len(clusters),
            }
        )

        elapsed = time.time() - start_time
        return {
            **state,
            "detected_signals": validated_signals,
            "signal_clusters": clusters,
            "surfaced_signals": surfaced,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }

    except Exception as e:
        elapsed = time.time() - start_time
        errors = state.get("errors", [])
        errors.append({"node": node_name, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
        trace.event(name="node_error", level="ERROR", message=str(e))
        return {
            **state,
            "detected_signals": state.get("detected_signals", []),
            "signal_clusters": state.get("signal_clusters", {}),
            "surfaced_signals": state.get("surfaced_signals", []),
            "errors": errors,
            "node_timings": {**state.get("node_timings", {}), node_name: elapsed},
        }
