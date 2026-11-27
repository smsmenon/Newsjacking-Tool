"""
Contrarian POV Pipeline — 7 Stages

Stage 1: Source Whitelist Filter       — hard filter, no exceptions
Stage 2: LinkedIn Engagement Filter    — configurable thresholds
Stage 3: Theme Matching                — Llama (fast, cheap)
Stage 4: Contrarian Fit Scoring        — Claude API (needs real judgment)
Stage 5: POV Generation                — Claude API
Stage 6: Hater Bot Review              — Claude API
Stage 7: Structured Output             — final result per candidate
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ── Model routing ──────────────────────────────────────────────────────────────
_OLLAMA_URL  = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "llama3.1"
_CLAUDE_MODEL = "claude-sonnet-4-6"          # Stages 4, 5, 6
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _ollama(prompt: str, max_tokens: int = 300) -> str:
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


def _claude(prompt: str, max_tokens: int = 600, cached_prefix: str = "") -> str:
    """
    cached_prefix: static content (e.g. the reference docs) marked for Anthropic prompt
    caching — cuts cost ~90% on repeat calls within the ~5min cache TTL that reuse the exact
    same prefix text. Only worth using for content that's identical across several calls in
    the same run; the per-call dynamic part still goes in `prompt` uncached.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — required for Stages 4, 5, 6")
    if cached_prefix:
        content = [
            {"type": "text", "text": cached_prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": prompt},
        ]
    else:
        content = prompt
    payload = json.dumps({
        "model": _CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
    }).encode()
    req = urllib.request.Request(
        _ANTHROPIC_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
                data = json.loads(r.read())
            usage = data.get("usage", {})
            if usage.get("cache_read_input_tokens") or usage.get("cache_creation_input_tokens"):
                log.info(
                    "prompt cache: created=%s read=%s (input=%s output=%s)",
                    usage.get("cache_creation_input_tokens", 0),
                    usage.get("cache_read_input_tokens", 0),
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                )
            return data["content"][0]["text"].strip()
        except (urllib.error.URLError, TimeoutError) as exc:
            # ponytail: transient DNS/network flakiness, not a code bug — 3 attempts, short backoff
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def _parse_labeled(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip().upper()] = v.strip()
    return result


# ── Config loaders ─────────────────────────────────────────────────────────────

def _load_engagement_config(root: Path) -> dict:
    p = root / "config" / "engagement_config.json"
    if p.exists():
        return json.loads(p.read_text()).get("linkedin", {})
    return {"min_likes": 50, "min_comments": 10, "max_age_hours": 24}


def _load_reference_docs(root: Path) -> str:
    docs_dir = root / "config" / "reference_docs"
    if not docs_dir.exists():
        return ""
    texts = []
    for f in sorted(docs_dir.glob("*.txt")) + sorted(docs_dir.glob("*.md")):
        if f.name == "README.md":
            continue
        try:
            texts.append(f"--- {f.stem} ---\n{f.read_text()[:20000]}")
        except Exception:
            pass
    return "\n\n".join(texts)


def _load_whitelist(root: Path) -> tuple[set[str], set[str]]:
    """Returns (whitelisted_source_names, whitelisted_linkedin_usernames)."""
    p = root / "config" / "sources.json"
    sources = json.loads(p.read_text()) if p.exists() else []
    source_names = {s.get("name", "").lower() for s in sources if s.get("enabled", True)}

    lp = root / "config" / "linkedin_profiles.json"
    profiles = json.loads(lp.read_text()) if lp.exists() else []
    li_usernames = {pr.get("username", "").lower() for pr in profiles}

    return source_names, li_usernames


def _load_themes(root: Path) -> list[dict]:
    p = root / "config" / "themes.json"
    if not p.exists():
        return []
    return [t for t in json.loads(p.read_text()) if t.get("enabled", True)]


# ── Stage 1: Source Whitelist Filter ──────────────────────────────────────────

def _stage1_whitelist(articles: list[dict], source_names: set[str], li_usernames: set[str]) -> list[dict]:
    passed = []
    for a in articles:
        src = a.get("source", "").lower()
        origin = a.get("origin", "rss")   # "rss" or "linkedin"
        if origin == "linkedin":
            author = a.get("author", a.get("username", "")).lower()
            if author in li_usernames or src in li_usernames:
                passed.append(a)
        else:
            if any(src in name or name in src for name in source_names):
                passed.append(a)
    log.info("Stage 1 whitelist: %d → %d", len(articles), len(passed))
    return passed


# ── Stage 2: LinkedIn Engagement Filter ───────────────────────────────────────

def _stage2_engagement(articles: list[dict], config: dict) -> list[dict]:
    min_likes    = config.get("min_likes", 50)
    min_comments = config.get("min_comments", 10)
    max_age_h    = config.get("max_age_hours", 24)
    cutoff       = datetime.now(timezone.utc) - timedelta(hours=max_age_h)

    passed = []
    for a in articles:
        if a.get("origin", "rss") != "linkedin":
            passed.append(a)   # RSS articles skip this stage
            continue
        likes    = int(a.get("likes", 0) or 0)
        comments = int(a.get("comments", 0) or 0)
        pub_str  = a.get("published_at", "")
        # Age check
        too_old = False
        if pub_str:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                too_old = dt < cutoff
            except Exception:
                pass
        if likes >= min_likes and comments >= min_comments and not too_old:
            passed.append(a)
        else:
            log.debug("Stage 2 dropped LinkedIn post '%s' (likes=%d, comments=%d)", a.get("title","")[:60], likes, comments)
    log.info("Stage 2 engagement: %d → %d", len(articles), len(passed))
    return passed


# ── Stage 3: Theme Matching ────────────────────────────────────────────────────

def _stage3_theme_match(articles: list[dict], themes: list[dict]) -> list[dict]:
    if not themes:
        for a in articles:
            a["matched_theme"] = None
        return articles

    theme_block = "\n".join(
        f"THEME_{i+1}: {t['name']} — {t.get('description','')}"
        for i, t in enumerate(themes)
    )
    theme_names = [t["name"] for t in themes]

    passed = []
    for a in articles:
        snippet = f"{a.get('title','')} {a.get('content','')[:400]}"
        prompt = f"""Match this content to ONE of the themes below, or say NONE.

THEMES:
{theme_block}

CONTENT: {snippet}

Respond with:
MATCH: [exact theme name from the list, or NONE]
CONFIDENCE: [high / medium / low]"""

        try:
            # Previously always _ollama() with no fallback — on a machine with no local
            # Ollama server this made Stage 3 reject every article, so the whole 7-stage
            # pipeline always produced zero output regardless of any other stage's behavior.
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            raw = _claude(prompt, max_tokens=60) if api_key else _ollama(prompt, max_tokens=60)
            parsed = _parse_labeled(raw)
            match = parsed.get("MATCH", "NONE").strip()
            confidence = parsed.get("CONFIDENCE", "low").strip().lower()
            if match.upper() != "NONE" and any(match.lower() in tn.lower() or tn.lower() in match.lower() for tn in theme_names):
                a["matched_theme"] = match
                a["theme_confidence"] = confidence
                passed.append(a)
        except Exception as exc:
            log.debug("Stage 3 theme match error: %s", exc)

    log.info("Stage 3 theme match: %d → %d", len(articles), len(passed))
    return passed


# ── Stage 4: Contrarian Fit Scoring ───────────────────────────────────────────

def _stage4_contrarian_score(articles: list[dict], reference_docs: str) -> list[dict]:
    ref_block = f"\n\nREFERENCE MATERIAL:\n{reference_docs[:20000]}" if reference_docs else ""

    passed = []
    for a in articles:
        title   = a.get("title", "")
        content = a.get("content", "")[:800]
        theme   = a.get("matched_theme", "")

        prompt = f"""You are a strategic editorial director for TADA, a supply chain consultancy with strong contrarian views on enterprise technology, planning systems, and AI adoption.{ref_block}

ARTICLE:
Title: {title}
Theme: {theme}
Content: {content}

Does this article offer a strong opportunity for a CONTRARIAN take grounded in TADA's thinking?

A contrarian take must:
- Push back against the mainstream conclusion of the article
- Be grounded in real operational evidence, not just skepticism
- Challenge what executives are being told to do or buy

Respond with:
CONTRARIAN_FIT: [strong / weak / none]
REASON: [one sentence — what specifically can be challenged and why]"""

        try:
            raw = _claude(prompt, max_tokens=200)
            parsed = _parse_labeled(raw)
            fit    = parsed.get("CONTRARIAN_FIT", "none").lower()
            reason = parsed.get("REASON", "")
            if fit in ("strong", "weak"):
                a["contrarian_fit"]    = fit
                a["contrarian_reason"] = reason
                passed.append(a)
                log.info("Stage 4 [%s] '%s'", fit.upper(), title[:60])
        except Exception as exc:
            log.warning("Stage 4 error for '%s': %s", title[:60], exc)

    log.info("Stage 4 contrarian scoring: %d → %d", len(articles), len(passed))
    return passed


# ── Stage 5: POV Generation ────────────────────────────────────────────────────

def _stage5_pov(articles: list[dict], reference_docs: str) -> list[dict]:
    ref_block = f"\n\nTADA REFERENCE MATERIAL:\n{reference_docs[:20000]}" if reference_docs else ""

    for a in articles:
        title   = a.get("title", "")
        content = a.get("content", "")[:800]
        theme   = a.get("matched_theme", "")
        reason  = a.get("contrarian_reason", "")

        prompt = f"""You are writing for TADA, a supply chain consultancy that takes credible contrarian positions on enterprise technology and AI adoption.{ref_block}

ARTICLE:
Title: {title}
Theme: {theme}
Contrarian angle identified: {reason}
Content: {content}

Write TADA's POV on this article. This is NOT a summary. It is a specific, well-reasoned position that DISAGREES with or COMPLICATES the mainstream take in the article.

Rules:
- 3–4 sentences maximum
- Name the specific thing the article gets wrong or oversimplifies
- Ground the pushback in operational reality, not theory
- End with what supply chain leaders should actually do instead
- No hedging. No "however" and "on the other hand". Take a position.

Write the POV directly. No labels, no preamble."""

        try:
            pov = _claude(prompt, max_tokens=300)
            a["pov"] = pov
            log.info("Stage 5 POV generated for '%s'", title[:60])
        except Exception as exc:
            log.warning("Stage 5 POV error for '%s': %s", title[:60], exc)
            a["pov"] = ""

    return articles


# ── Stage 6: Hater Bot Review ─────────────────────────────────────────────────

def _stage6_hater_bot(articles: list[dict]) -> list[dict]:
    for a in articles:
        title = a.get("title", "")
        pov   = a.get("pov", "")
        if not pov:
            a["hater_bot"] = {"verdict": "SKIPPED", "notes": "No POV to review"}
            continue

        prompt = f"""You are a ruthless editorial critic stress-testing a supply chain consultancy's POV before it reaches a client.

ORIGINAL ARTICLE TITLE: {title}
POV TO REVIEW: {pov}

Your job: find every weakness. Flag it.

Check for:
1. Does the POV actually contradict the article, or just add nuance?
2. Is the reasoning generic enough to apply to ANY industry or company?
3. Are there specific claims that could be challenged or fact-checked?
4. Does it end with a concrete action or just vague advice?

Respond with:
VERDICT: [APPROVED / NEEDS REVISION / REJECTED]
NOTES: [2–3 specific, brutal observations — what's weak, what's missing, what's generic]"""

        try:
            raw = _claude(prompt, max_tokens=250)
            parsed = _parse_labeled(raw)
            verdict = parsed.get("VERDICT", "NEEDS REVISION")
            notes   = parsed.get("NOTES", "")
            a["hater_bot"] = {"verdict": verdict, "notes": notes}
            log.info("Stage 6 Hater Bot [%s] '%s'", verdict, title[:60])
        except Exception as exc:
            log.warning("Stage 6 hater bot error: %s", exc)
            a["hater_bot"] = {"verdict": "SKIPPED", "notes": f"Error: {exc}"}

    return articles


# ── Stage 7: Structured Output ────────────────────────────────────────────────

def _stage7_output(articles: list[dict]) -> list[dict]:
    results = []
    for a in articles:
        origin = a.get("origin", "rss")
        result = {
            "title":              a.get("title", ""),
            "url":                a.get("url", ""),
            "source":             a.get("source", ""),
            "origin":             origin,
            "published_at":       a.get("published_at", ""),
            "theme":              a.get("matched_theme", ""),
            "theme_confidence":   a.get("theme_confidence", ""),
            "contrarian_fit":     a.get("contrarian_fit", ""),
            "contrarian_reason":  a.get("contrarian_reason", ""),
            "pov":                a.get("pov", ""),
            "hater_bot":          a.get("hater_bot", {}),
        }
        if origin == "linkedin":
            result["engagement"] = {
                "likes":    a.get("likes", 0),
                "comments": a.get("comments", 0),
            }
        results.append(result)
    return results


# ── Standalone POV — works with Llama fallback ────────────────────────────────

def _reference_material_cache_block(reference_docs: str) -> str:
    """
    Exact same text every call in a run, by design — this is what makes generate_pov_for_article
    and check_source_criteria able to share one Anthropic prompt-cache entry (cache hits require
    an identical prefix) instead of each writing their own ~5K-token cache copy.
    """
    return f"TADA REFERENCE MATERIAL:\n{reference_docs[:20000]}" if reference_docs else ""


def generate_pov_for_article(article: dict, reference_docs: str = "") -> str:
    """
    Generate a TADA POV for a single article.
    Uses Claude if ANTHROPIC_API_KEY is set, falls back to Llama.
    """
    title   = article.get("title", "")
    content = article.get("content", "")[:1000]
    theme   = article.get("matched_themes", [""])[0] if article.get("matched_themes") else ""
    cached_prefix = _reference_material_cache_block(reference_docs)

    prompt = f"""You are a strategic analyst for TADA, a supply chain intelligence platform advising CSCOs and COOs at Fortune 500 companies.

ARTICLE:
Title: {title}
Theme: {theme}
Content: {content}

Write TADA's point of view on this article. This is NOT a summary.

Your POV must carry all three of these, compressed — not as separate sentences:
- what the article gets right
- the DEEPER problem it points to that most executives are missing (the contrarian core — this is the part that must survive)
- what a CSCO should actually do differently

HARD LIMIT: 2 sentences, under 45 words total. This goes in an executive email where
length kills readability, so cut every qualifier, throat-clearing phrase and restatement
of the headline — keep the sharp claim and the instruction. No hedging. No "however".
Take a clear position. Write the POV directly. No labels or preamble."""

    # Try Claude first, fall back to Llama
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        if api_key:
            return _claude(prompt, max_tokens=300, cached_prefix=cached_prefix)
        else:
            return _ollama(prompt, max_tokens=300)
    except Exception as exc:
        log.warning("generate_pov error: %s", exc)
        return ""


# ── Source selection gate — enforces the written criteria, not just prompt flavor ──

def check_source_criteria(article: dict, reference_docs: str) -> dict:
    """
    Apply the SOURCE SELECTION CRITERIA from the reference docs as an actual pass/fail gate,
    not just background context for the POV prompt. Returns {"pass": bool, "reason": str}.
    Fails open (pass=True) if the LLM call itself errors, so a network blip doesn't block
    every candidate — the point is to catch bad *articles*, not to become a new failure mode.
    """
    title = article.get("title", "")
    content = article.get("content", "")[:1500]
    if not content or len(content.strip()) < 200:
        return {"pass": False, "reason": "No real article content available to judge fit."}

    # Same helper/text as generate_pov_for_article's cached_prefix — identical prefix is what
    # lets a gate call and a POV call in the same run share one cached read.
    cached_prefix = _reference_material_cache_block(reference_docs)

    prompt = f"""You are gatekeeping content for TADA, a supply chain intelligence platform.

Apply ONLY the REJECT rules explicitly listed in the reference material's SOURCE SELECTION
CRITERIA to this candidate. Do not invent additional rules. In particular: the reference
material's "Prefer sources where the underlying claim comes from..." list explicitly names
enterprise-technology publications (and general business/analyst press) as acceptable —
do NOT reject an article solely because its outlet isn't a dedicated supply-chain trade
publication. Reject only if one of the listed REJECT conditions actually applies.

Two of the listed criteria are missed most often, so check them explicitly:

- STATUS UPDATE / RECAP: reject an earnings-call write-up, quarterly roundup, or "latest
  checkpoint on an ongoing saga" that mixes past problems, current numbers and a quote
  instead of making one argument. A new date on an old story is not a new opportunity.
- NO ARGUMENT TO ANSWER: reject product launches, funding and partnership announcements,
  award and event write-ups, and vendor-sponsored or unattributed marketing copy, however
  many real statistics they quote.

ARTICLE:
Title: {title}
Content: {content}

Then answer separately: does TADA have a SHARPER DIAGNOSIS than this article's central
claim? True when TADA would say the author has the right observation but the wrong layer,
cause or fix — that is the normal case and it counts. False when the article already reaches
TADA's own conclusion, so our POV would only restate the author in TADA's vocabulary (for
example, a piece whose own thesis is "the operating model is the problem, not the
technology"). If our reply would open by agreeing and add no different diagnosis, answer
false — an article we merely endorse is not a contrarian opportunity.

Respond with ONLY these labeled lines:
PASS: [true/false]
REASON: [one sentence citing the specific listed criterion that passed or failed]
CAN_CONTRADICT: [true/false]
CONTRADICTION: [one sentence naming what TADA disagrees with, or NONE]"""

    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        raw = _claude(prompt, max_tokens=150, cached_prefix=cached_prefix) if api_key else _ollama(prompt, max_tokens=150)
        parsed = _parse_labeled(raw)
        passed = parsed.get("PASS", "false").strip().lower() == "true"
        reason = parsed.get("REASON", "")
        # An article TADA merely agrees with produces a POV that restates the author — the
        # Cisco and Levi's picks both read that way. Treat it as a gate failure, not a note.
        can_contradict = parsed.get("CAN_CONTRADICT", "true").strip().lower() == "true"
        if passed and not can_contradict:
            return {
                "pass": False,
                "reason": "Nothing to argue with — TADA would agree with this article's claim, "
                          "so the POV would only restate it.",
                "contradiction": "NONE",
            }
        return {"pass": passed, "reason": reason,
                "contradiction": parsed.get("CONTRADICTION", "")}
    except Exception as exc:
        log.warning("check_source_criteria error: %s", exc)
        # Distinguishable from a real pass — "pass": true alone previously looked identical
        # to an article that actually cleared the criteria.
        return {"pass": True, "gate_error": True, "reason": f"Gate check unavailable ({exc}) — failed open."}


# ── Public entry point ─────────────────────────────────────────────────────────

def run_contrarian_pipeline(root: Any = None, raw_articles: list[dict] | None = None) -> dict:
    """
    Run the full 7-stage contrarian POV pipeline.

    Parameters
    ----------
    root : Path-like project root
    raw_articles : pre-fetched articles (dicts). If None, loads from existing digest.

    Returns
    -------
    dict with keys: results, usage_stats, run_metadata
    """
    from pathlib import Path as _Path
    start = time.time()

    if root is None:
        root = _Path(__file__).resolve().parents[3]
    root = _Path(root)

    # Load configs
    engagement_cfg  = _load_engagement_config(root)
    reference_docs  = _load_reference_docs(root)
    source_names, li_usernames = _load_whitelist(root)
    themes          = _load_themes(root)

    # Load articles from existing digest if not provided
    if raw_articles is None:
        digest_path = root / "work" / "daily_digest.json"
        if digest_path.exists():
            digest = json.loads(digest_path.read_text())
            raw_articles = digest.get("signals", digest.get("articles", []))
        else:
            raw_articles = []

    stats = {"input": len(raw_articles)}

    # ── Stage 1 ──
    s1 = _stage1_whitelist(raw_articles, source_names, li_usernames)
    stats["after_stage1_whitelist"] = len(s1)

    # ── Stage 2 ──
    s2 = _stage2_engagement(s1, engagement_cfg)
    stats["after_stage2_engagement"] = len(s2)

    # ── Stage 3 ──
    s3 = _stage3_theme_match(s2, themes)
    stats["after_stage3_theme_match"] = len(s3)

    # ── Stage 4 ──
    s4 = _stage4_contrarian_score(s3, reference_docs)
    stats["after_stage4_contrarian"] = len(s4)

    # ── Stage 5 ──
    s5 = _stage5_pov(s4, reference_docs)

    # ── Stage 6 ──
    s6 = _stage6_hater_bot(s5)

    # ── Stage 7 ──
    results = _stage7_output(s6)

    stats["final_candidates"] = len(results)
    stats["run_duration_seconds"] = round(time.time() - start, 2)
    stats["reference_docs_loaded"] = bool(reference_docs)
    stats["claude_stages"] = "4, 5, 6"
    stats["llama_stages"] = "3"

    return {
        "results": results,
        "usage_stats": stats,
        "run_metadata": {
            "run_date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "themes_active": [t["name"] for t in themes],
            "engagement_config": engagement_cfg,
            "sources_whitelisted": len(source_names),
            "linkedin_profiles_whitelisted": len(li_usernames),
        },
    }
