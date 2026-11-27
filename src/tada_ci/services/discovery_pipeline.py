"""
Full V1 discovery pipeline:
1. Fetch all RSS + LinkedIn articles
2. Filter by time window (24h or 72h on Monday)
3. Score each article against active themes using LLM (parallel, 5 workers)
4. Filter: keep only score >= 6.0, executive audience, recommendation == include
5. Deduplicate
6. Sort by score descending, take top 10
7. Fetch full article content for top 10
8. Summarize top 3
9. Track stats
Returns dict with top_articles, usage_stats, run_metadata
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional service imports — each wrapped in try/except so the pipeline
# degrades gracefully if a module is not yet wired up.
# ---------------------------------------------------------------------------

try:
    from .rss_fetcher import fetch_live_articles
except Exception:
    fetch_live_articles = None  # type: ignore[assignment]

try:
    from .linkedin_fetcher import fetch_linkedin_posts
except Exception:
    fetch_linkedin_posts = None  # type: ignore[assignment]

try:
    from .theme_manager import load_themes
except Exception:
    load_themes = None  # type: ignore[assignment]

try:
    from .time_filter import filter_fresh_articles, get_cutoff_datetime, is_article_fresh
except Exception:
    filter_fresh_articles = None  # type: ignore[assignment]
    get_cutoff_datetime = None  # type: ignore[assignment]
    is_article_fresh = None  # type: ignore[assignment]

try:
    from .relevance_scorer import score_article_against_themes
except Exception:
    score_article_against_themes = None  # type: ignore[assignment]

try:
    from .deduplicator import deduplicate_articles
except Exception:
    deduplicate_articles = None  # type: ignore[assignment]

try:
    from .summarizer import summarize_article, run_hater_bot
except Exception:
    summarize_article = None  # type: ignore[assignment]
    run_hater_bot = None  # type: ignore[assignment]

try:
    from .article_scraper import fetch_article_content, extract_published_date
except Exception:
    fetch_article_content = None  # type: ignore[assignment]
    extract_published_date = None  # type: ignore[assignment]

try:
    from .linkedin_validator import validate_for_linkedin
except Exception:
    validate_for_linkedin = None  # type: ignore[assignment]

try:
    from .contrarian_pipeline import generate_pov_for_article, check_source_criteria
except Exception:
    generate_pov_for_article = None  # type: ignore[assignment]
    check_source_criteria = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SENT_CACHE_NAME = "emailed_urls.json"
_SENT_RETENTION_DAYS = 60


def _sent_cache_path(root: Any):
    from pathlib import Path as _Path

    return _Path(root) / "data" / _SENT_CACHE_NAME


def load_sent_urls(root: Any) -> dict:
    """URL -> ISO date it went out in a digest, so the same link is never emailed twice."""
    try:
        import json as _json

        p = _sent_cache_path(root)
        return _json.loads(p.read_text()) if p.exists() else {}
    except Exception as exc:
        log.debug("could not read sent-url cache: %s", exc)
        return {}


def record_sent_urls(root: Any, urls: list) -> None:
    """Remember URLs that were actually emailed. Call only after a successful send."""
    urls = [u for u in urls if u]
    if not urls:
        return
    try:
        import json as _json

        today = datetime.now(timezone.utc)
        merged = load_sent_urls(root)
        merged.update({u: today.isoformat() for u in urls})

        # Keep the file from growing without bound; anything older than the retention
        # window is long past being re-surfaced by a freshness filter measured in hours.
        cutoff = today - timedelta(days=_SENT_RETENTION_DAYS)
        kept = {}
        for url, sent_at in merged.items():
            try:
                if datetime.fromisoformat(sent_at) >= cutoff:
                    kept[url] = sent_at
            except Exception:
                kept[url] = sent_at

        p = _sent_cache_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_json.dumps(kept, indent=2, sort_keys=True))
    except Exception as exc:
        log.debug("could not write sent-url cache: %s", exc)


_STALE_CACHE_NAME = "known_stale_urls.json"


def _stale_cache_path(root: Any):
    from pathlib import Path as _Path

    return _Path(root) / "data" / _STALE_CACHE_NAME


def _load_stale_urls(root: Any) -> dict:
    """URL -> real publish date, for articles a previous run proved were outside the window."""
    try:
        import json as _json

        p = _stale_cache_path(root)
        return _json.loads(p.read_text()) if p.exists() else {}
    except Exception as exc:
        log.debug("could not read stale-url cache: %s", exc)
        return {}


def _record_stale_urls(root: Any, newly_stale: dict) -> None:
    if not newly_stale:
        return
    try:
        import json as _json

        p = _stale_cache_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        merged = _load_stale_urls(root)
        merged.update(newly_stale)
        p.write_text(_json.dumps(merged, indent=2, sort_keys=True))
    except Exception as exc:
        log.debug("could not write stale-url cache: %s", exc)


def _has_real_content(article: dict) -> bool:
    """True when we actually fetched article body text, not just the title-shaped stub.

    Scraped candidates start with a placeholder body ("Article from <source>: <title>"), and
    fetch_article_content leaves that untouched when the page is unreachable or the extracted
    text fails its quality check.
    """
    content = (article.get("content") or "").strip()
    if len(content) < 300:
        return False
    return not content.startswith("Article from ")


def _article_to_dict(article: Any) -> dict:
    """Normalise an Article dataclass or dict into the pipeline dict shape."""
    if isinstance(article, dict):
        return article

    # Article dataclass — map known fields
    pub = getattr(article, "publication_date", None) or getattr(article, "published_at", None) or ""
    return {
        "title": getattr(article, "title", ""),
        "url": getattr(article, "url", ""),
        "source": getattr(article, "source", ""),
        "published_at": pub,
        "content": getattr(article, "full_text", "") or "",
        "relevance_score": 0.0,
        "matched_themes": [],
        "reasoning": "",
        "audience_fit": "",
        "recommendation": "",
        "summary_bullets": [],
        "trust_tier": getattr(article, "category", "unknown"),
        "why_it_matters": "",
    }


def _why_it_matters(matched_themes: list[str]) -> str:
    if not matched_themes:
        return (
            "Relevant to TADA's supply chain intelligence focus — "
            "signals a shift that supply chain leaders should track."
        )
    theme_name = matched_themes[0]
    return (
        f"Relevant to TADA's focus on {theme_name} — "
        "signals a shift that supply chain leaders should track."
    )


def _fallback_score(article_dict: dict, themes: list[dict]) -> dict:
    """
    Simple keyword-based scoring used when relevance_scorer is unavailable.
    Returns a score dict compatible with the pipeline shape.
    """
    import re

    text = f"{article_dict.get('title', '')} {article_dict.get('content', '')}".lower()
    matched = []
    for theme in themes:
        name = theme.get("name", "")
        desc = theme.get("description", "")
        keywords = re.findall(r"\w+", (name + " " + desc).lower())
        hits = sum(1 for kw in keywords if len(kw) > 3 and kw in text)
        if hits >= 2:
            matched.append(name)

    score = min(10.0, 4.0 + len(matched) * 1.5)
    audience_fit = "executive" if any(
        w in text for w in ("ceo", "coo", "cso", "vp", "leader", "executive", "board", "strategy")
    ) else "general"
    recommendation = "include" if score >= 6.0 and audience_fit == "executive" else "exclude"

    return {
        "relevance_score": round(score, 1),
        "matched_themes": matched,
        "reasoning": f"Keyword match on {len(matched)} theme(s).",
        "audience_fit": audience_fit,
        "recommendation": recommendation,
    }


def _score_one(article_dict: dict, themes: list[dict]) -> dict:
    """Score a single article dict; returns the enriched dict."""
    try:
        if score_article_against_themes is not None:
            # Previously called as score_article_against_themes(article_dict, themes) — wrong
            # arity (the real signature is (title, content, themes)), which raised a TypeError
            # on every single call, silently caught below, meaning the real Claude scorer has
            # never actually run through this pipeline — every run fell back to the crude
            # keyword-count heuristic instead (visible in the telltale reasoning text
            # "Keyword match on N theme(s)." that showed up in every prior run's output).
            result = score_article_against_themes(
                article_dict.get("title", ""), article_dict.get("content", ""), themes
            )
            # relevance_scorer returns the score under "score"; the rest of this pipeline
            # (the passing filter, etc.) reads "relevance_score" — normalize here so a real
            # score doesn't silently disappear under the wrong key.
            result = dict(result)
            result["relevance_score"] = result.pop("score", 0.0)
            article_dict.update(result)
        else:
            article_dict.update(_fallback_score(article_dict, themes))
    except Exception as exc:
        log.debug("Scoring error for %s: %s", article_dict.get("url"), exc)
        article_dict.update(_fallback_score(article_dict, themes))

    article_dict["why_it_matters"] = _why_it_matters(article_dict.get("matched_themes", []))
    return article_dict


def _fallback_summarize(article_dict: dict) -> list[str]:
    """Return 3 short bullet points extracted from the article content."""
    content = article_dict.get("content", "") or article_dict.get("title", "")
    sentences = [s.strip() for s in content.replace("\n", ". ").split(".") if len(s.strip()) > 30]
    bullets = sentences[:3]
    if not bullets:
        bullets = [article_dict.get("title", "No summary available.")]
    return bullets


def _deduplicate(articles: list[dict]) -> list[dict]:
    """URL-based deduplication fallback."""
    seen: set[str] = set()
    out: list[dict] = []
    for a in articles:
        url = a.get("url", "")
        if url not in seen:
            seen.add(url)
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# Public pipeline entry point
# ---------------------------------------------------------------------------

def run_discovery_pipeline(root: Any = None, sources: list[dict] | None = None, hours_window: int | None = None) -> dict:
    """
    Execute the full V1 discovery pipeline.

    Parameters
    ----------
    root:
        Path-like project root, passed to load_themes(root) and source loaders.
    sources:
        Optional list of source dicts (RSS sources). If None, the pipeline
        attempts to load them from root/config/sources.json.
    hours_window:
        Optional override for the freshness window in hours. If None, defaults to
        48 on Mondays (to cover the weekend) and 24 otherwise.

    Returns
    -------
    dict with keys: top_articles, usage_stats, run_metadata
    """
    start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    llm_calls_made = 0

    # ------------------------------------------------------------------
    # 0. Resolve project root
    # ------------------------------------------------------------------
    if root is None:
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]

    # ------------------------------------------------------------------
    # 1. Load themes
    # ------------------------------------------------------------------
    themes: list[dict] = []
    if load_themes is not None:
        try:
            themes = load_themes(root)
        except Exception as exc:
            log.warning("load_themes failed: %s", exc)
    active_theme_names = [t.get("name", "") for t in themes]

    # ------------------------------------------------------------------
    # 2. Load sources if not provided
    # ------------------------------------------------------------------
    if sources is None:
        try:
            import json
            from pathlib import Path
            src_path = Path(root) / "config" / "sources.json"
            sources = json.loads(src_path.read_text()) if src_path.exists() else []
        except Exception:
            sources = []

    # ------------------------------------------------------------------
    # 3. Fetch RSS articles
    # ------------------------------------------------------------------
    rss_articles: list[Any] = []
    rss_errors: list[dict] = []
    sources_used: list[str] = []

    if fetch_live_articles is not None and sources:
        try:
            rss_articles, rss_errors = fetch_live_articles(sources)
            sources_used.extend(
                s.get("name", "") for s in sources if s.get("rss_url")
            )
        except Exception as exc:
            log.warning("fetch_live_articles failed: %s", exc)
            rss_errors.append({"source": "RSS", "error": str(exc)})

    # ------------------------------------------------------------------
    # 4. LinkedIn is not used as a source — RSS only
    # ------------------------------------------------------------------
    all_raw = rss_articles
    articles_fetched = len(all_raw)

    # Per-source funnel. A source that contributes nothing is invisible in the run log — it
    # looks identical whether it published nothing, was blocked, or had every body fetch
    # fail. Counting each stage separates those, which matters because the pipeline now runs
    # from GitHub's datacenter IPs rather than a home connection.
    source_funnel: dict[str, dict[str, int]] = {}

    def _tally(stage: str, items: list) -> None:
        for item in items:
            name = (getattr(item, "source", None)
                    or (item.get("source") if isinstance(item, dict) else None) or "?")
            source_funnel.setdefault(name, {})[stage] = \
                source_funnel.setdefault(name, {}).get(stage, 0) + 1

    _tally("fetched", all_raw)

    # ------------------------------------------------------------------
    # 5. Normalise to dicts
    # ------------------------------------------------------------------
    articles: list[dict] = [_article_to_dict(a) for a in all_raw]

    # ------------------------------------------------------------------
    # 6. Time filter
    # ------------------------------------------------------------------
    if hours_window is None:
        hours_window = 48 if now_utc.weekday() == 0 else 24

    if filter_fresh_articles is not None:
        try:
            articles = [_article_to_dict(a) if not isinstance(a, dict) else a
                        for a in filter_fresh_articles(articles, hours_window)]
        except Exception as exc:
            log.warning("filter_fresh_articles failed: %s", exc)
    else:
        # Inline fallback: filter by published_at
        from datetime import timedelta
        cutoff = now_utc - timedelta(hours=hours_window)
        from email.utils import parsedate_to_datetime

        def _is_fresh(pub_str: str) -> bool:
            if not pub_str:
                return True
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(pub_str.strip(), fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt >= cutoff
                except ValueError:
                    pass
            try:
                dt = parsedate_to_datetime(pub_str)
                return dt >= cutoff
            except Exception:
                return True

        articles = [a for a in articles if _is_fresh(a.get("published_at", ""))]

    # ------------------------------------------------------------------
    # 6a. Drop URLs already proven stale on a previous run.
    # Scraped listing pages carry no date, so a pinned/"Top Story" link (confirmed: a
    # Logistics Management piece byline-dated Aug 25 living in the site's nav dropdown)
    # passes the freshness filter on every run, gets scored, and is only unmasked at step
    # 11a once its real byline date is read — burning LLM calls each time to reach the same
    # verdict. Once proven out-of-window, remember it and skip it up front.
    # ------------------------------------------------------------------
    stale_urls = _load_stale_urls(root)
    if stale_urls:
        before = len(articles)
        articles = [a for a in articles if a.get("url") not in stale_urls]
        if before != len(articles):
            log.info("Skipped %d URL(s) already known to be outside the window", before - len(articles))

    # Windows hand off cleanly between runs (Monday's 72h starts where Friday's ended), but a
    # story can still reappear: outlets re-date pieces, and a manual re-run covers ground an
    # automated one already sent. Drop anything already emailed before it costs LLM calls.
    sent_urls = load_sent_urls(root)
    if sent_urls:
        before = len(articles)
        articles = [a for a in articles if a.get("url") not in sent_urls]
        if before != len(articles):
            log.info("Skipped %d URL(s) already sent in a previous digest", before - len(articles))

    articles_after_time_filter = len(articles)
    _tally("fresh", articles)

    # ------------------------------------------------------------------
    # 6b. Keyword pre-filter — discard obvious non-supply-chain before LLM
    # ------------------------------------------------------------------
    _SC_KEYWORDS = {
        "supply chain", "logistics", "procurement", "inventory", "warehouse",
        "freight", "shipping", "sourcing", "supplier", "distribution",
        "manufacturing", "operations", "demand planning", "s&op", "erp",
        "tariff", "disruption", "resilience", "nearshoring", "reshoring",
        "last mile", "3pl", "4pl", "fulfilment", "fulfillment", "customs",
        "trade", "import", "export", "port", "intermodal", "cold chain",
    }
    _HARD_EXCLUDE = {
        "coding", "developer", "github copilot", "cursor ai", "zcode",
        "gaming", "healthcare drug", "cryptocurrency", "real estate",
        "dating app", "social media", "streaming", "music", "movie",
    }

    # Paid placements ride in on the same RSS feeds as editorial and read like real analysis
    # — Supply Chain Dive's "/spons/" advertorial scored 6.2 and was selected. The reference
    # doc rejects vendor promotion outright, and the gate cannot always tell from prose alone.
    _PROMO_URL_MARKERS = (
        "/spons/", "/sponsored", "/partner-content", "/advertorial",
        "/whitepaper", "/webinar", "/press-release",
    )

    def _keyword_prefilter(a: dict) -> bool:
        url = (a.get("url") or "").lower()
        if any(marker in url for marker in _PROMO_URL_MARKERS):
            return False
        text = (a.get("title", "") + " " + a.get("content", "")[:400]).lower()
        if any(ex in text for ex in _HARD_EXCLUDE):
            return False
        return any(kw in text for kw in _SC_KEYWORDS)

    pre_filtered = [a for a in articles if _keyword_prefilter(a)]
    log.info("Keyword pre-filter: %d → %d", len(articles), len(pre_filtered))
    articles = pre_filtered
    _tally("on_topic", articles)

    # ------------------------------------------------------------------
    # 6c. Fetch real article text BEFORE scoring.
    # Scoring used to run on the title plus whatever blurb the feed carried, because full
    # text was only fetched later for the top 10. Judged on a headline alone, genuine
    # reporting scored 2.0-4.2 while contentless hub pages ("Procurement Magazine") scored a
    # neutral 5.0 — there was nothing in them to mark down — so junk out-ranked journalism
    # and almost nothing ever cleared the 6.0 bar. Fetch first, then score on the real thing,
    # and drop candidates that turn out to have no readable body at all.
    # ------------------------------------------------------------------
    if fetch_article_content is not None and articles:
        # Feeds that syndicate <content:encoded> already carry the whole article, so there is
        # nothing to gain from re-fetching the page — and for publishers who block automated
        # requests (SCMR serves a Cloudflare challenge) the scrape only fails slowly after
        # retries, then falls back to this same text.
        needs_fetch = [a for a in articles if a.get("url") and not _has_real_content(a)]
        if len(needs_fetch) < len(articles):
            log.info("Full text already in feed for %d/%d articles — skipping their fetch",
                     len(articles) - len(needs_fetch), len(articles))
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_article_content, a["url"]): a for a in needs_fetch}
            for future in as_completed(futures):
                article = futures[future]
                try:
                    scraped = future.result()
                    if scraped:
                        article["content"] = scraped
                except Exception as exc:
                    log.debug("pre-score fetch failed for %s: %s", article.get("url"), exc)

        with_content = [a for a in articles if _has_real_content(a)]
        log.info("Full-text fetch: %d → %d with readable content", len(articles), len(with_content))
        # If every fetch failed (site-wide block, network out), keep going on blurbs rather
        # than throwing the whole run away.
        if with_content:
            articles = with_content
    _tally("body_read", articles)

    # ------------------------------------------------------------------
    # 7. Score articles in parallel (10 workers)
    # ------------------------------------------------------------------
    scored: list[dict] = []
    if articles:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_score_one, a, themes): a for a in articles}
            for future in as_completed(futures):
                try:
                    scored.append(future.result())
                    llm_calls_made += 1
                except Exception as exc:
                    log.debug("Scoring worker error: %s", exc)

    # ------------------------------------------------------------------
    # 8. Filter: score >= 6.0, executive audience, recommendation == include
    # ------------------------------------------------------------------
    passing = [
        a for a in scored
        if (
            a.get("relevance_score", 0.0) >= 6.0
            and a.get("audience_fit", "").lower() in ("executive", "exec")
            and a.get("recommendation", "").lower() == "include"
        )
    ]
    if not passing and scored:
        # Nothing cleared the strict bar — take the single best-scored article anyway rather
        # than returning nothing. Flagged so it's visibly a relaxed pick, not a real pass.
        best = max(scored, key=lambda a: a.get("relevance_score", 0.0))
        best["relaxed_selection"] = "No article met the score>=6.0/executive/include bar; this is the highest-scored candidate available."
        passing = [best]
        log.info("No article passed strict scoring — falling back to best-scored: '%s' (%.1f)",
                  best.get("title", "")[:60], best.get("relevance_score", 0.0))
    articles_after_scoring = len(passing)

    # ------------------------------------------------------------------
    # 9. Deduplicate
    # ------------------------------------------------------------------
    if deduplicate_articles is not None:
        try:
            passing = deduplicate_articles(passing)
        except Exception as exc:
            log.debug("deduplicate_articles failed: %s — using URL fallback", exc)
            passing = _deduplicate(passing)
    else:
        passing = _deduplicate(passing)

    articles_after_dedup = len(passing)

    # ------------------------------------------------------------------
    # 10. Sort by score descending, take top 10
    # ------------------------------------------------------------------
    passing.sort(key=lambda a: a.get("relevance_score", 0.0), reverse=True)
    top10 = passing[:10]

    # ------------------------------------------------------------------
    # 11. Fetch full article content for top 10
    # ------------------------------------------------------------------
    if fetch_article_content is not None:
        for article in top10:
            # RSS feeds often populate `content` with a short one-sentence blurb, which made
            # the old `if not article.get("content")` guard skip the real fetch entirely.
            # Always try the full fetch; keep the blurb only as a fallback if it fails.
            # fetch_article_content itself rejects CSS/JS junk and returns "" in that case.
            if article.get("url"):
                try:
                    scraped = fetch_article_content(article["url"])
                    if scraped:
                        article["content"] = scraped
                except Exception as exc:
                    log.debug("fetch_article_content failed for %s: %s", article.get("url"), exc)

    # ------------------------------------------------------------------
    # 11a. Real-date freshness re-check for scraped (undated) articles.
    # Scraped listing-page sources never get a real publish date at fetch time (no reliable
    # field on a generic homepage), so time_filter treats "no date" as "always fresh" rather
    # than silently discarding them — but that meant a genuinely weeks-old scraped article
    # (confirmed: a Logistics Management piece byline-dated Aug 25, still surfacing in a
    # 48h-window run in September) could pass the freshness filter forever. Now that we have
    # the real article text, extract its actual date and drop it if it's actually stale.
    # ------------------------------------------------------------------
    if extract_published_date is not None and is_article_fresh is not None:
        still_fresh = []
        newly_stale: dict = {}
        for article in top10:
            if article.get("published_at"):
                still_fresh.append(article)  # already had a real date, already filtered correctly
                continue
            real_date = extract_published_date(article.get("content", ""))
            if real_date is None:
                still_fresh.append(article)  # couldn't determine — don't punish for our own gap
                continue
            article["published_at"] = real_date
            if is_article_fresh(real_date, hours_window):
                still_fresh.append(article)
            else:
                log.info("Dropping stale scraped article (real date %s, outside window): '%s'",
                          real_date, article.get("title", "")[:60])
                if article.get("url"):
                    newly_stale[article["url"]] = real_date
        _record_stale_urls(root, newly_stale)
        top10 = still_fresh

    # ------------------------------------------------------------------
    # 11b. Gate candidates against the written SOURCE SELECTION CRITERIA
    # (redundant status-updates, no-claim announcements, wrong audience, etc.) —
    # this makes the reference-doc criteria an actual filter, not just prompt flavor.
    # Walk top10 in score order, keep the first 3 that pass, backfill from the rest.
    # ------------------------------------------------------------------
    ref_docs_for_gate = ""
    if check_source_criteria is not None:
        try:
            from pathlib import Path as _Path
            docs_dir = _Path(root) / "config" / "reference_docs"
            texts = []
            for f in sorted(docs_dir.glob("*.txt")) + sorted(docs_dir.glob("*.md")):
                if f.name == "README.md":
                    continue
                texts.append(f.read_text()[:20000])
            ref_docs_for_gate = "\n\n".join(texts)
        except Exception:
            pass

    top3: list[dict] = []
    gated: list[dict] = []  # every candidate the gate actually reviewed, in order, pass or fail
    if check_source_criteria is not None:
        for article in top10:
            if len(top3) >= 3:
                break
            gate = check_source_criteria(article, ref_docs_for_gate)
            llm_calls_made += 1
            article["source_gate"] = gate
            gated.append(article)
            if gate.get("pass"):
                top3.append(article)
            else:
                log.info("Source gate rejected '%s': %s", article.get("title", "")[:60], gate.get("reason"))

        if not top3 and gated:
            # No override. The gate rejects for disqualifying reasons — sponsored content,
            # unattributed marketing, earnings recaps, nothing to argue with — and overriding
            # it shipped exactly those: a Huron advertorial the gate had flagged as paid, and
            # an unattributed procurement piece it called marketing copy. An empty section
            # states plainly that nothing cleared the bar; a rescued advertorial misrepresents
            # itself as the day's best thinking, which is worse than sending nothing.
            worst = max(gated, key=lambda a: a.get("relevance_score", 0.0))
            log.info("All %d candidate(s) failed the gate — sending none. Closest: '%s' (%.1f) — %s",
                     len(gated), worst.get("title", "")[:50], worst.get("relevance_score", 0.0),
                     (worst.get("source_gate") or {}).get("reason", "")[:120])
    else:
        top3 = top10[:3]
    top_3_selected = len(top3)

    for article in top3:
        if not article.get("summary_bullets"):
            if summarize_article is not None:
                try:
                    title = article.get("title", "")
                    content = article.get("content", "")
                    source = article.get("source", "")

                    bullets = summarize_article(title, content, source)
                    llm_calls_made += 1

                    # ── Hater Bot review — flags only, no rewrite to keep pipeline fast ──
                    if run_hater_bot is not None and bullets:
                        summary_text = " | ".join(bullets)
                        review = run_hater_bot(summary_text, title)
                        llm_calls_made += 1
                        article["hater_bot"] = review

                    article["summary_bullets"] = bullets if isinstance(bullets, list) else [bullets]
                except Exception as exc:
                    log.debug("summarize_article failed: %s", exc)
                    article["summary_bullets"] = _fallback_summarize(article)
            else:
                article["summary_bullets"] = _fallback_summarize(article)

        # Ensure why_it_matters is set
        if not article.get("why_it_matters"):
            article["why_it_matters"] = _why_it_matters(article.get("matched_themes", []))

    # ------------------------------------------------------------------
    # 13. POV Generation — TADA's take on each article (Llama)
    # ------------------------------------------------------------------
    if generate_pov_for_article is not None:
        ref_docs = ref_docs_for_gate  # same reference material already loaded for the gate
        for article in top3:
            try:
                pov = generate_pov_for_article(article, ref_docs)
                article["tada_pov"] = pov
                llm_calls_made += 1
            except Exception as exc:
                log.debug("POV generation error: %s", exc)
                article["tada_pov"] = ""

    # ------------------------------------------------------------------
    # 14. LinkedIn content validation — enrich articles, never filter
    # ------------------------------------------------------------------
    for article in top3:
        if validate_for_linkedin is not None:
            try:
                article["linkedin_validation"] = validate_for_linkedin(article)
                llm_calls_made += 1
            except Exception as exc:
                log.debug("linkedin_validator error: %s", exc)
                article.setdefault("linkedin_validation", {})

    # ------------------------------------------------------------------
    # 15. Build return structure
    # ------------------------------------------------------------------
    run_duration = round(time.time() - start_time, 2)
    status = "success" if top3 else "no_articles_found"

    return {
        "top_articles": top3,
        # Every candidate that reached scoring, with its fetched body. Competitor tracking
        # scans these for mentions, so that half of it costs no extra requests — without
        # this it would only ever see the three selected articles.
        "all_candidates": articles,
        "usage_stats": {
            "articles_fetched": articles_fetched,
            "articles_after_time_filter": articles_after_time_filter,
            "articles_after_scoring": articles_after_scoring,
            "articles_after_dedup": articles_after_dedup,
            "top_3_selected": top_3_selected,
            "llm_calls_made": llm_calls_made,
            "run_duration_seconds": run_duration,
            # Reported as "llama3.1 (local)" at $0.00 regardless of what actually ran. With
            # ANTHROPIC_API_KEY set — as it is in CI — every call went to Claude over the
            # API and cost real money, so both fields were simply untrue.
            "model": ("claude-haiku-4-5 (api)" if os.environ.get("ANTHROPIC_API_KEY", "").strip()
                      else "llama3.1 (local)"),
            "source_funnel": source_funnel,
        },
        "run_metadata": {
            "run_date": now_utc.isoformat().replace("+00:00", "Z"),
            "time_window_hours": hours_window,
            "active_themes": active_theme_names,
            "sources_used": list(dict.fromkeys(sources_used)),  # dedup, preserve order
            "status": status,
        },
    }
