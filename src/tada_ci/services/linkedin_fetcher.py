from __future__ import annotations

import json
import logging
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

log = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

from tada_ci.models import Article

_BASE = "https://linkdapi.com/api/v1"
_API_KEY = os.environ.get("LINKDAPI_KEY", "rnd-Rg_QOKAP_yWja2g-AkBkI6I9qZwj2o3PpgjWpDmgehd-ghVP9Buvb7fMuR-Y47tFpmBVI6-gqnBCi1_uzQXs1MFAbZbMLQ")

_PROFILES_FILE = Path(__file__).resolve().parents[3] / "config" / "linkedin_profiles.json"


def _load_profiles() -> list[dict]:
    try:
        return json.loads(_PROFILES_FILE.read_text())
    except Exception:
        return []

SEARCH_KEYWORDS = [
    "supply chain disruption",
    "manufacturing tariff",
    "procurement strategy",
    "supply chain AI",
    "inventory optimization",
    "logistics disruption",
    "supplier risk",
    "demand planning",
]


_HEADERS = {
    "X-linkdapi-apikey": _API_KEY,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _get(path: str, params: dict[str, Any]) -> dict:
    url = f"{_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers=_HEADERS)
    with urlopen(req, timeout=15, context=_SSL_CTX) as r:
        return json.loads(r.read().decode())


def _ts_to_iso(ts_ms: int) -> str:
    return (
        datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _post_to_article(post: dict, override_author: str = "", override_role: str = "") -> Article | None:
    post_id = post.get("postID", "") or post.get("id", "")
    text = post.get("text", "").strip()
    if not text or len(text) < 60:
        return None

    author = post.get("author", {})
    author_name = override_author or author.get("name", "LinkedIn")
    author_role = override_role or author.get("headline", "")
    post_url = post.get("postURL", "") or post.get("url", "")
    ts = post.get("postedAt", {}).get("timestamp", 0) or post.get("timestamp", 0)
    pub_date = (
        _ts_to_iso(ts) if ts
        else datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    engagements = post.get("engagements", {})
    reactions = engagements.get("totalReactions", 0)
    comments = engagements.get("commentsCount", 0)
    reposts = engagements.get("repostsCount", 0)

    title = text[:120].replace("\n", " ").strip()
    if len(text) > 120:
        title = title[:117] + "..."

    full_text = (
        f"{text}\n\n"
        f"[LinkedIn post by {author_name} — {author_role}] "
        f"Reactions: {reactions} | Comments: {comments} | Reposts: {reposts}"
    )

    return Article(
        title=title,
        source=f"LinkedIn / {author_name}",
        category="LinkedIn Intelligence",
        url=post_url,
        publication_date=pub_date,
        author=f"{author_name} — {author_role}",
        full_text=full_text,
    )


def fetch_profile_posts(
    profiles: list[dict] | None = None,
    per_profile: int = 5,
    max_posts: int = 30,
) -> tuple[list[Article], list[dict]]:
    """Fetch recent posts from specific LinkedIn thought-leader profiles."""
    if profiles is None:
        profiles = _load_profiles()

    articles: list[Article] = []
    errors: list[dict] = []
    seen: set[str] = set()

    for profile in profiles:
        if len(articles) >= max_posts:
            break
        username = profile.get("username", "")
        name = profile.get("name", username)
        role = profile.get("role", "")
        if not username:
            continue
        try:
            resp = _get("/profile/posts", {"username": username, "count": per_profile})
            if not resp.get("success"):
                errors.append({"source": f"LinkedIn/{username}", "error": resp.get("message", "unknown")})
                continue

            posts = resp.get("data", {}).get("posts", []) or resp.get("data", [])
            for post in posts:
                post_id = post.get("postID", "") or post.get("id", "")
                if post_id and post_id in seen:
                    continue
                if post_id:
                    seen.add(post_id)
                art = _post_to_article(post, override_author=name, override_role=role)
                if art:
                    articles.append(art)

        except Exception as exc:
            errors.append({"source": f"LinkedIn/{username}", "error": str(exc)[:120]})
            log.debug("linkedin profile fetch failed for %s: %s", username, exc)

    return articles[:max_posts], errors


def fetch_linkedin_posts(
    keywords: list[str] | None = None,
    per_keyword: int = 5,
    max_posts: int = 30,
) -> tuple[list[Article], list[dict]]:
    if keywords is None:
        keywords = SEARCH_KEYWORDS

    articles: list[Article] = []
    errors: list[dict] = []
    seen: set[str] = set()

    for keyword in keywords:
        if len(articles) >= max_posts:
            break
        try:
            resp = _get("/search/posts", {"keyword": keyword, "count": per_keyword})
            if not resp.get("success"):
                errors.append({"source": "LinkedIn", "keyword": keyword, "error": resp.get("message", "unknown")})
                continue

            posts = resp.get("data", {}).get("posts", [])
            for post in posts:
                post_id = post.get("postID", "")
                if not post_id or post_id in seen:
                    continue
                seen.add(post_id)
                art = _post_to_article(post)
                if art:
                    articles.append(art)

        except Exception as exc:
            errors.append({"source": "LinkedIn", "keyword": keyword, "error": str(exc)[:120]})

    # Also fetch from configured thought-leader profiles
    profile_articles, profile_errors = fetch_profile_posts(per_profile=3, max_posts=20)
    errors.extend(profile_errors)

    # Merge, dedup by URL
    seen_urls = {a.url for a in articles if a.url}
    for a in profile_articles:
        if a.url not in seen_urls:
            articles.append(a)
            seen_urls.add(a.url)

    return articles[:max_posts + 20], errors
