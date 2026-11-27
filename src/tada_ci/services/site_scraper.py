from __future__ import annotations

import logging
import re
import time
import urllib.request
from html import unescape
from urllib.parse import urljoin, urlsplit

from tada_ci.models import Article
from .article_scraper import ROBOTS_OPTED_OUT_HOSTS

log = logging.getLogger(__name__)

try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
except ImportError:
    _ScraplingFetcher = None

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_ANCHOR = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_MULTI_WS = re.compile(r"\s{2,}")

# Links that are structurally never article headlines on a listing/homepage — nav,
# category/topic index pages, legal, and generic promo pages rather than actual articles.
_JUNK_HREF = re.compile(
    r"(login|signin|signup|subscribe|privacy|terms|cookie|contact|about|advertis|"
    r"careers|sitemap|rss|feed|guidelines|awards|/topics?/|/resources?/|/podcast|formstack|"
    # Section fronts and directory pages that read as headlines but hold no article:
    # "/magazines", "/logistics-planner/", "/all-leaders-profiles/", "/top-100-reports".
    r"/magazines?|/planner|/all-leaders|/leaders-profiles|/profiles?/|/rfp|/top-\d+|"
    r"/archives?/|/issues?/|/whitepapers?|/webinars?|/events?/|/directory|/buyers-guide|"
    r"facebook\.com|twitter\.com|x\.com|linkedin\.com|instagram\.com|youtube\.com|"
    r"#|mailto:|javascript:|\.(png|jpg|jpeg|gif|svg|pdf)$)",
    re.I,
)

# A lone short path segment ("/magazines", "/global-freight-trade") is a section front, not
# an article — real article slugs are longer or carry an id. Checked only when the URL has
# no article-shaped id, so numeric permalinks are never caught by this.
_SECTION_FRONT = re.compile(r"^/[a-z0-9-]{1,28}/?$", re.I)

# A real article URL on most news CMSs has a numeric ID or a /YYYY/MM/ date segment in the
# path. When a page has enough of these, prefer them over the generic heuristic — this is
# what separates real articles from category/index pages that also have long link text.
_ARTICLE_URL_HINT = re.compile(r"/\d{4,}(/|$|-)|/20\d{2}/\d{1,2}/")


def _title_from_slug(href: str) -> str:
    """Readable headline from a URL slug, for links whose anchor text is a bare CTA."""
    slug = urlsplit(href).path.rstrip("/").rsplit("/", 1)[-1]
    slug = re.sub(r"\.(html?|php|aspx)$", "", slug, flags=re.I)
    words = [w for w in re.split(r"[-_]+", slug) if w and not w.isdigit()]
    return " ".join(w.capitalize() if w.islower() else w for w in words)


def _clean_text(html_fragment: str) -> str:
    text = _TAG.sub(" ", html_fragment)
    text = unescape(text)
    return _MULTI_WS.sub(" ", text).strip()


def _fetch(url: str, timeout: int = 20) -> str:
    """Listing-page HTML, preferring the browser-fingerprinted client.

    Several publishers' WAFs reject plain urllib at the transport layer and return nothing
    usable, which is why six sources produced zero links. Falls back to urllib so the
    scraper still works without the optional dependency.
    """
    from urllib.parse import urlsplit as _split

    if _split(url).netloc in ROBOTS_OPTED_OUT_HOSTS:
        log.debug("site_scraper: %s disallows our crawler in robots.txt — not fetching", url)
        return ""

    if _ScraplingFetcher is not None:
        try:
            page = _ScraplingFetcher.get(url, timeout=timeout + 10)
            if getattr(page, "status", 0) == 200:
                html = str(page.html_content or "")
                if html:
                    return html
        except Exception as exc:
            log.debug("site_scraper: scrapling failed for %s: %s — falling back", url, exc)

    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(400_000).decode("utf-8", errors="replace")
        except Exception as exc:
            # ponytail: transient DNS/network flakiness, not a code bug — 3 attempts, short backoff
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def scrape_listing_page(source: dict, limit: int = 8) -> list[Article]:
    """
    Best-effort generic scraper for a site's homepage/listing page, used only when no RSS
    feed exists. This is a heuristic link extractor, not a per-site parser: it keeps anchor
    tags whose visible text is headline-shaped (long enough, not a nav/legal link) and
    discards the rest.

    Known limitations (deliberate — a full per-site parser for 15 different CMSs is not
    worth building for this): no publication date is extracted (downstream freshness
    filtering treats undated articles as fresh, so scraped sources aren't time-filtered the
    way RSS sources are), and some non-article "headline-shaped" links (e.g. section fronts)
    will slip through. Good enough to surface real candidates; not RSS-feed precision.
    """
    url = source.get("url", "")
    if not url:
        return []

    try:
        html = _fetch(url)
    except Exception as exc:
        log.debug("site_scraper: failed to fetch %s — %s", url, exc)
        return []

    raw_pattern = source.get("article_url_pattern", "")
    try:
        url_pattern = re.compile(raw_pattern, re.I) if raw_pattern else None
    except re.error as exc:
        log.warning("site_scraper: bad article_url_pattern for %s (%s) — ignoring",
                    source.get("name", "?"), exc)
        url_pattern = None

    candidates: list[tuple[str, str]] = []  # (title, full_url), in page order, deduped
    seen_urls: set[str] = set()

    for match in _ANCHOR.finditer(html):
        href, inner = match.group(1), match.group(2)
        title = _clean_text(inner)

        # When the URL shape already identifies an article, a useless anchor label is not a
        # reason to drop it — Blue Yonder links its press releases behind the words "Learn
        # More", with the headline in a separate heading. Recover the title from the slug.
        if url_pattern and url_pattern.search(urljoin(url, href)) and len(title) < 20:
            title = _title_from_slug(href) or title

        if len(title) < 20 or len(title) > 200:
            continue
        if _JUNK_HREF.search(href):
            continue

        full_url = urljoin(url, href)
        if full_url in seen_urls or not full_url.startswith("http"):
            continue
        # Some newsrooms render their list client-side, so the served HTML carries only
        # product and nav links — FourKites' /newsroom yields "/platform/digital-twins/..."
        # and Blue Yonder's /media yields "/why-blue-yonder/...". Where a source knows the
        # shape of its own article URLs, keep only those.
        if url_pattern and not url_pattern.search(full_url):
            continue
        path = urlsplit(full_url).path
        if _SECTION_FRONT.match(path) and not _ARTICLE_URL_HINT.search(full_url):
            continue
        seen_urls.add(full_url)
        candidates.append((title, full_url))

    # Prefer links whose URL shape looks like a real article (numeric ID or /YYYY/MM/ date)
    # over generic category/index pages — but only when there are enough of them; some sites
    # don't use that URL convention at all, and falling back to everything beats returning
    # nothing.
    article_shaped = [c for c in candidates if _ARTICLE_URL_HINT.search(c[1])]
    chosen = article_shaped if len(article_shaped) >= 3 else candidates

    return [
        Article(
            title=title,
            source=source.get("name", ""),
            category=source.get("category", ""),
            url=full_url,
            publication_date="",
            author="",
            full_text=f"Article from {source.get('name', '')}: {title}",
        )
        for title, full_url in chosen[:limit]
    ]
