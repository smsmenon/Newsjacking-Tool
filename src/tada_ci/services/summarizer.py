from __future__ import annotations
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "llama3.1"
_CLAUDE_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _urlopen_with_retry(req: urllib.request.Request, timeout: int):
    # ponytail: transient DNS/network flakiness, not a code bug — 3 attempts, short backoff
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def _llm(prompt: str, max_tokens: int = 400, temperature: float = 0.4) -> str:
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
        with _urlopen_with_retry(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["content"][0]["text"].strip()
    # Fallback to Llama
    payload = json.dumps({
        "model": _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }).encode()
    req = urllib.request.Request(
        _OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["response"].strip()


def summarize_article(title: str, content: str, source: str = "") -> list[str]:
    if not content or len(content.strip()) < 200:
        return ["Full article content not accessible — summary not available"]

    # ── Step 1: Writer Bot — find the hidden drama and force the So What ──
    writer_prompt = f"""You are a sharp supply chain intelligence analyst writing for CSCOs and COOs at Fortune 500 companies.

Your job is NOT to summarize. Your job is to find:
- The hidden drama: what is breaking, failing, or about to snap?
- The weird glitch: what is happening that shouldn't be? What does the data reveal that no one is saying out loud?
- The big problem: what does this mean for companies that are not paying attention?

Article title: {title}
Source: {source}
Content: {content[:2000]}

Write exactly 3 insights. Each insight MUST follow this structure:
INSIGHT: [What is happening — be specific, name numbers, companies, or systems if present]
CAUSE: [The hidden reason WHY this is happening — not the obvious answer]
ACTION: [What a supply chain leader must do or stop doing because of this]

Rules:
- No vague language ("experts say", "companies are facing", "it is important to")
- No rephrasing the headline
- If it is boring news, find the uncomfortable implication
- Write 3 blocks of INSIGHT / CAUSE / ACTION only. Nothing else."""

    raw = ""
    try:
        raw = _llm(writer_prompt, max_tokens=250, temperature=0.5)
        bullets = _parse_insights(raw)
        if len(bullets) >= 2:
            return bullets
    except Exception as exc:
        log.warning("summarizer writer: %s", exc)

    # Fallback if parsing fails or the call errored (raw stays "" in that case)
    lines = [l.strip().lstrip("-•* ") for l in raw.splitlines() if len(l.strip()) > 30]
    return lines[:5] if lines else ["Full article content not accessible — summary not available"]


def _parse_insights(raw: str) -> list[str]:
    """Parse INSIGHT/CAUSE/ACTION blocks into combined bullet strings."""
    bullets = []
    current: dict[str, str] = {}

    for line in raw.splitlines():
        line = line.strip()
        upper = line.upper()
        if upper.startswith("INSIGHT:"):
            if current.get("insight"):
                bullets.append(_format_insight(current))
                current = {}
            current["insight"] = line.split(":", 1)[1].strip()
        elif upper.startswith("CAUSE:"):
            current["cause"] = line.split(":", 1)[1].strip()
        elif upper.startswith("ACTION:"):
            current["action"] = line.split(":", 1)[1].strip()

    if current.get("insight"):
        bullets.append(_format_insight(current))

    return bullets


def _format_insight(parts: dict) -> str:
    insight = parts.get("insight", "")
    cause = parts.get("cause", "")
    action = parts.get("action", "")
    result = insight
    if cause:
        result += f" - {cause}"
    if action:
        result += f" -> {action}"
    return result


def run_hater_bot(summary_text: str, title: str) -> dict:
    """
    Hater Bot: a critic AI that reviews the summary before it goes in the email.
    Returns {"approved": bool, "verdict": str, "reason": str}
    """
    prompt = f"""You are a ruthless editorial critic for a supply chain intelligence newsletter read by CSCOs and COOs.

Your only job is to REJECT content that is:
- Generic (could apply to any industry, any year)
- Boring (no tension, no stakes, no urgency)
- Vague (no specific numbers, companies, or consequences named)
- Just a headline rewrite
- Corporate fluff with no real insight

Article title: {title}
Summary to review:
{summary_text}

Respond with ONLY these labeled lines:
VERDICT: [APPROVED / REJECTED]
REASON: [one sentence — be brutally specific about what is wrong, or why it passes]"""

    try:
        raw = _llm(prompt, max_tokens=120, temperature=0.3)
        verdict = "APPROVED"
        reason = ""
        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip().upper()
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        approved = "APPROVED" in verdict
        return {"approved": approved, "verdict": verdict, "reason": reason}
    except Exception as exc:
        log.warning("hater_bot error: %s", exc)
        return {"approved": True, "verdict": "APPROVED", "reason": "Hater bot unavailable"}
