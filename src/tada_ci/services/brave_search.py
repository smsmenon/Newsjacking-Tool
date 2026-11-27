"""
Thin Brave Search client, used to find competitor news the RSS sources don't carry.

The discovery pipeline reads a fixed list of publications. Competitor tracking needs the
opposite: "anything about Kinaxis in the last 24 hours, wherever it appeared" — press wires,
analyst sites, regional trade press. That is a search problem, not a feed problem.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_SSL_CTX = ssl.create_default_context()

# Brave's own value for "last 24 hours"; pw/pm/py widen to week/month/year.
FRESHNESS_DAY = "pd"

# Brave documents no rate limit for the base plan, so pace conservatively rather than
# discover the ceiling mid-run and lose a day's competitor section to 429s.
_MIN_SECONDS_BETWEEN_CALLS = 1.1
_last_call_at = 0.0


def search(
    query: str,
    *,
    freshness: str | None = FRESHNESS_DAY,
    count: int = 10,
    api_key: str | None = None,
) -> list[dict]:
    """Web results for `query`, newest first. Returns [] rather than raising."""
    global _last_call_at

    api_key = api_key or os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        log.warning("BRAVE_API_KEY not configured — competitor search skipped")
        return []

    params = {"q": query, "count": min(count, 20), "extra_snippets": "true"}
    if freshness:
        params["freshness"] = freshness

    elapsed = time.monotonic() - _last_call_at
    if elapsed < _MIN_SECONDS_BETWEEN_CALLS:
        time.sleep(_MIN_SECONDS_BETWEEN_CALLS - elapsed)
    _last_call_at = time.monotonic()

    request = urllib.request.Request(
        f"{_ENDPOINT}?{urllib.parse.urlencode(params)}",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25, context=_SSL_CTX) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:200]
        log.warning("brave_search %s for %r: %s", exc.code, query[:60], body)
        return []
    except Exception as exc:
        log.warning("brave_search failed for %r: %s", query[:60], exc)
        return []

    results = []
    for item in (payload.get("web") or {}).get("results", []):
        snippets = item.get("extra_snippets") or []
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "extra": " ".join(snippets)[:800],
            # Brave does not document these keys; they appear on some results, so read them
            # defensively rather than relying on them for the freshness guarantee.
            "age": item.get("age") or item.get("page_age") or "",
        })
    return results


def is_configured() -> bool:
    return bool(os.environ.get("BRAVE_API_KEY", ""))
