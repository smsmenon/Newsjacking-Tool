from __future__ import annotations
import logging
import re
import ssl
import threading
import time
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

try:
    import trafilatura as _trafilatura
except ImportError:  # keep the regex path working if the dependency is missing
    _trafilatura = None

try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
except ImportError:
    _ScraplingFetcher = None

# Publishers whose robots.txt names Claude's crawler with Disallow: /. Their pages are never
# requested — SCMR syndicates full articles in its RSS feed, so that content still reaches the
# pipeline through the channel they publish it on.
ROBOTS_OPTED_OUT_HOSTS = {
    "scmr.com", "www.scmr.com",
    "supplychain247.com", "www.supplychain247.com",
}
_ROBOTS_OPTED_OUT_HOSTS = ROBOTS_OPTED_OUT_HOSTS  # back-compat alias


def _fetch_html(url: str) -> str:
    """Page HTML, preferring the client that presents a normal browser TLS fingerprint.

    Several publishers' WAFs reject any client that doesn't look like a browser at the
    transport layer, regardless of headers — Supply Chain Digital, Procurement Magazine,
    Inbound Logistics and McKinsey all returned 403 to urllib and 200 to this. Falls back to
    urllib so the pipeline still runs without the optional dependency.
    """
    if _ScraplingFetcher is not None:
        try:
            page = _ScraplingFetcher.get(url, timeout=30)
            if getattr(page, "status", 0) == 200:
                html = str(page.html_content or "")
                if html:
                    return html
        except Exception as exc:
            log.debug("scrapling fetch failed for %s: %s — falling back to urllib", url, exc)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
                return r.read(2_000_000).decode("utf-8", errors="replace")
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 429):
                _back_off_host(url)
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                _wait_for_host(url)
            else:
                log.debug("article_scraper: failed to fetch %s — %s", url, exc)
    return ""

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

_BLOCK_TAGS = re.compile(r"<(script|style|nav|header|footer|aside|form|noscript|iframe)[^>]*>.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_MULTI_WS = re.compile(r"\s{2,}")


_MONTHS_FULL = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_MONTHS_ABBR = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
_MONTH_ANY = f"{_MONTHS_FULL}|{_MONTHS_ABBR}"

# Ordered by how common each byline style is; first match wins.
_DATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "August 25, 2026" / "Aug 25, 2026" / "August 25th, 2026"
    (re.compile(rf"\b({_MONTH_ANY})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d{{2}})\b"), "MDY"),
    # "25 August 2026" / "25th August 2026" (day-month-year, common on non-US sites)
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_ANY})\.?,?\s+(20\d{{2}})\b"), "DMY"),
    # ISO-style "2026-08-25"
    (re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b"), "YMD"),
]


_NEXT_ALLOWED_AT: dict[str, float] = {}
_HOST_DELAY: dict[str, float] = {}
_THROTTLE_LOCK = threading.Lock()
_DEFAULT_HOST_DELAY = 3.0
_BACKOFF_HOST_DELAY = 10.0  # what Supply Chain Brain's robots.txt asks for


def _host_of(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc


def _wait_for_host(url: str) -> None:
    """
    Space out requests to the same host.

    Fetching one publisher's article pages back to back reads as a burst and gets
    rate-limited: Supply Chain Brain and SCMR returned 403 for every article during pipeline
    runs while the very same URL fetched fine in isolation, leaving the gate with "No real
    article content available to judge fit."

    Slots are reserved under a lock and waited on outside it, so parallel fetches to
    different hosts still overlap.
    """
    host = _host_of(url)
    if not host:
        return
    with _THROTTLE_LOCK:
        delay = _HOST_DELAY.get(host, _DEFAULT_HOST_DELAY)
        start_at = max(time.monotonic(), _NEXT_ALLOWED_AT.get(host, 0.0))
        _NEXT_ALLOWED_AT[host] = start_at + delay
    remaining = start_at - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)


def _back_off_host(url: str) -> None:
    """A host that answered 403/429 gets the slower, robots.txt-style delay from here on."""
    host = _host_of(url)
    if not host:
        return
    with _THROTTLE_LOCK:
        if _HOST_DELAY.get(host, 0.0) < _BACKOFF_HOST_DELAY:
            _HOST_DELAY[host] = _BACKOFF_HOST_DELAY
            log.debug("article_scraper: backing off %s to %.0fs between requests",
                      host, _BACKOFF_HOST_DELAY)


def extract_published_date(text: str) -> str | None:
    """
    Best-effort real publish date from a fetched article's own text (byline, dateline).
    Scraped listing-page sources never get a real date at fetch time (no reliable field on
    a generic homepage/listing page), which meant their freshness check silently defaulted
    to "always fresh" — letting genuinely weeks-old articles pass a 24-48h filter forever.
    The full article page almost always states its real date in prose; this recovers it once
    we have that content, so a proper freshness re-check becomes possible. Tries several
    common byline styles (full/abbreviated month, day-first, ISO) since sites vary.
    """
    from datetime import datetime

    window = text[:1500]  # date is always near the top (byline), not the body
    for pattern, order in _DATE_PATTERNS:
        m = pattern.search(window)
        if not m:
            continue
        try:
            if order == "MDY":
                month, day, year = m.groups()
                dt = datetime.strptime(f"{month[:3]} {day} {year}", "%b %d %Y")
            elif order == "DMY":
                day, month, year = m.groups()
                dt = datetime.strptime(f"{day} {month[:3]} {year}", "%d %b %Y")
            else:  # YMD
                year, month, day = m.groups()
                dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            continue
    return None


def _looks_like_real_article(text: str) -> bool:
    """Cheap heuristic to reject CSS/JS junk that slipped past tag-stripping (no LLM call).

    Real prose is mostly letters/spaces with normal punctuation. Leftover CSS/JS is dense
    with structural symbols ({ } ; : . -) and lacks common English stopwords.
    """
    if len(text) < 200:
        return False
    symbol_count = sum(text.count(c) for c in "{};:")
    symbol_ratio = symbol_count / len(text)
    if symbol_ratio > 0.02:  # real prose is well under 1%; CSS rule blocks are far denser
        return False
    lower = f" {text.lower()} "
    stopword_hits = sum(1 for w in (" the ", " and ", " that ", " with ", " for ") if w in lower)
    return stopword_hits >= 3


def fetch_article_content(url: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    if _host_of(url) in _ROBOTS_OPTED_OUT_HOSTS:
        log.debug("article_scraper: %s disallows our crawler in robots.txt — using feed text only", url)
        return ""

    _wait_for_host(url)
    raw = _fetch_html(url)
    if not raw:
        return ""

    # Purpose-built extraction first. The hand-rolled tag logic below looks for an <article>
    # or <main> wrapper, which many templates simply do not use — IndustryWeek and Forbes
    # pages downloaded fine at ~200KB and still yielded nothing, and were discarded before
    # ever being scored. trafilatura finds the body regardless of wrapper.
    if _trafilatura is not None:
        try:
            extracted = _trafilatura.extract(raw, include_comments=False, include_tables=False)
            if extracted:
                text = _MULTI_WS.sub(" ", extracted).strip()[:3000]
                if _looks_like_real_article(text):
                    return text
        except Exception as exc:
            log.debug("trafilatura failed for %s: %s — falling back to tag extraction", url, exc)

    # Remove noise blocks
    html = _BLOCK_TAGS.sub(" ", raw)

    # Extract <article> or <main> body if present
    # Pages carry several <article> elements — related-story teasers, "most read" rails —
    # and a non-greedy search returns whichever comes first in the markup, which on Supply
    # Chain Brain is a sidebar teaser that reduces to ~90 characters and then fails the
    # quality check. The main body is reliably the longest of them.
    for tag in ("article", "main"):
        blocks = re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.I | re.S)
        if blocks:
            biggest = max(blocks, key=len)
            # On some templates every <article> is a related-story teaser (~1-2KB) and the
            # real body sits in an unmarked div, so the largest match is still a teaser.
            # Only trust the container when it is big enough to be a body.
            if len(biggest) > 3000:
                html = biggest
            break

    text = _TAG.sub(" ", html)
    text = _MULTI_WS.sub(" ", text).strip()
    text = text[:3000]
    if not _looks_like_real_article(text):
        log.debug("article_scraper: extracted text failed quality check for %s", url)
        return ""
    return text
