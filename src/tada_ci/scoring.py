from __future__ import annotations

import re

from .models import Article, Signal, SignalScore

SUPPLY_CHAIN_TERMS = {
    "supply chain",
    "tariff",
    "supplier",
    "inventory",
    "logistics",
    "transportation",
    "demand",
    "planning",
    "manufacturing",
    "procurement",
    "resilience",
    "capacity",
    "schedule",
}

EXECUTIVE_TERMS = {
    "leader",
    "leaders",
    "margin",
    "revenue",
    "risk",
    "cost",
    "compliance",
    "growth",
    "board",
    "strategy",
    "service",
    "inflation",
}

TECH_TERMS = {
    "ai",
    "agentic",
    "automation",
    "decision intelligence",
    "analytics",
    "simulation",
    "digital",
}

TADA_TERMS = {
    "detect",
    "decide",
    "do",
    "action",
    "response",
    "decision",
    "outcome",
    "visibility",
    "continuous planning",
    "workflow",
    "workflows",
}

RISK_TERMS = {
    "tariff": "Tariff exposure",
    "shortage": "Supply shortage",
    "disruption": "Operational disruption",
    "delay": "Delivery delay",
    "inflation": "Cost inflation",
    "geopolitical": "Geopolitical risk",
    "labor": "Labor constraint",
}

OPPORTUNITY_TERMS = {
    "nearshoring": "Network redesign and nearshoring strategy",
    "reshoring": "Domestic manufacturing expansion",
    "ai": "AI-assisted decision workflows",
    "automation": "Automated response orchestration",
    "inventory": "Inventory optimization",
    "supplier": "Supplier risk management",
}


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text.lower()) is not None


def _match_count(text: str, terms: set[str]) -> int:
    return sum(1 for term in terms if _contains_term(text, term))


def _term_score(text: str, terms: set[str], base: float = 3.5, weight: float = 0.9) -> float:
    lower = text.lower()
    matches = _match_count(lower, terms)
    return min(10.0, round(base + matches * weight, 2))


def classify_signal(article: Article) -> str:
    text = f"{article.title} {article.full_text}".lower()
    if "tariff" in text or "regulation" in text:
        return "Regulatory Change"
    if "ai" in text or "automation" in text or "agentic" in text:
        return "Technology Adoption"
    if "supplier" in text or "shortage" in text:
        return "Supplier Risk"
    if "inventory" in text or "demand" in text:
        return "Inventory Trend"
    if "manufacturing" in text or "capacity" in text or "schedule" in text:
        return "Manufacturing Constraint"
    return "Market Shift"


def extract_keywords(article: Article) -> list[str]:
    text = f"{article.title} {article.full_text}".lower()
    candidates = sorted(SUPPLY_CHAIN_TERMS | EXECUTIVE_TERMS | TECH_TERMS | TADA_TERMS)
    return [term for term in candidates if _contains_term(text, term)][:12]


def extract_risks(article: Article) -> list[str]:
    text = f"{article.title} {article.full_text}".lower()
    return sorted({label for term, label in RISK_TERMS.items() if _contains_term(text, term)})


def extract_opportunities(article: Article) -> list[str]:
    text = f"{article.title} {article.full_text}".lower()
    return sorted({label for term, label in OPPORTUNITY_TERMS.items() if _contains_term(text, term)})


def score_article(article: Article) -> SignalScore:
    text = f"{article.title} {article.full_text}"
    business_score = _term_score(text, EXECUTIVE_TERMS | set(RISK_TERMS), base=5.0, weight=0.95)
    return SignalScore(
        supply_chain_relevance=_term_score(text, SUPPLY_CHAIN_TERMS, base=4.5, weight=0.9),
        executive_importance=_term_score(text, EXECUTIVE_TERMS, base=5.0, weight=0.95),
        business_impact=business_score,
        technology_relevance=_term_score(text, TECH_TERMS, base=4.0, weight=1.0),
        tada_alignment=_term_score(text, TADA_TERMS, base=5.0, weight=0.95),
    )


def pick_theme(signal: Signal) -> str:
    for keyword in signal.keywords:
        if keyword in SUPPLY_CHAIN_TERMS:
            return keyword
    if signal.keywords:
        return signal.keywords[0]
    return signal.signal_type.lower()


def article_to_signal(article: Article) -> Signal:
    text = article.full_text.strip().replace("\n", " ")
    summary = text[:280] + ("..." if len(text) > 280 else "")
    evidence = text[:420] + ("..." if len(text) > 420 else "")
    score = score_article(article)
    signal_type = classify_signal(article)
    return Signal(
        headline=article.title,
        source=article.source,
        date=article.publication_date,
        url=article.url,
        signal_type=signal_type,
        summary=summary,
        evidence=evidence,
        score=score,
        keywords=extract_keywords(article),
        risks=extract_risks(article),
        opportunities=extract_opportunities(article),
        is_breaking="breaking" in article.title.lower(),
        is_major_analyst_report=article.source.lower() in {"gartner", "idc", "forrester"},
    )
