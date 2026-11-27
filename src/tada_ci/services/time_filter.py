from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


# The job runs each weekday at 08:00 America/Chicago, so a 24h window hands off cleanly from
# one run to the next. Monday is the exception: the previous run was Friday morning, leaving
# Friday's own reporting plus the weekend uncovered. 72h puts Monday's cutoff exactly on
# Friday's run time — no gap, and nothing Friday already sent gets re-reported.
#
# The weekday is read in Chicago, not UTC, because that is what the schedule is anchored to.
# They agree at the scheduled hour, but not for a manual run late in the evening: 02:00 UTC
# Monday is still Sunday in Chicago, and should not claim Monday's 72h window.
_SCHEDULE_TZ = ZoneInfo("America/Chicago")
_WINDOW_BY_WEEKDAY = {0: 72}  # Monday → back to Friday's run
_DEFAULT_WINDOW_HOURS = 24


def get_window_hours(hours: int | None = None) -> int:
    """Effective lookback in hours: an explicit value, else today's default."""
    if hours is not None:
        return hours
    weekday = datetime.now(_SCHEDULE_TZ).weekday()
    return _WINDOW_BY_WEEKDAY.get(weekday, _DEFAULT_WINDOW_HOURS)


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
