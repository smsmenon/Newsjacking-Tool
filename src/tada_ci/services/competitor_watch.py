"""
Daily competitor tracking: what the nine tracked companies did in the last 24 hours that
could affect a sales conversation, TADA's positioning, or a content opportunity.

Three collection routes, none of which need a paid search API:
  1. Each competitor's own channel — RSS, WordPress REST, or their newsroom page.
  2. Press-release wires, filtered for competitor names. Launches, funding and partnerships
     almost always cross a wire.
  3. The trade articles the discovery pipeline already fetched, scanned for mentions. Free:
     those are in memory by the time this runs.

The gap this leaves is deliberate and worth stating: a competitor mention on a site nobody
listed is invisible here. Closing it needs open-web search, which Google now gates behind
billing — see the conversation around brave_search.py for the options.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Broad business/tech wires. Competitor names are filtered out of these afterwards, so a
# noisy feed costs nothing but a string match.
WIRE_FEEDS = {
    "PR Newswire": "https://www.prnewswire.com/rss/technology-latest-news/technology-latest-news-list.rss",
    "Business Wire": "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFpRXg==",
    "GlobeNewswire": "https://www.globenewswire.com/RssFeed/subjectcode/22-Technology/feedTitle/GlobeNewswire%20-%20Technology",
}

# One competitor publishing five things shouldn't crowd out the other eight. SAP and
# Palantir are the likely offenders given how much they announce.
MAX_ITEMS_PER_COMPETITOR = 2

# Google News RSS pacing. Unauthenticated and free, so politeness is the only rate control
# available — and the only thing standing between a run and a wall of 429s.
_NEWS_MIN_GAP_SECONDS = 3.0
_NEWS_BACKOFF_SECONDS = 20.0
_last_news_call_at = 0.0

EMPTY_SECTION_LINE = "No major competitor updates today."


def load_competitors(root: Path) -> list[dict]:
    path = Path(root) / "config" / "competitors.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _seen_path(root: Path) -> Path:
    return Path(root) / "data" / "competitor_seen.json"


def load_seen(root: Path) -> dict:
    """URL -> when we first saw it.

    Newsroom pages carry no publish date, and most competitor posts have no parseable date
    in the body either, so "is this from the last 24 hours?" cannot be answered from the
    page. What can be answered is "did this exist last time we looked" — which is the same
    question for our purposes, and is how a newsroom's own RSS reader would decide.
    """
    try:
        path = _seen_path(root)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as exc:
        log.debug("competitor_watch: could not read seen cache: %s", exc)
        return {}


def record_seen(root: Path, urls: list[str]) -> None:
    from datetime import datetime, timezone

    urls = [u for u in urls if u]
    if not urls:
        return
    try:
        now = datetime.now(timezone.utc).isoformat()
        merged = load_seen(root)
        for url in urls:
            merged.setdefault(url, now)
        path = _seen_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        log.debug("competitor_watch: could not write seen cache: %s", exc)


def _name_matches(text: str, competitor: dict) -> bool:
    """Whether a piece of text is about this competitor.

    Deliberately strict for the ambiguous ones: "Lyric" alone matches song-lyric sites and
    "Blue Yonder" matches aviation and video-game content, so those require a supply-chain
    word nearby rather than the bare name.
    """
    low = text.lower()
    name = competitor["name"].lower()
    if name not in low:
        return False
    if competitor["name"] in ("Lyric", "Blue Yonder", "Pelico"):
        context = ("supply chain", "manufactur", "procure", "logistic", "planning",
                   "inventory", "chainbrain", "decision intelligence")
        return any(word in low for word in context)
    return True


def _google_news(term: str, hours_window: int) -> list[tuple[str, str, str]]:
    """Open-web news search for one term, as (title, url, published).

    Google News RSS needs no key, no billing and no account, which the Custom Search JSON
    API now does. It is the only free route that reaches past a fixed list of sites —
    without it, anything a competitor does that is covered somewhere we do not track is
    invisible. Returns [] on any failure; this route is a bonus, never load-bearing.
    """
    import re
    import urllib.parse

    window = "1d" if hours_window <= 24 else f"{max(1, hours_window // 24)}d"
    query = urllib.parse.urlencode({
        "q": f"{term} when:{window}",
        "hl": "en-US", "gl": "US", "ceid": "US:en",
    })
    url = f"https://news.google.com/rss/search?{query}"

    # Google rate-limits this endpoint: firing ~15 queries back to back drew 429s on two of
    # seven. Space them out, and retry once after a longer wait rather than losing the term.
    global _last_news_call_at
    import time

    try:
        from scrapling.fetchers import Fetcher

        body = ""
        for attempt in range(2):
            wait = _NEWS_MIN_GAP_SECONDS - (time.monotonic() - _last_news_call_at)
            if wait > 0:
                time.sleep(wait)
            _last_news_call_at = time.monotonic()

            page = Fetcher.get(url, timeout=25)
            status = getattr(page, "status", 0)
            if status == 200:
                body = str(page.html_content or "")
                break
            if status == 429 and attempt == 0:
                log.debug("competitor_watch: google news 429 for %r — backing off", term)
                time.sleep(_NEWS_BACKOFF_SECONDS)
                continue
            return []
        if not body:
            return []
    except Exception as exc:
        log.debug("competitor_watch: google news failed for %r: %s", term, exc)
        return []

    results: list[tuple[str, str, str]] = []
    for block in re.findall(r"<item>(.*?)</item>", body, re.S | re.I)[:10]:
        title = re.search(r"<title>(.*?)</title>", block, re.S | re.I)
        # <link> is a void element in HTML, so the parser drops its closing tag and the URL
        # simply runs up to the next tag. <pubDate> comes back lowercased for the same
        # reason — both patterns have to tolerate what an HTML parser does to RSS.
        link = re.search(r"<link\s*/?>([^<]+)", block, re.I)
        date = re.search(r"<pubdate>(.*?)</pubdate>", block, re.S | re.I)
        if not title or not link:
            continue
        clean = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        results.append((clean, link.group(1).strip(), date.group(1).strip() if date else ""))
    return results


def collect_candidates(root: Path, trade_articles: list[dict] | None = None,
                       hours_window: int = 24) -> list[dict]:
    """Everything plausibly about a tracked competitor, before any LLM judgement."""
    from .article_scraper import fetch_article_content
    from .rss_fetcher import fetch_rss_articles, fetch_wp_rest_articles
    from .site_scraper import scrape_listing_page
    from .time_filter import is_article_fresh

    competitors = load_competitors(root)
    candidates: list[dict] = []

    def add(competitor: dict, title: str, url: str, published: str, body: str, origin: str) -> None:
        if not title or not url:
            return
        candidates.append({
            "competitor": competitor["name"],
            "title": title,
            "url": url,
            "published_at": published,
            "content": body,
            "origin": origin,
        })

    # 1. The competitor's own channel.
    for competitor in competitors:
        source = {
            "name": competitor["name"],
            "category": "Competitor",
            "url": competitor.get("newsroom", ""),
            "rss_url": competitor.get("rss_url", ""),
            "wp_json_url": competitor.get("wp_json_url", ""),
            "article_url_pattern": competitor.get("article_url_pattern", ""),
        }
        try:
            if source["rss_url"]:
                found = fetch_rss_articles(source, limit=15)
            elif source["wp_json_url"]:
                found = fetch_wp_rest_articles(source, limit=15)
            elif source["url"]:
                found = scrape_listing_page(source, limit=10)
            else:
                found = []
        except Exception as exc:
            log.warning("competitor_watch: %s own-channel fetch failed: %s", competitor["name"], exc)
            found = []

        for article in found:
            published = getattr(article, "publication_date", "") or ""
            # Scraped newsrooms carry no date; keep them and let the classifier see the body.
            if published and not is_article_fresh(published, hours_window):
                continue
            add(competitor, getattr(article, "title", ""), getattr(article, "url", ""),
                published, getattr(article, "full_text", "") or "", "own channel")

    # 2. Press wires, filtered by name.
    for wire_name, feed_url in WIRE_FEEDS.items():
        try:
            releases = fetch_rss_articles(
                {"name": wire_name, "category": "Wire", "rss_url": feed_url}, limit=50
            )
        except Exception as exc:
            log.warning("competitor_watch: wire %s failed: %s", wire_name, exc)
            continue
        for release in releases:
            published = getattr(release, "publication_date", "") or ""
            if published and not is_article_fresh(published, hours_window):
                continue
            blob = f"{getattr(release, 'title', '')} {getattr(release, 'full_text', '')}"
            for competitor in competitors:
                if _name_matches(blob, competitor):
                    add(competitor, getattr(release, "title", ""), getattr(release, "url", ""),
                        published, getattr(release, "full_text", "") or "", wire_name)
                    break

    # 3. Open-web news search. This is the "anywhere on the internet" route: Google News
    # indexes far beyond our source list, and it surfaced a Kinaxis CEO interview in the
    # Indian press and a FourKites product story on a site we do not track — neither of
    # which appears on the companies' own newsrooms.
    for competitor in competitors:
        for term in competitor.get("search_terms") or [competitor["name"]]:
            for title, link, published in _google_news(term, hours_window):
                if not _name_matches(title, competitor):
                    continue
                add(competitor, title, link, published, "", "Google News")

    # 4. Trade articles the discovery pipeline already pulled — free to reuse.
    for article in trade_articles or []:
        blob = f"{article.get('title', '')} {article.get('content', '')[:2000]}"
        for competitor in competitors:
            if _name_matches(blob, competitor):
                add(competitor, article.get("title", ""), article.get("url", ""),
                    article.get("published_at", ""), article.get("content", ""),
                    article.get("source", "trade press"))
                break

    # Dedupe by URL, preferring whichever copy already carries body text.
    best: dict[str, dict] = {}
    for item in candidates:
        existing = best.get(item["url"])
        if not existing or len(item["content"]) > len(existing["content"]):
            best[item["url"]] = item
    deduped = list(best.values())

    # Fill in missing bodies so the classifier judges the story, not the headline.
    for item in deduped:
        if len(item["content"]) < 300 and item["url"]:
            try:
                fetched = fetch_article_content(item["url"])
                if fetched:
                    item["content"] = fetched
            except Exception as exc:
                log.debug("competitor_watch: body fetch failed for %s: %s", item["url"], exc)

    # Newsroom pages give no publish date, so those items skipped the freshness check above
    # and a months-old blog post would read as today's news. Now that the body is here, read
    # the real date out of it and drop anything genuinely stale.
    from .article_scraper import extract_published_date

    fresh: list[dict] = []
    for item in deduped:
        if item.get("published_at"):
            fresh.append(item)
            continue
        real_date = extract_published_date(item.get("content", ""))
        if real_date is None:
            # Undated and unparseable — the seen-cache decides this one instead.
            item["date_unknown"] = True
            fresh.append(item)
            continue
        item["published_at"] = real_date
        if is_article_fresh(real_date, hours_window):
            fresh.append(item)
        else:
            log.info("competitor_watch: dropping stale %s item (%s): %s",
                     item["competitor"], real_date[:10], item.get("title", "")[:60])

    log.info("competitor_watch: %d candidate(s) across %d competitor(s)",
             len(fresh), len({i["competitor"] for i in fresh}))
    return fresh


def classify(item: dict, competitor: dict, reference_docs: str) -> dict:
    """Decide whether an item belongs in the digest, and write its three lines."""
    from .contrarian_pipeline import _claude

    keep_rules = competitor.get("keep_even_if_off_topic") or []
    keep_block = "\n".join(f"- {rule}" for rule in keep_rules)
    scope = competitor.get("scope") or "No special scoping — ordinary competitor coverage."

    prompt = f"""You are screening competitor news for TADA, a supply chain intelligence platform.

TADA REFERENCE MATERIAL (for judging overlap with TADA's own claims):
{reference_docs[:12000]}

COMPETITOR: {competitor['name']}
SCOPE FOR THIS COMPETITOR: {scope}
{"ALWAYS KEEP THESE, even though they look out of scope:" + chr(10) + keep_block if keep_block else ""}

CANDIDATE ITEM
Title: {item.get('title', '')}
Source: {item.get('origin', '')}
Published: {item.get('published_at', '') or 'date not stated'}
Body: {(item.get('content') or '')[:2500]}

INCLUDE only if it is one of:
- a product launch or major new capability
- a customer win, especially a manufacturer
- a partnership with an ERP or cloud platform (SAP, Oracle, Microsoft, AWS, Snowflake...)
- funding, an acquisition, or layoffs
- a Gartner, Forrester or IDC placement, or a major award
- a C-suite or head-of-product change
- a public position on a theme TADA owns: system of action, autonomous execution, AI agents
  in planning, or execution versus visibility
- anything named in this competitor's ALWAYS KEEP list

SKIP everything else, including: other blog posts and thought leadership, job postings,
webinars and event attendance, listicles that mention them in passing, and anything older
than 24 hours.

If the item is a partnership between this competitor and SAP, Oracle or another platform,
attribute it to this competitor — do not treat the platform as the subject.

Answer with ONLY these labelled lines:
INCLUDE: [true/false]
CATEGORY: [launch | customer | partnership | funding | analyst | people | positioning | other]
WHAT: [one sentence, paraphrased, no copied article text]
WHY: [one line on why it matters for TADA]
ANGLE: [one line content angle, or NONE if there is no real one]
OVERLAP: [true/false — true if they claim something TADA also claims]"""

    try:
        raw = _claude(prompt, max_tokens=400)
    except Exception as exc:
        log.debug("competitor_watch classify failed: %s", exc)
        return {"include": False}

    parsed: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            parsed[key.strip().upper()] = value.strip()

    if parsed.get("INCLUDE", "").lower() != "true":
        return {"include": False}

    angle = parsed.get("ANGLE", "")
    return {
        "include": True,
        "competitor": item["competitor"],
        "url": item["url"],
        "published_at": item.get("published_at", ""),
        "category": parsed.get("CATEGORY", "other"),
        "what": parsed.get("WHAT", ""),
        "why": parsed.get("WHY", ""),
        "angle": "" if angle.upper() in ("NONE", "") else angle,
        "overlap": parsed.get("OVERLAP", "").lower() == "true",
    }


def run_competitor_watch(root: Path, trade_articles: list[dict] | None = None,
                         hours_window: int = 24) -> list[dict]:
    """Collect, classify, cap. Returns the items for the digest's competitor section."""
    from .contrarian_pipeline import _load_reference_docs

    competitors = {c["name"]: c for c in load_competitors(root)}
    reference_docs = _load_reference_docs(root)

    candidates = collect_candidates(root, trade_articles, hours_window)
    seen = load_seen(root)
    record_seen(root, [c["url"] for c in candidates])

    if not seen:
        # First run: every newsroom's back catalogue looks new. Record it as the baseline
        # and report nothing, rather than mailing months of history as today's news.
        log.info("competitor_watch: first run — recorded %d URL(s) as baseline, reporting none",
                 len(candidates))
        return []

    # An item we have already seen is not news, whatever its page says about dates.
    new_items = [c for c in candidates if c["url"] not in seen]
    if len(new_items) != len(candidates):
        log.info("competitor_watch: %d of %d candidate(s) are new since the last run",
                 len(new_items), len(candidates))

    kept: list[dict] = []
    for item in new_items:
        competitor = competitors.get(item["competitor"])
        if not competitor:
            continue
        verdict = classify(item, competitor, reference_docs)
        if verdict.get("include"):
            kept.append(verdict)

    # Cap per competitor, keeping the ones that overlap TADA's own claims first.
    by_competitor: dict[str, list[dict]] = {}
    for item in kept:
        by_competitor.setdefault(item["competitor"], []).append(item)

    final: list[dict] = []
    for name, items in by_competitor.items():
        items.sort(key=lambda i: (not i["overlap"],))
        final.extend(items[:MAX_ITEMS_PER_COMPETITOR])

    final.sort(key=lambda i: (not i["overlap"], i["competitor"]))
    log.info("competitor_watch: %d item(s) kept for the digest", len(final))
    return final
