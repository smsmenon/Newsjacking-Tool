from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Article:
    title: str
    source: str
    category: str
    url: str
    publication_date: str
    full_text: str
    author: str | None = None


@dataclass
class SignalScore:
    supply_chain_relevance: float
    executive_importance: float
    business_impact: float
    technology_relevance: float
    tada_alignment: float

    @property
    def final_score(self) -> float:
        weighted = (
            self.supply_chain_relevance * 0.30
            + self.executive_importance * 0.20
            + self.business_impact * 0.20
            + self.technology_relevance * 0.15
            + self.tada_alignment * 0.15
        )
        return round(weighted, 2)


@dataclass
class Signal:
    headline: str
    source: str
    date: str
    url: str
    signal_type: str
    summary: str
    evidence: str
    score: SignalScore
    keywords: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    is_breaking: bool = False
    is_major_analyst_report: bool = False

    @property
    def surfaced(self) -> bool:
        return self.score.final_score >= 7 or self.is_breaking or self.is_major_analyst_report


@dataclass
class Perspective:
    what_happened: str
    why_it_matters: str
    potential_impact: str
    traditional_response: str
    tada_response: str
    detect: str
    decide: str
    do: str


@dataclass
class ContentOpportunity:
    linkedin_post: dict[str, str]
    thought_leadership_article: dict[str, Any]
    newsletter_topic: dict[str, Any]
    sales_talking_point: dict[str, str]
    executive_briefing: dict[str, str]
    review_status: str = "draft"


@dataclass
class DigestItem:
    signal: Signal
    business_impact: str
    tada_perspective: Perspective
    suggested_action: str
    content_opportunity: ContentOpportunity

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signal"]["score"]["final_score"] = self.signal.score.final_score
        payload["signal"]["surfaced"] = self.signal.surfaced
        return payload


@dataclass
class DailyDigest:
    generated_at: str
    top_signals: list[DigestItem]
    emerging_themes: list[str]
    top_opportunities: list[str]
    top_risks: list[str]
    sales_talking_points: list[str]
    recommended_content_topics: list[str]

    @classmethod
    def create(cls, items: list[DigestItem]) -> "DailyDigest":
        themes = sorted({kw for item in items for kw in item.signal.keywords})[:8]
        opportunities = [item.content_opportunity.executive_briefing["opportunity"] for item in items[:5]]
        risks = sorted({risk for item in items for risk in item.signal.risks})[:8]
        talking_points = [
            item.content_opportunity.sales_talking_point["suggested_discovery_question"]
            for item in items[:5]
        ]
        topics = [
            item.content_opportunity.thought_leadership_article["title"]
            for item in items[:5]
        ]
        return cls(
            generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            top_signals=items,
            emerging_themes=themes,
            top_opportunities=opportunities,
            top_risks=risks,
            sales_talking_points=talking_points,
            recommended_content_topics=topics,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["top_signals"] = [item.to_dict() for item in self.top_signals]
        return payload

