from __future__ import annotations

import logging
import re
import ssl
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.entities import name2codepoint
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from tada_ci.models import Article

log = logging.getLogger(__name__)

try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
except ImportError:
    _ScraplingFetcher = None

# SSL context that works on macOS without certifi installed
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, "
        "application/xml, text/xml, */*"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Access methods that have a usable RSS feed
_RSS_METHODS = {"rss", "rss_or_scrape", "licensed_api"}


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text


def _child_text(item: ElementTree.Element, names: list[str]) -> str:
    for name in names:
        found = item.find(name)
        if found is not None and found.text:
            return found.text.strip()
    for child in item:
        if child.tag.split("}")[-1] in names and child.text:
            return child.text.strip()
    return ""


def _richest_text(item: ElementTree.Element, names: list[str]) -> str:
    """Longest of the candidate fields, rather than the first one present.

    Publishers often syndicate the whole article in <content:encoded> while <description>
    holds a one-line teaser. Taking the first match meant reading SCMR's 221-character
    summary and ignoring the 10,000-character full text in the same feed entry — then
    trying to scrape the article page for content the feed had already handed us.
    """
    best = ""
    for name in names:
        for found in item.iter():
            if found.tag.split("}")[-1] != name:
                continue
            text = (found.text or "").strip()
            if len(text) > len(best):
                best = text
    return best


def _entry_link(item: ElementTree.Element) -> str:
    link = _child_text(item, ["link"])
    if link:
        return link
    for child in item:
        if child.tag.split("}")[-1] == "link":
            href = child.attrib.get("href")
            if href:
                return href
    return ""


def _entry_date(item: ElementTree.Element) -> str:
    raw = _child_text(item, ["pubDate", "published", "updated", "dc:date"])
    if raw:
        try:
            return (
                parsedate_to_datetime(raw)
                .astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except (TypeError, ValueError):
            return raw
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_wp_rest_articles(source: dict[str, Any], limit: int = 25) -> list[Article]:
    """
    Pull articles from a WordPress REST API instead of a feed or the listing page.

    Inbound Logistics runs WordPress but its RSS feed is empty: its journalism lives in a
    custom `articles` post type, while the homepage also carries `find-solution`, `planner`
    and `whitepaper` entries — which is why scraping it produced "Find Expedited Shipping
    Solutions" instead of news. Asking the API for one post type returns full body text and
    real timestamps, with none of that mixed in.
    """
    import json as _json

    endpoint = source.get("wp_json_url", "")
    if not endpoint:
        return []

    url = f"{endpoint}?per_page={limit}&orderby=date&order=desc"
    raw = ""
    if _ScraplingFetcher is not None:
        try:
            page = _ScraplingFetcher.get(url, timeout=30)
            if getattr(page, "status", 0) == 200:
                raw = str(page.html_content or "")
        except Exception as exc:
            log.debug("wp_rest: scrapling failed for %s: %s", url, exc)
    if not raw:
        with urlopen(Request(url, headers=_HEADERS), timeout=25, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return []
    # Do NOT unescape before parsing: article bodies contain &quot;, and turning those into
    # real quotes breaks the JSON strings they sit inside. _clean_html unescapes per field.
    payload = _json.loads(match.group(0))

    articles: list[Article] = []
    for post in payload:
        title = _clean_html((post.get("title") or {}).get("rendered", ""))
        link = post.get("link", "")
        body = _clean_html((post.get("content") or {}).get("rendered", ""))
        if not title or not link:
            continue
        published = post.get("date_gmt") or post.get("date") or ""
        if published and not published.endswith("Z"):
            published = f"{published}Z"
        articles.append(
            Article(
                title=title,
                source=source["name"],
                category=source["category"],
                url=link,
                publication_date=published,
                author="",
                full_text=body or f"Article from {source['name']}: {title}",
            )
        )
    return articles


_XML_BUILTIN_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}
_NAMED_ENTITY = re.compile(rb"&([A-Za-z][A-Za-z0-9]*);")


def _xml_safe_entities(xml: bytes) -> bytes:
    """Convert HTML named entities to numeric ones so the XML parser accepts them.

    XML defines only five named entities; anything else is a fatal "undefined entity".
    Publishers emit HTML entities in feeds regardless — a single `&nbsp;` in one Modern
    Materials Handling headline aborted the parse for all 500 items in that feed.
    """
    def replace(match: "re.Match[bytes]") -> bytes:
        name = match.group(1).decode("ascii", errors="ignore")
        if name in _XML_BUILTIN_ENTITIES:
            return match.group(0)
        codepoint = name2codepoint.get(name)
        return f"&#{codepoint};".encode() if codepoint else b""

    return _NAMED_ENTITY.sub(replace, xml)


def fetch_rss_articles(
    source: dict[str, Any],
    limit: int = 10,
    timeout: int = 12,
) -> list[Article]:
    rss_url = source.get("rss_url")
    if not rss_url:
        return []

    xml = b""
    # Publishers rate-limit plain urllib: VentureBeat answers it with 429 while serving the
    # same feed normally to a browser-shaped client.
    if _ScraplingFetcher is not None:
        try:
            page = _ScraplingFetcher.get(rss_url, timeout=timeout + 15)
            if getattr(page, "status", 0) == 200:
                xml = page.body or b""
        except Exception as exc:
            log.debug("rss_fetcher: scrapling failed for %s: %s — falling back", rss_url, exc)

    if not xml:
        request = Request(rss_url, headers=_HEADERS)
        with urlopen(request, timeout=timeout, context=_SSL_CTX) as response:
            xml = response.read()

    root = ElementTree.fromstring(_xml_safe_entities(xml))

    # RSS 2.0
    entries = root.findall(".//item")
    # Atom
    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    articles: list[Article] = []
    for item in entries[:limit]:
        title = _clean_html(_child_text(item, ["title"]))
        summary = _clean_html(
            _richest_text(item, ["encoded", "content", "description", "summary"])
        )
        link = _entry_link(item)
        if not title or not link:
            continue
        body = summary or f"Article from {source['name']}: {title}"
        articles.append(
            Article(
                title=title,
                source=source["name"],
                category=source["category"],
                url=link,
                publication_date=_entry_date(item),
                author=_clean_html(_child_text(item, ["author", "creator"])),
                full_text=body,
            )
        )
    return articles


def fetch_live_articles(
    sources: list[dict[str, Any]],
    per_source: int = 25,
    max_articles: int = 250,
) -> tuple[list[Article], list[dict[str, str]]]:
    """
    Fetches from EVERY non-paid source in full first (no early exit) — network/scrape calls
    are cheap, so there's no reason to let list order decide which sources get tried. The
    max_articles cap is applied afterward via round-robin across sources, so it limits total
    volume without letting whichever source happens to come first crowd out the rest. This
    optimizes for coverage/quality within the cap, not for doing the least possible work.

    The caps were 8/80, set when every fetched candidate reached the LLM scorer. They now
    bind long before cost does: a 48h window yielded 80 candidates, of which one cleared the
    bar — while SCMR, the source producing the highest-scoring articles, had 50 items in its
    feed and we read 8. Junk is filtered on keywords and readability before any LLM call, so
    a wider net costs fetch time, not tokens.
    """
    errors: list[dict[str, str]] = []
    per_source_results: list[list[Article]] = []

    for source in sources:
        method = source.get("access_method", "")
        rss_url = source.get("rss_url", "")

        # skip sources explicitly marked as needing a paid API — no scraper fallback for these
        if source.get("health_status") == "requires_api_key":
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": "requires paid API key — skipped",
            })
            continue

        # A WordPress REST endpoint beats both a feed and the listing page: one post type,
        # full body text, real dates.
        if source.get("wp_json_url"):
            try:
                rest = fetch_wp_rest_articles(source, limit=per_source)
                if rest:
                    per_source_results.append(rest)
                    continue
                errors.append({"source": source.get("name", "Unknown"),
                               "error": "wp_json_url returned no articles"})
            except Exception as exc:
                errors.append({"source": source.get("name", "Unknown"),
                               "error": f"wp REST fetch failed: {exc}"})
            continue

        # no RSS feed: fall back to the generic listing-page scraper
        if not rss_url:
            try:
                from tada_ci.services.site_scraper import scrape_listing_page
                scraped = scrape_listing_page(source, limit=per_source)
                if scraped:
                    per_source_results.append(scraped)
                else:
                    errors.append({
                        "source": source.get("name", "Unknown"),
                        "error": "no rss_url, and listing-page scrape returned nothing (likely blocked or no matching links)",
                    })
            except Exception as exc:
                errors.append({
                    "source": source.get("name", "Unknown"),
                    "error": f"listing-page scrape failed: {str(exc)[:100]}",
                })
            continue

        # skip sources whose access method isn't RSS-based
        if not any(m in method for m in ("rss", "licensed_api")):
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": f"access_method '{method}' has no RSS feed",
            })
            continue

        try:
            fetched = fetch_rss_articles(source, limit=per_source)
            if fetched:
                per_source_results.append(fetched)
        except urllib.error.HTTPError as exc:
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": f"HTTP {exc.code} — feed blocked or URL wrong",
            })
        except urllib.error.URLError as exc:
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": f"Network error: {exc.reason}",
            })
        except ElementTree.ParseError:
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": "XML parse error — feed returned non-RSS content",
            })
        except Exception as exc:
            errors.append({
                "source": source.get("name", "Unknown"),
                "error": str(exc)[:120],
            })

    # Round-robin merge: one article from each source per round, so the cap trims evenly
    # across sources instead of favoring whichever source was fetched first.
    articles: list[Article] = []
    round_idx = 0
    while len(articles) < max_articles and any(round_idx < len(lst) for lst in per_source_results):
        for lst in per_source_results:
            if round_idx < len(lst):
                articles.append(lst[round_idx])
                if len(articles) >= max_articles:
                    break
        round_idx += 1

    return articles, errors
