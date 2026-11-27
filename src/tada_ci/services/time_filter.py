from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

log = logging.getLogger(__name__)


# The job runs every morning, so a 24h window hands off cleanly from one run to the next.
# (It previously ran weekdays only, and Monday used 72h to cover Friday's reporting plus the
# weekend. Daily runs cover those themselves, so that exception is gone — keeping it would
# re-trawl what Saturday and Sunday already sent.)
_DEFAULT_WINDOW_HOURS = 24


def get_window_hours(hours: int | None = None) -> int:
    """Effective lookback in hours: an explicit value, else the daily default."""
    return _DEFAULT_WINDOW_HOURS if hours is None else hours


def get_cutoff_datetime(hours: int | None = None) -> datetime:
    """Cutoff for freshness. `hours` overrides the weekday-aware default window."""
    return datetime.now(timezone.utc) - timedelta(hours=get_window_hours(hours))


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y",  # some feeds (seen from McKinsey) omit the time entirely
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    return None


def is_article_fresh(publication_date_str: str, hours: int | None = None) -> bool:
    dt = _parse_date(publication_date_str)
    if dt is None:
        # No date at all (e.g. scraped listing-page sources that don't expose a publish date)
        # or a genuinely unparseable one. Excluding these outright was silently discarding
        # 100% of scraped-source content before it ever reached keyword/relevance filtering —
        # let those downstream quality gates decide instead of dropping it here on a guess.
        return True
    cutoff = get_cutoff_datetime(hours)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def filter_fresh_articles(articles: list, hours: int | None = None) -> list:
    cutoff = get_cutoff_datetime(hours)
    fresh, stale = [], []
    for a in articles:
        pub = getattr(a, "published_at", None) or (a.get("published_at") if isinstance(a, dict) else None)
        if is_article_fresh(pub or "", hours):
            fresh.append(a)
        else:
            stale.append(a)
    log.info("Time filter: %d fresh, %d stale (cutoff %s)", len(fresh), len(stale), cutoff.isoformat())
    return fresh
