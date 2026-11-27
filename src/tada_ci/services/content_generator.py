from __future__ import annotations

import json
import os
import ssl
import urllib.request
import urllib.error
from typing import Any

_OLLAMA_URL = "http://localhost:11434/api/generate"
_MODEL = "llama3.1"
_CLAUDE_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_TADA_CONTEXT = """
TADA is a supply chain intelligence platform.
It helps supply chain, procurement, manufacturing and operations leaders detect market signals early, decide on the best response, and execute faster — using the "Detect → Decide → Do" framework.
TADA's target audience: VPs and Directors of Supply Chain, Procurement, Operations, and Manufacturing at mid-to-large enterprises.
TADA's value proposition: Turn market signals into decisions and actions — not just reports.
"""


def _ollama(prompt: str, max_tokens: int = 400) -> str:
    """Claude if ANTHROPIC_API_KEY is set, else local Ollama — previously this called Ollama
    unconditionally with no fallback, so it silently returned canned fallback text on any
    machine without a local Ollama server running."""
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
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
            return json.loads(r.read())["content"][0]["text"].strip()
    payload = json.dumps({
        "model": _MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.7},
    }).encode()

    req = urllib.request.Request(
        _OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["response"].strip()


def generate_content_idea(
    headline: str,
    summary: str,
    source: str,
    signal_type: str,
) -> dict[str, str]:
    """
    Ask Llama to write a single-paragraph content idea for TADA to post on LinkedIn.
    Plain text — no parsing complexity.
    """
    prompt = f"""You are a B2B content strategist for TADA, a supply chain intelligence platform.
TADA's audience: VP and Director level leaders in Supply Chain, Procurement, and Operations at large enterprises.
TADA's value: helps teams detect market signals early, decide on the best response, and act faster.

An article was published:
Headline: {headline}
Summary: {summary[:300]}

In 3-4 sentences, describe a specific LinkedIn post or carousel that TADA should create based on this topic.
- Start with the format (post/carousel/poll)
- Give a punchy opening hook for the post
- Describe the key angle and what points to cover
- Do NOT just summarize the article. Create an original content angle.

Write only the content idea. No intro, no labels, no extra text."""

    try:
        raw = _ollama(prompt, max_tokens=300).strip()
        # Clean up any leading labels Llama might add anyway
        for prefix in ("Content Idea:", "LinkedIn Post:", "Post:", "Idea:"):
            if raw.lower().startswith(prefix.lower()):
                raw = raw[len(prefix):].strip()
        if len(raw) > 60:
            return {"idea": raw}
    except Exception:
        pass

    # Fallback
    return {
        "idea": f"LinkedIn post — {headline}. Use this signal to show how supply chain leaders can move from detecting a market shift to executing a response, using TADA's Detect → Decide → Do framework."
    }


def generate_one_line_summary(headline: str, summary: str) -> str:
    """Generate a crisp one-line summary of what the article is about."""
    prompt = f"""Summarize this article in ONE sentence (max 20 words). Be factual and specific. No fluff.

Headline: {headline}
Summary: {summary[:400]}

Output only the one-sentence summary. Nothing else."""

    try:
        result = _ollama(prompt, max_tokens=60)
        # Take first sentence only
        result = result.strip().split("\n")[0]
        for sep in [".", "!", "?"]:
            idx = result.find(sep)
            if idx > 10:
                return result[:idx + 1].strip()
        return result[:150].strip()
    except Exception:
        # Fallback: first sentence of summary
        for sep in [".", "!", "?"]:
            idx = summary.find(sep)
            if idx > 20:
                return summary[:idx + 1].strip()
        return summary[:140].strip() + "..."


def _enrich_one(item: dict) -> dict:
    sig = item.get("signal", {})
    headline = sig.get("headline", "")
    summary = sig.get("summary", "") or sig.get("evidence", "")
    source = sig.get("source", "")
    signal_type = sig.get("signal_type", "Industry Trend")
    item = dict(item)
    item["content_idea"] = generate_content_idea(headline, summary, source, signal_type)
    item["one_line_summary"] = generate_one_line_summary(headline, summary)
    return item


def enrich_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run Llama in parallel threads — all 3 articles at once, 30s max."""
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

    top3 = signals[:3]
    rest = signals[3:]
    enriched_map: dict[int, dict] = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_enrich_one, item): i for i, item in enumerate(top3)}
        for future in as_completed(futures, timeout=35):
            idx = futures[future]
            try:
                enriched_map[idx] = future.result(timeout=35)
            except Exception:
                enriched_map[idx] = top3[idx]  # fallback to original

    enriched = [enriched_map.get(i, top3[i]) for i in range(len(top3))]
    return enriched + rest
