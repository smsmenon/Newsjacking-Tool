from __future__ import annotations

from .models import ContentOpportunity, Perspective, Signal
from .scoring import pick_theme


def build_content(signal: Signal, perspective: Perspective) -> ContentOpportunity:
    theme = pick_theme(signal).title()
    score = signal.score.final_score
    hook = perspective.tada_response.split(". ")[0].rstrip(".") + "."
    return ContentOpportunity(
        linkedin_post={
            "hook": hook,
            "narrative": (
                f"{signal.headline} -- {perspective.traditional_response} We disagree. "
                f"{perspective.tada_response}"
            ),
            "key_insight": perspective.tada_response,
            "cta": "Where is your team still detecting change faster than it can act on it?",
        },
        thought_leadership_article={
            "title": f"From Visibility to Action: What {theme} Signals Mean for Supply Chain Leaders",
            "executive_summary": (
                f"This article interprets a score {score} market signal through TADA's Detect, Decide, Do lens."
            ),
            "outline": [
                "What changed in the market",
                "Why traditional planning cycles are exposed",
                "The decision gap leaders must close",
                "How Detect, Decide, Do improves response speed",
                "Business outcomes to measure",
            ],
            "key_arguments": [
                "Volatility turns static visibility into a lagging indicator.",
                "AI should recommend decisions and actions, not produce generic commentary.",
                "Supply chain intelligence must connect directly to execution workflows.",
            ],
        },
        newsletter_topic={
            "headline": f"{theme}: A Signal Worth Watching",
            "summary": signal.summary,
            "three_key_takeaways": [
                perspective.why_it_matters,
                perspective.potential_impact,
                perspective.do,
            ],
        },
        sales_talking_point={
            "customer_problem": "Teams see disruption in dashboards but struggle to coordinate a fast response.",
            "business_impact": perspective.potential_impact,
            "recommended_discussion": (
                "Use this signal to discuss how decision intelligence shortens response cycles "
                "between planning and execution."
            ),
            "suggested_discovery_question": (
                "When market conditions change, how long does it take your team to move from detection "
                "to an approved action?"
            ),
        },
        executive_briefing={
            "situation": perspective.what_happened,
            "risk": perspective.potential_impact,
            "opportunity": perspective.do,
            "recommendation": "Review exposure, define decision thresholds, and automate the response path.",
        },
    )

