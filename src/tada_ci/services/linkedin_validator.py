"""
LinkedIn Content Validation for TADA Content Intelligence Platform.

Evaluates each discovered article against TADA's LinkedIn content strategy using
Llama 3.1 (local Ollama). Returns a verdict, angle recommendation, suggested post
direction, and what to avoid — replicating the manual process the content team used.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.request as _ur
from typing import Any

log = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
_CLAUDE_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _llm(prompt: str, max_tokens: int = 300) -> str:
    """Claude if ANTHROPIC_API_KEY is set, else local Ollama — this file previously called
    Ollama unconditionally with no fallback, so it silently returned the default 'Skip'
    result on any machine without a local Ollama server running."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        payload = json.dumps({
            "model": _CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = _ur.Request(
            _ANTHROPIC_URL, data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }, method="POST",
        )
        with _ur.urlopen(req, timeout=30, context=_SSL_CTX) as r:
            return json.loads(r.read())["content"][0]["text"].strip()
    payload = json.dumps({
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
    }).encode()
    req = _ur.Request(
        "http://localhost:11434/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with _ur.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["response"].strip()

# ---------------------------------------------------------------------------
# TADA LinkedIn strategy context — baked into every validation prompt
# ---------------------------------------------------------------------------
_TADA_CONTEXT = """
COMPANY: TADA Cognitive Solutions
POSITIONING: AI-native System of Action for manufacturing supply chain. Built on Digital Duplicate (patented) + Industry Action Graph. Sits on top of existing ERP/CRM/TMS — no rip-and-replace.
KEY DIFFERENTIATOR: TADA operates on the business operating model (live ESM), not just the data. SAP Joule, Microsoft Copilot, Salesforce Agentforce = C-3PO (language model, no agency). TADA = Anakin Skywalker (connected to the Force, acts within the live business model). Competitors are L1 agents. TADA is L2.
THREE COMMAND LAYERS: Strategic (10 weeks–10 months), Operational (10 days–10 weeks), Tactical (1–10 days).
SIX SYSTEMS OF ACTION: Sourcing & Procurement, Supply-Chain & Logistics, Production Planning, Distribution & Finished Goods Inventory, Service & Support, Strategic Accounts.
PROOF POINTS: $32M cost savings, $11M productivity improvement, 20% working capital reduction, 6 weeks to value. 35+ Fortune 500 customers including Caterpillar, GE Healthcare, Cummins, Oshkosh.
STAT: 95% of GenAI pilots show zero P&L impact (MIT NANDA). McKinsey: 30–50% EBITDA erasure from supply chain volatility.

LINKEDIN CONTENT THEMES (use these exact names):
1. ERP Trap — ERP is a system of record, not action. CIOs/COOs drowning in data but starved of decisions. TADA sits above ERP.
2. Volatility — Tariffs, geopolitical disruption, demand shocks. The case for operational AI that acts in real-time.
3. Infrastructure Trap — Companies spending on AI infrastructure but getting zero P&L output. GenAI pilots that don't survive contact with operations.
4. AI (Board Approved) — The shift from "AI strategy" to "AI P&L accountability". What boards actually want from AI.
5. Wizarding World — The R2-D2/C-3PO/Anakin/Yoda analogy. L1 vs L2 agents. Why most AI is C-3PO (speaks, doesn't act).

TARGET AUDIENCE: Supply chain executives — CSCOs, COOs, VP Supply Chain, SVP Operations. Fortune 500 manufacturing.

POST FORMAT: 150–250 words. Plain text. Punchy opening line. One clear thesis. No bullet dumps. Contrarian when genuinely warranted.

BANNED PHRASES: "game-changer", "revolutionizing", "unlocking value", "digital transformation journey", "now more than ever", "in today's fast-paced world", "seamlessly", "robust", "leverage", "utilize".

VERDICT OPTIONS:
- Strong fit: Article directly validates or challenges a TADA theme. Can generate a post this week.
- Good fit with refinement: Relevant but needs TADA's angle added. Needs work before posting.
- Weak fit: Loosely connected. Hard to make TADA-relevant without forcing it.
- Not a fit: Off-topic, too generic, or would dilute TADA's positioning.

ANGLE OPTIONS:
- Alignment: Article supports TADA's thesis directly. Post amplifies it.
- Contrarian: Article represents conventional wisdom that TADA disagrees with. Post challenges it.
- Expansion: Article covers adjacent territory. Post takes it further using TADA's lens.

RECOMMENDATION OPTIONS:
- Use now: Strong enough to post this week as-is or with light editing.
- Save for later: Good content but not timely or needs a better hook.
- Background reference: Keep as a reference data point, don't post directly.
- Skip: Not worth using for LinkedIn.
"""

_PROMPT_TEMPLATE = """{context}

---

ARTICLE TO EVALUATE:
Title: {title}
Source: {source}
Published: {published_at}
Content excerpt: {content_excerpt}

---

Evaluate this article against TADA's LinkedIn content strategy. Use the labeled format below EXACTLY. Do not add extra sections.

VERDICT: [Strong fit / Good fit with refinement / Weak fit / Not a fit]
WHY: [1-2 sentences explaining the verdict]
TADA_THEMES: [comma-separated list from the 5 themes above, or "None"]
ANGLE: [Alignment / Contrarian / Expansion]
POST_DIRECTION: [1-2 sentences on what the LinkedIn post should say — the specific argument or hook, not generic advice]
WHAT_TO_AVOID: [1 sentence on the specific trap or cliché this post must NOT fall into]
RECOMMENDATION: [Use now / Save for later / Background reference / Skip]
"""


def validate_for_linkedin(article: dict) -> dict[str, Any]:
    """
    Run a single article through TADA's LinkedIn content validation.

    Parameters
    ----------
    article:
        Article dict from the discovery pipeline (must have title, content, source, published_at).

    Returns
    -------
    dict with keys: verdict, why, tada_themes, angle, post_direction, what_to_avoid, recommendation
    """
    title = article.get("title", "")
    source = article.get("source", "Unknown")
    published_at = article.get("published_at", "")
    # Was previously `article.get("content", "") or bullets[0] if bullets else ""` — Python's
    # `if/else` binds looser than `or`, so that actually parsed as
    # `(content or bullets[0]) if bullets else ""`: whenever summary_bullets was empty, real
    # content got discarded to "" regardless. Parenthesized explicitly now.
    content = article.get("content", "") or (
        article.get("summary_bullets", [""])[0] if article.get("summary_bullets") else ""
    )
    content_excerpt = content[:800] if content else title

    prompt = _PROMPT_TEMPLATE.format(
        context=_TADA_CONTEXT,
        title=title,
        source=source,
        published_at=published_at,
        content_excerpt=content_excerpt,
    )

    try:
        response_text = _llm(prompt, max_tokens=300)
        return _parse_validation(response_text)
    except Exception as exc:
        log.debug("linkedin_validator failed for %s: %s", title[:60], exc)
        return _default_validation()


def _parse_validation(text: str) -> dict[str, Any]:
    """Parse labeled-line output from Llama into a structured dict."""
    result: dict[str, Any] = {}
    key_map = {
        "VERDICT": "verdict",
        "WHY": "why",
        "TADA_THEMES": "tada_themes",
        "ANGLE": "angle",
        "POST_DIRECTION": "post_direction",
        "WHAT_TO_AVOID": "what_to_avoid",
        "RECOMMENDATION": "recommendation",
    }

    for line in text.splitlines():
        for label, field in key_map.items():
            if line.startswith(f"{label}:"):
                value = line[len(label) + 1:].strip()
                result[field] = value
                break

    # Normalise verdict to known values
    verdict = result.get("verdict", "").lower()
    if "strong" in verdict:
        result["verdict"] = "Strong fit"
    elif "good" in verdict:
        result["verdict"] = "Good fit with refinement"
    elif "weak" in verdict:
        result["verdict"] = "Weak fit"
    else:
        result["verdict"] = "Not a fit"

    # Normalise recommendation
    rec = result.get("recommendation", "").lower()
    if "use now" in rec or "use_now" in rec:
        result["recommendation"] = "Use now"
    elif "save" in rec:
        result["recommendation"] = "Save for later"
    elif "background" in rec:
        result["recommendation"] = "Background reference"
    else:
        result["recommendation"] = "Skip"

    return {
        "verdict": result.get("verdict", "Not a fit"),
        "why": result.get("why", ""),
        "tada_themes": result.get("tada_themes", ""),
        "angle": result.get("angle", "Expansion"),
        "post_direction": result.get("post_direction", ""),
        "what_to_avoid": result.get("what_to_avoid", ""),
        "recommendation": result.get("recommendation", "Skip"),
    }


def _default_validation() -> dict[str, Any]:
    return {
        "verdict": "Not a fit",
        "why": "Validation could not be completed.",
        "tada_themes": "",
        "angle": "",
        "post_direction": "",
        "what_to_avoid": "",
        "recommendation": "Skip",
    }


def is_strong_enough(linkedin_validation: dict) -> bool:
    """Return True if the article passes the LinkedIn quality bar."""
    verdict = linkedin_validation.get("verdict", "")
    rec = linkedin_validation.get("recommendation", "")
    # Only keep Strong fit or Good fit; reject Weak and Not a fit
    return verdict in ("Strong fit", "Good fit with refinement") and rec != "Skip"
