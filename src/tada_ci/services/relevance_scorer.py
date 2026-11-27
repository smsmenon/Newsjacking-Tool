from __future__ import annotations
import json
import logging
import os
import re
import ssl
import urllib.request

log = logging.getLogger(__name__)

_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "llama3.1"
_CLAUDE_MODEL = "claude-haiku-4-5-20251001"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _llm(prompt: str, max_tokens: int = 200) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        payload = json.dumps({
            "model": _CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            _ANTHROPIC_URL, data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
            data = json.loads(r.read())
            return data["content"][0]["text"].strip()
    # Fallback to Llama
    payload = json.dumps({
        "model": _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3},
    }).encode()
    req = urllib.request.Request(
        _OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["response"].strip()


def _parse_labeled(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip().upper()] = v.strip()
    return result


def score_article_against_themes(title: str, content: str, themes: list[dict]) -> dict:
    theme_list = "\n".join(
        f"- {t['name']}: {t.get('description', '')}" for t in themes
    )
    snippet = (content or title)[:1200]

    prompt = f"""You are a content relevance analyst for TADA, a supply chain intelligence platform.
TADA's audience: CSCOs, COOs, and VP-level executives in Supply Chain, Logistics, and Operations at Fortune 500 manufacturing and distribution companies.

TADA's focus is exclusively on: supply chain disruption, planning failures, ERP and technology limitations in operations, AI that doesn't work in practice, procurement risk, inventory volatility, and logistics breakdowns.

ACTIVE THEMES:
{theme_list}

ARTICLE:
Title: {title}
Content: {snippet}

Score this article strictly. Use ONLY these labeled lines:
SCORE: [0.0-10.0]
THEMES: [comma-separated matching theme names, or "none"]
AUDIENCE: [executive / operational / tactical]
REASONING: [one sentence why]
RECOMMENDATION: [include / exclude]

The single test for every article: would a CSCO at a Fortune 500 manufacturer read this and change a decision TODAY?

Scoring guide:
- 8-10: Directly actionable for a CSCO — operational failures, planning breakdowns, technology gaps, supplier risk, AI not delivering, real decisions being made wrong
- 5-7: Useful context but no immediate decision impact
- 0-4: Academic, theoretical, design-phase, consumer, tech product releases, or anything a CSCO would not act on this week

HARD EXCLUSION RULES — score 0 and exclude if ANY apply:
- Article is about product design, R&D, or upstream innovation (not operational)
- Article is about a software/AI model release with no direct supply chain operations use case
- Article is about consumer technology, cybersecurity tools, or developer tools
- Article mentions supply chain only as a passing reference, not as the core subject
- Article is opinion/thought leadership with no specific data, event, or operational finding
- If AUDIENCE is operational or tactical, exclude regardless of score
- Only recommend include if SCORE >= 6.0 AND AUDIENCE is executive AND a specific theme matched"""

    fallback = {
        "score": 5.0,
        "matched_themes": [],
        "reasoning": "Could not score — Ollama unavailable",
        "audience_fit": "executive",
        "recommendation": "exclude",
    }

    try:
        raw = _llm(prompt, max_tokens=200)
        parsed = _parse_labeled(raw)

        # The model occasionally echoes the prompt's own placeholder ("[0.0-10.0]") instead of
        # a real number — extract the first numeric substring rather than crashing into the
        # generic "Ollama unavailable" fallback for what's actually just a formatting slip.
        score_raw = parsed.get("SCORE", "5.0")
        score_match = re.search(r"\d+(?:\.\d+)?", score_raw)
        score = float(score_match.group()) if score_match else 5.0
        themes_raw = parsed.get("THEMES", "none")
        matched = [
            t.strip()
            for t in themes_raw.split(",")
            if t.strip() and t.strip().lower() != "none"
        ]
        audience = parsed.get("AUDIENCE", "operational").lower()
        reasoning = parsed.get("REASONING", "")
        rec = parsed.get("RECOMMENDATION", "exclude").lower()

        if audience in ("operational", "tactical"):
            rec = "exclude"

        return {
            "score": round(min(10.0, max(0.0, score)), 1),
            "matched_themes": matched,
            "reasoning": reasoning,
            "audience_fit": audience,
            "recommendation": rec,
        }
    except Exception as exc:
        log.warning("relevance_scorer: %s", exc)
        return fallback
