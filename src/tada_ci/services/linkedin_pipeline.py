"""
LinkedIn discovery pipeline via LinkdAPI (linkdapi.com) — fetches posts from named profiles
and theme-keyword search, tiers by engagement, and qualifies with the same
theme-valid + thought-leadership + can-contradict standard used for website articles
(see contrarian_pipeline.check_source_criteria / config/reference_docs).

Tiering (engagement-based, not the news-relevance bar — see session history: LinkedIn
thought-leadership content is exactly what relevance_scorer.py's news-worthiness rubric is
built to reject, since it requires a data-backed event, not opinion):
  Tier 1: 15+ comments  -> full contrarian POV, meant to be reposted with our own commentary
  Tier 2: 5-10 comments -> "note to monitor" only, not a full POV — too early to commit to
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
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_BASE_URL = "https://linkdapi.com"
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Hard ceiling on LinkdAPI requests per run. A normal sweep (11 profiles + 28 keywords,
# with urns cached) costs ~39, so this leaves headroom for retries without letting one run
# empty the key.
MAX_CALLS_PER_RUN = 100
_calls_this_run = 0


def reset_call_budget() -> None:
    """Start a fresh budget. Called at the top of each pipeline run."""
    global _calls_this_run
    _calls_this_run = 0


def calls_used() -> int:
    return _calls_this_run


TIER1_MIN_COMMENTS = 15
TIER2_MIN_COMMENTS = 5
# No upper bound: the tiers are separated by age, so a same-day post can never reach Tier 1
# however popular it gets. A ceiling here only discarded the day's fastest-growing posts —
# exactly the live conversations worth joining.

# The two tiers are a maturity split, not just a volume one: a post needs days on the
# platform before its comment count means anything. Tier 1 is "old enough to have gathered a
# real discussion", Tier 2 is "posted recently and still climbing" — judging both over the
# same window (as an earlier 48h change did) collapses that distinction.
TIER1_MIN_AGE_HOURS = 72   # 3 days — below this, a low count may just mean "posted today"
TIER1_MAX_AGE_HOURS = 168  # 7 days — past this the conversation is over; too late to join


def _call(path: str, params: dict, api_key: str, retries: int = 2) -> dict:
    """One LinkdAPI request, subject to the per-run call budget.

    Credits are the scarce resource here — a trial key carries ~100 and a full sweep spends
    ~39, so an unbounded run (a long profile list, or retries on a bad day) can drain a key
    in one go and leave the next day's digest with nothing.
    """
    global _calls_this_run
    if _calls_this_run >= MAX_CALLS_PER_RUN:
        raise RuntimeError(
            f"LinkdAPI call budget exhausted ({MAX_CALLS_PER_RUN} per run) — "
            "skipping the rest to preserve credits"
        )
    _calls_this_run += 1

    url = f"{_BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"X-linkdapi-apikey": api_key, "User-Agent": _UA, "Accept": "application/json"}
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=25, context=_SSL_CTX) as r:
                body = json.loads(r.read())
            if body.get("data") is None:
                # LinkdAPI soft-failure: HTTP 200 with data:null under load, no HTTPError raised.
                last_exc = RuntimeError(f"empty data in response: {body.get('message', body)}")
                if attempt < retries:
                    time.sleep(5)
                    continue
                raise last_exc
            return body
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < retries:
                time.sleep(15)
                continue
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(3)
                continue
    raise last_exc


def _urn_cache_path(root: Path) -> Path:
    return root / "data" / "linkedin_urns.json"


def _load_urn_cache(root: Path) -> dict:
    """username -> urn. A member's urn is permanent, so re-resolving it every run spends a
    credit to learn something that cannot have changed."""
    try:
        p = _urn_cache_path(root)
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception as exc:
        log.debug("could not read urn cache: %s", exc)
        return {}


def _save_urn_cache(root: Path, cache: dict) -> None:
    try:
        p = _urn_cache_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, indent=2, sort_keys=True))
    except Exception as exc:
        log.debug("could not write urn cache: %s", exc)


def _load_profiles(root: Path) -> list[dict]:
    p = root / "config" / "linkedin_profiles.json"
    return json.loads(p.read_text()) if p.exists() else []


def _load_keywords(root: Path) -> list[str]:
    p = root / "config" / "linkedin_keywords.json"
    return json.loads(p.read_text()) if p.exists() else []


def fetch_all_posts(root: Path, api_key: str | None = None) -> tuple[list[dict], list[str]]:
    """
    Fetch posts from every configured profile + every configured keyword search.
    Returns (posts, errors). A credit-exhausted or otherwise failing keyword just gets
    skipped and logged — one bad keyword shouldn't abort the whole fetch.
    """
    api_key = api_key or os.environ.get("LINKDAPI_API_KEY", "")
    if not api_key:
        return [], ["LINKDAPI_API_KEY not configured"]

    errors: list[str] = []
    all_posts: list[dict] = []

    urn_cache = _load_urn_cache(root)
    cache_dirty = False

    for prof in _load_profiles(root):
        username = prof.get("username", "")
        if not username:
            continue
        try:
            cached = urn_cache.get(username) or {}
            urn = cached.get("urn")
            name = cached.get("name") or prof.get("name") or username
            if not urn:
                overview = _call("/api/v1/profile/overview", {"username": username}, api_key)
                urn = overview["data"]["urn"]
                name = overview["data"].get("fullName", username) or name
                urn_cache[username] = {"urn": urn, "name": name}
                cache_dirty = True
                time.sleep(3)

            posts = _call("/api/v1/posts/all", {"urn": urn, "start": 0}, api_key)["data"]["posts"]
            for p in posts:
                p["_profile"] = name
            all_posts.extend(posts)
        except Exception as exc:
            errors.append(f"profile '{username}': {exc}")
            log.debug("linkedin_pipeline profile fetch failed for %s: %s", username, exc)
        time.sleep(3)

    if cache_dirty:
        _save_urn_cache(root, urn_cache)

    for kw in _load_keywords(root):
        try:
            res = _call(
                "/api/v1/search/posts",
                {"keyword": kw, "datePosted": "past-week", "sortBy": "date_posted"},
                api_key,
            )
            posts = res.get("data", {}).get("posts", [])
            for p in posts:
                p["_profile"] = f"SEARCH:{kw}"
            all_posts.extend(posts)
        except Exception as exc:
            errors.append(f"keyword '{kw}': {exc}")
            log.debug("linkedin_pipeline search failed for '%s': %s", kw, exc)
        time.sleep(4)

    return all_posts, errors


# LinkdAPI does not publish a response schema, and reading a single wrong key here is
# catastrophically quiet: `.get(..., 0)` turns a renamed field into "0 comments, posted in
# 1970", so every post is discarded and the run looks like a slow news day. One confirmed
# symptom: 692 posts fetched, 0 tiered. Accept the plausible spellings, and when none match,
# say so loudly with the keys the API actually sent.
_ID_PATHS = (("urn",), ("postUrn",), ("activityUrn",), ("id",), ("postId",), ("shareUrn",))
_TIMESTAMP_PATHS = (
    ("postedAt", "timestamp"), ("postedAt", "date"), ("postedAt", "epoch"),
    ("postedDate",), ("publishedAt",), ("createdAt",), ("timestamp",), ("time",), ("date",),
)
_COMMENT_PATHS = (
    ("engagements", "commentsCount"), ("engagements", "comments"),
    ("engagement", "commentsCount"), ("socialCounts", "numComments"),
    ("stats", "commentCount"), ("commentsCount",), ("commentCount",), ("numComments",),
)


def _dig(post: dict, paths: tuple) -> Any:
    """First value found at any of these key paths, or None."""
    for path in paths:
        value: Any = post
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_epoch_ms(value: Any) -> int | None:
    """Normalise a timestamp to epoch milliseconds, whatever shape it arrived in."""
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        number = float(value)
        if number > 1e11:        # already milliseconds
            return int(number)
        if number > 1e8:         # seconds
            return int(number * 1000)
        return None              # too small to be a real date
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        for parse in (
            lambda t: datetime.fromisoformat(t),
            lambda t: parsedate_to_datetime(t),
        ):
            try:
                dt = parse(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except Exception:
                continue
    return None


def _comment_count(post: dict) -> int | None:
    value = _dig(post, _COMMENT_PATHS)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def tier_posts(posts: list[dict], hours_window: int) -> tuple[list[dict], list[dict]]:
    """Dedup by id, filter to hours_window, split into Tier 1 / Tier 2 by comment count."""
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - hours_window * 3600 * 1000

    seen: set[str] = set()
    tier1: list[dict] = []
    tier2: list[dict] = []
    counts = {"no_id": 0, "no_timestamp": 0, "no_comments": 0, "out_of_window": 0}
    sample_keys: list[str] = []

    for index, p in enumerate(posts):
        if not isinstance(p, dict):
            continue
        post_id = _dig(p, _ID_PATHS) or f"_index_{index}"
        if _dig(p, _ID_PATHS) is None:
            counts["no_id"] += 1
        if post_id in seen:
            continue
        seen.add(post_id)

        ts = _as_epoch_ms(_dig(p, _TIMESTAMP_PATHS))
        if ts is None:
            # Unknown date: keep it rather than silently discarding every post, and treat it
            # as recent so it can still reach Tier 2. The warning below makes the gap visible.
            counts["no_timestamp"] += 1
            age_hours = 0.0
        else:
            age_hours = (now_ms - ts) / 3_600_000

        comments = _comment_count(p)
        if comments is None:
            counts["no_comments"] += 1
            if not sample_keys:
                sample_keys = sorted(p.keys())
            continue

        # The two bands must meet exactly. Tying Tier 2 to the caller's hours_window instead
        # left everything between that window and TIER1_MIN_AGE_HOURS unreachable — a 24h
        # run silently discarded every post aged 24-72h, however busy its comments were.
        # LinkedIn maturity is its own clock and shouldn't inherit the website's window.
        mature = TIER1_MIN_AGE_HOURS <= age_hours <= TIER1_MAX_AGE_HOURS
        recent = age_hours < TIER1_MIN_AGE_HOURS

        if mature and comments >= TIER1_MIN_COMMENTS:
            tier1.append(p)
        elif recent and comments >= TIER2_MIN_COMMENTS:
            tier2.append(p)
        elif age_hours > TIER1_MAX_AGE_HOURS:
            counts["out_of_window"] += 1

    if posts and counts["no_comments"] == len(seen):
        log.warning(
            "tier_posts: no comment count found on ANY of %d posts — LinkdAPI field names "
            "have probably changed. Keys on a sample post: %s",
            len(seen), sample_keys,
        )
    elif counts["no_comments"] or counts["no_timestamp"] or counts["no_id"]:
        log.info("tier_posts: %d posts — unreadable id:%d date:%d comments:%d, out of window:%d",
                 len(seen), counts["no_id"], counts["no_timestamp"],
                 counts["no_comments"], counts["out_of_window"])

    tier1.sort(key=lambda p: _comment_count(p) or 0, reverse=True)
    tier2.sort(key=lambda p: _comment_count(p) or 0, reverse=True)
    log.info("tier_posts: %d unique posts -> tier1 %d, tier2 %d", len(seen), len(tier1), len(tier2))
    return tier1, tier2


def qualify_post(post: dict, reference_docs: str) -> dict:
    """
    Same standard as website articles: theme-valid + is-thought-leadership + can-contradict.
    Not relevance_scorer.py's news-worthiness bar — that explicitly excludes opinion/thought
    leadership, which is exactly what LinkedIn content is.
    """
    from .contrarian_pipeline import _claude

    author = (post.get("author") or {}).get("name", "")
    text = post.get("text", "")[:1500]

    prompt = f"""You are screening LinkedIn content for TADA, a supply chain intelligence platform.

TADA REFERENCE MATERIAL:
{reference_docs[:15000]}

CANDIDATE POST by {author}:
{text}

Answer:
1. THEME_VALID: Does this touch a real TADA theme? true/false

2. IS_THOUGHT_LEADERSHIP: Is the post's PURPOSE to argue a point? true/false
   Answer false if its purpose is to promote or announce anything, even when it is wrapped
   in commentary and cites real data. Specifically false for:
   - product/platform launches, partnership or acquisition announcements, funding news
   - promoting a report, whitepaper, webinar, podcast, newsletter or event
     (a download link, "register here", or a sponsor tag is a giveaway)
   - conference recaps, award wins, hiring posts, personal tributes or milestones
   A post can quote credible statistics and still be an advertisement. Ask what the post
   wants the reader to DO: if it is "download / register / congratulate us", answer false.

3. CAN_CONTRADICT: Does TADA have a sharper diagnosis than this post's central claim? true/false
   TRUE when TADA would say the author has the right observation but the wrong layer, wrong
   cause, or wrong fix. That is the normal case and it IS a contradiction — for example:
   - post prescribes governance/org design for AI agents -> TADA: governance is downstream,
     the agents have no live model of the operation to reason against (true)
   - post says forecasts need improving -> TADA: forecast quality is not the constraint,
     execution latency is (true)
   - post recommends LLMs for planning decisions -> TADA: probabilistic is the wrong
     architecture for constraint problems (true)
   FALSE only when the post already reaches TADA's own conclusion, so the POV would simply
   restate the author in TADA's vocabulary — for example a post whose own thesis is "the
   operating model is the problem, not the technology", or "automating a broken process
   entrenches it". If our reply would begin by agreeing and add no different diagnosis,
   answer false.

Respond with ONLY:
THEME_VALID: [true/false]
IS_THOUGHT_LEADERSHIP: [true/false]
CAN_CONTRADICT: [true/false]
CONTRADICTION: [one sentence naming what TADA disagrees with, or NONE]"""

    try:
        raw = _claude(prompt, max_tokens=200)
    except Exception as exc:
        log.debug("qualify_post error: %s", exc)
        return {"passed": False, "contradiction": "", "error": str(exc)}

    result = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()

    passed = (
        result.get("THEME_VALID", "").lower() == "true"
        and result.get("IS_THOUGHT_LEADERSHIP", "").lower() == "true"
        and result.get("CAN_CONTRADICT", "").lower() == "true"
    )
    return {"passed": passed, "contradiction": result.get("CONTRADICTION", "")}


def group_by_argument(posts: list[dict]) -> list[dict]:
    """
    Cluster qualifying posts by the argument they make, returning groups of indices.

    Posts are deduped by id only, so a week where several people (or one person repeatedly)
    push the same idea produced several near-identical entries and a POV restated almost
    verbatim each time — three "agents can execute but cannot be accountable" posts all drew
    the same "build the live operational model" response. Grouping also turns that repetition
    into the more useful signal: a claim several voices are converging on.
    """
    def solo(indices: list[int]) -> list[dict]:
        return [{"members": [i], "label": _first_line(posts[i])} for i in indices]

    if len(posts) < 2:
        return solo(list(range(len(posts))))

    from .contrarian_pipeline import _claude

    listing = "\n\n".join(
        f"[{i}] {(p.get('text') or '')[:400]}" for i, p in enumerate(posts)
    )
    prompt = f"""Group these LinkedIn posts by the ARGUMENT they make — not by author, topic
area, or keyword. Two posts belong together only if responding to one would answer both.

{listing}

Return one line per group, nothing else:
GROUP: <comma-separated indices> | <a specific one-line description of the shared argument,
max 12 words, no author names>

Every index must appear exactly once. A post that shares no argument forms its own group."""

    try:
        raw = _claude(prompt, max_tokens=600)
    except Exception as exc:
        log.debug("group_by_argument failed: %s — treating every post separately", exc)
        return solo(list(range(len(posts))))

    groups: list[dict] = []
    claimed: set[int] = set()
    for line in raw.splitlines():
        if "GROUP:" not in line:
            continue
        body = line.split("GROUP:", 1)[1]
        index_part, _, label = body.partition("|")
        members = []
        for token in index_part.replace("[", " ").replace("]", " ").split(","):
            token = token.strip()
            if token.isdigit():
                idx = int(token)
                if 0 <= idx < len(posts) and idx not in claimed:
                    claimed.add(idx)
                    members.append(idx)
        if members:
            groups.append({
                "members": members,
                "label": label.strip() or _first_line(posts[members[0]]),
            })

    # Anything the model dropped still has to reach the digest.
    groups.extend(solo([i for i in range(len(posts)) if i not in claimed]))
    return groups


def _first_line(post: dict) -> str:
    """Fallback label: a post's opening line is almost always its hook."""
    text = (post.get("text") or "").strip()
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 15:
            return line[:120]
    return text[:120] or "LinkedIn post"


def run_linkedin_pipeline(root: Path, hours_window: int = 24) -> dict[str, Any]:
    """
    Full LinkedIn discovery run: fetch -> tier -> qualify -> POV (tier1) / monitor note (tier2).
    Returns {"tier1": [...], "tier2": [...], "errors": [...]}.
    """
    from .contrarian_pipeline import generate_pov_for_article, _load_reference_docs

    reset_call_budget()
    posts, errors = fetch_all_posts(root)
    log.info("linkedin: %d/%d LinkdAPI calls used fetching", calls_used(), MAX_CALLS_PER_RUN)
    tier1_raw, tier2_raw = tier_posts(posts, hours_window)
    ref_docs = _load_reference_docs(root)

    qualified: list[dict] = []
    for tier, candidates in (("tier1", tier1_raw), ("tier2", tier2_raw)):
        for p in candidates:
            q = qualify_post(p, ref_docs)
            if q["passed"]:
                qualified.append({"post": p, "tier": tier, "contradiction": q["contradiction"]})

    # One POV per argument, not per post: the POV is written against the shared claim, which
    # is a stronger position than replying to one author when several are saying the same thing.
    groups_out: list[dict] = []
    for group in group_by_argument([item["post"] for item in qualified]):
        members = [qualified[i] for i in group["members"]]
        members.sort(key=lambda m: _comment_count(m["post"]) or 0, reverse=True)
        primary = members[0]["post"]

        shared_text = "\n\n---\n\n".join((m["post"].get("text") or "")[:900] for m in members)
        if len(members) > 1:
            shared_text = (
                f"{len(members)} separate LinkedIn posts this week make the same argument. "
                f"Write TADA's POV against the shared claim, not against one author.\n\n{shared_text}"
            )
        pov = generate_pov_for_article({"title": group["label"], "content": shared_text}, ref_docs)

        groups_out.append({
            "label": group["label"],
            "pov": pov,
            "posts": [m["post"] for m in members],
            "primary": primary,
            "tier": members[0]["tier"],
            "post_count": len(members),
            "total_comments": sum(_comment_count(m["post"]) or 0 for m in members),
        })

    groups_out.sort(key=lambda g: g["total_comments"], reverse=True)

    tier1_out = [{"post": g["primary"], "pov": g["pov"]} for g in groups_out if g["tier"] == "tier1"]
    tier2_out = [{"post": g["primary"], "pov": g["pov"]} for g in groups_out if g["tier"] == "tier2"]
    _record_yield(root, posts, tier1_raw + tier2_raw, qualified)

    log.info("linkedin: %d qualifying posts -> %d argument group(s)", len(qualified), len(groups_out))
    return {
        "groups": groups_out,
        "tier1": tier1_out,
        "tier2": tier2_out,
        "errors": errors,
        "total_fetched": len(posts),
        "api_calls_used": calls_used(),
    }


def _record_yield(root: Path, fetched: list, tiered: list, qualified: list) -> None:
    """
    Track what each keyword and profile actually produced, accumulated across runs.

    Keyword choice is otherwise guesswork: a term that reads well can return nothing but
    vendor marketing, and there is no way to tell from the config file. This makes the
    per-term payoff visible so the list can be pruned on evidence.
    """
    def origin(post: dict) -> str:
        return post.get("_profile") or "unknown"

    try:
        path = root / "data" / "linkedin_keyword_yield.json"
        totals = json.loads(path.read_text()) if path.exists() else {}

        tiered_ids = {id(p) for p in tiered}
        qualified_ids = {id(item.get("post")) for item in qualified}

        for post in fetched:
            row = totals.setdefault(origin(post), {"runs": 0, "fetched": 0, "tiered": 0, "qualified": 0})
            row["fetched"] += 1
            if id(post) in tiered_ids:
                row["tiered"] += 1
            if id(post) in qualified_ids:
                row["qualified"] += 1

        seen_origins = {origin(p) for p in fetched}
        for name in seen_origins:
            totals[name]["runs"] += 1

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(totals, indent=2, sort_keys=True))

        barren = sorted(n for n, r in totals.items() if r["runs"] >= 5 and r["qualified"] == 0)
        if barren:
            log.info("linkedin yield: %d source(s) with 0 qualifying posts over 5+ runs — "
                     "candidates to drop: %s", len(barren), ", ".join(barren[:10]))
    except Exception as exc:
        log.debug("could not record keyword yield: %s", exc)
