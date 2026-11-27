from __future__ import annotations

from collections import Counter
from typing import Any


def build_weekly_report(digest: dict[str, Any]) -> dict[str, Any]:
    items = digest.get("top_signals", [])
    signal_types = Counter(item["signal"]["signal_type"] for item in items)
    sources = Counter(item["signal"]["source"] for item in items)
    scores = [item["signal"]["score"]["final_score"] for item in items]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0

    return {
        "title": "TADA Weekly Strategic Intelligence Report",
        "market_overview": (
            "The strongest surfaced signals point to volatility requiring faster movement "
            "from detection to coordinated execution."
        ),
        "major_trends": [name for name, _ in signal_types.most_common()],
        "major_risks": digest.get("top_risks", []),
        "ai_adoption_trends": [
            item["signal"]["headline"]
            for item in items
            if "ai" in item["signal"].get("keywords", [])
            or item["signal"]["signal_type"] == "Technology Adoption"
        ],
        "manufacturing_trends": [
            item["signal"]["headline"]
            for item in items
            if item["signal"]["signal_type"] == "Manufacturing Constraint"
        ],
        "procurement_trends": [
            item["signal"]["headline"]
            for item in items
            if "supplier" in item["signal"].get("keywords", [])
        ],
        "strategic_recommendations": [
            "Prioritize signals with measurable cost, service, inventory, and supplier exposure.",
            "Use Detect, Decide, Do language consistently across leadership, sales, and marketing.",
            "Keep all external content in human review until approved.",
        ],
        "content_calendar_recommendations": digest.get("recommended_content_topics", []),
        "sales_enablement_opportunities": digest.get("sales_talking_points", []),
        "leadership_talking_points": [
            "Visibility without decision velocity leaves teams reacting late.",
            "AI should support response orchestration, not generic market commentary.",
            "Market volatility is a reason to connect planning and execution workflows.",
        ],
        "metrics": {
            "surfaced_signals": len(items),
            "average_score": average_score,
            "top_sources": dict(sources.most_common(5)),
        },
    }

