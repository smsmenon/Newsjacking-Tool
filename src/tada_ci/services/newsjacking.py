"""
"Newsjacking Articles" — the daily combined website + LinkedIn discovery run, emailed via
Resend. Meant to be invoked once a day by an external scheduler (Windows Task Scheduler),
not by a live Claude session — see run_newsjacking.py for the CLI entry point.
"""

from __future__ import annotations

import json
import logging
import os
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .competitor_watch import record_seen as record_competitors_seen, run_competitor_watch
from .discovery_pipeline import load_sent_urls, record_sent_urls, run_discovery_pipeline
from .run_log import write_run_log
from .discovery_emailer import format_month_day_year
from .linkedin_pipeline import run_linkedin_pipeline
from .time_filter import get_window_hours

log = logging.getLogger(__name__)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _post_url(item: dict) -> str:
    """Stable identity for a LinkedIn post. Falls back to the urn so posts without a
    resolved permalink still dedupe against each other instead of colliding on a shared
    placeholder."""
    post = item.get("post") or item
    return post.get("url") or post.get("postURL") or post.get("urn") or ""


def _post_link(post: dict | None) -> str:
    """Clickable permalink. Some posts arrive with an empty url but a valid urn (seen on
    keyword-search results), which rendered a dead '#' link — rebuild it from the urn."""
    if not post:
        return "#"
    url = post.get("url") or post.get("postURL")
    if url:
        return url
    urn = post.get("urn")
    return f"https://www.linkedin.com/feed/update/{urn}" if urn else "#"


COMPETITOR_EMPTY_LINE = "No major competitor updates today."

_TITLE_JUNK = re.compile(
    r"\s*(learn more|read more|read the full (story|article)|click here|view all|continue reading)\s*$",
    re.I,
)


def _clean_title(title: str) -> str:
    """Drop call-to-action text that scraping glues onto a headline.

    Listing pages put the link label inside the same anchor as the headline, producing
    titles like "...Iraq Is Back in the Container Shipping Business Learn More".
    """
    cleaned = (title or "").strip()
    for _ in range(3):  # a couple of these can stack
        new = _TITLE_JUNK.sub("", cleaned).strip(" -–—|·")
        if new == cleaned:
            break
        cleaned = new
    return cleaned or title


def build_group_title(article: dict) -> str:
    """One headline covering every outlet's version of a grouped story.

    The primary outlet's own headline frames the story its way, which reads oddly when two
    mastheads are listed beside it; this states the shared event once.
    """
    coverage = [c for c in (article.get("coverage") or []) if c.get("title")]
    if not coverage:
        return ""
    try:
        from .contrarian_pipeline import _claude

        headlines = "\n".join(
            f"- {h}" for h in [article.get("title", "")] + [c["title"] for c in coverage]
        )
        raw = _claude(
            "These headlines all cover the same story. Write ONE neutral headline, under 14 "
            "words, that states what happened. No outlet names, no preamble, no quotes — "
            f"return the headline only.\n\n{headlines}",
            max_tokens=60,
        )
        return _clean_title(raw.strip().strip('"'))
    except Exception as exc:
        log.debug("build_group_title failed: %s — using the primary headline", exc)
        return ""


def _build_html(website_articles: list[dict], linkedin_groups: list[dict],
                competitor_items: list[dict] | None = None) -> str:
    def website_block(a: dict, index: int) -> str:
        # A grouped story gets a title covering both pieces; a single one keeps its headline.
        title = _clean_title(a.get("group_title") or a.get("title", "Untitled"))
        pov = a.get("tada_pov", "")
        gate = a.get("source_gate", {})
        flag = "" if gate.get("pass") and not gate.get("overridden") else \
            '<p style="margin:0 0 6px;font-size:11px;color:#b45309;">⚠ fallback pick — no article fully cleared TADA\'s criteria today</p>'

        # Each outlet links to its own version. The names are the point here, unlike
        # LinkedIn: breadth of pickup is a signal, and the reader may want a particular
        # outlet's write-up rather than whichever one happened to score highest.
        outlets = [{"source": a.get("source", ""), "url": a.get("url", "#")}]
        outlets += [c for c in (a.get("coverage") or []) if c.get("url")]
        links = " &nbsp;·&nbsp; ".join(
            f'<a href="{o["url"]}" style="color:#475569;text-decoration:underline;">{o.get("source") or "link"}</a>'
            for o in outlets
        )
        label = "Covered by" if len(outlets) > 1 else "Source:"

        return f"""
        <div style="margin-bottom:26px;padding-bottom:26px;border-bottom:1px solid #e2e8f0;">
          <p style="margin:0 0 6px;font-size:15px;font-weight:600;color:#0f172a;line-height:1.4;">{index}. {title}</p>
          <p style="margin:0 0 8px;font-size:12px;color:#94a3b8;">{label} {links}</p>
          {flag}
          <p style="margin:0;font-size:13px;color:#475569;line-height:1.6;"><strong>TADA's POV:</strong> {pov}</p>
        </div>"""

    def linkedin_block(group: dict, index: int) -> str:
        # Several posts can share one argument: the label describes the shared claim, the POV
        # answers it once, and every version is linked. Authors stay anonymous by design.
        posts = group.get("posts") or [group.get("primary")]
        count = len(posts)
        links = " &nbsp;·&nbsp; ".join(
            f'<a href="{_post_link(p)}" style="color:#475569;text-decoration:underline;">Post {i}</a>'
            for i, p in enumerate(posts, start=1)
        )
        label = f"Raised in {count} posts:" if count > 1 else "Post:"

        return f"""
        <div style="margin-bottom:26px;padding-bottom:26px;border-bottom:1px solid #e2e8f0;">
          <p style="margin:0 0 6px;font-size:15px;font-weight:600;color:#0f172a;line-height:1.4;">{index}. {_clean_title(group.get('label','LinkedIn post'))}</p>
          <p style="margin:0 0 8px;font-size:12px;color:#94a3b8;">{label} {links}</p>
          <p style="margin:0;font-size:13px;color:#475569;line-height:1.6;"><strong>TADA's POV:</strong> {group.get('pov','')}</p>
        </div>"""

    def competitor_block(item: dict, index: int) -> str:
        flag = ('<span style="color:#b45309;" title="Claims something TADA also claims">⚠️ </span>'
                if item.get("overlap") else "")
        date = (item.get("published_at") or "")[:10]
        meta = " · ".join(part for part in (item.get("competitor", ""), date) if part)
        angle = item.get("angle") or ""
        angle_html = (f'<p style="margin:6px 0 0;font-size:13px;color:#475569;line-height:1.6;">'
                      f'<strong>Content angle:</strong> {angle}</p>') if angle else ""
        return f"""
        <div style="margin-bottom:26px;padding-bottom:26px;border-bottom:1px solid #e2e8f0;">
          <p style="margin:0 0 6px;font-size:15px;font-weight:600;color:#0f172a;line-height:1.4;">{index}. {flag}{item.get('what','')}</p>
          <p style="margin:0 0 8px;font-size:12px;color:#94a3b8;">{meta} &nbsp;·&nbsp; <a href="{item.get('url','#')}" style="color:#475569;text-decoration:underline;">Source</a></p>
          <p style="margin:0;font-size:13px;color:#475569;line-height:1.6;"><strong>Why it matters:</strong> {item.get('why','')}</p>
          {angle_html}
        </div>"""

    # Busiest conversation first — that is the strongest repost target.
    groups = sorted(linkedin_groups, key=lambda g: g.get("total_comments", 0), reverse=True)
    website_html = "".join(website_block(a, i) for i, a in enumerate(website_articles, start=1)) or "<p style='font-size:13px;color:#94a3b8;'>No website articles cleared today.</p>"
    linkedin_html = "".join(linkedin_block(g, i) for i, g in enumerate(groups, start=1)) or "<p style='font-size:13px;color:#94a3b8;'>No LinkedIn posts cleared today.</p>"
    # One flat line when nothing qualifies — the section is not padded.
    competitor_html = "".join(
        competitor_block(c, i) for i, c in enumerate(competitor_items or [], start=1)
    ) or f"<p style='font-size:13px;color:#94a3b8;'>{COMPETITOR_EMPTY_LINE}</p>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:32px 16px;">
    <div style="background:#ffffff;border-radius:8px;padding:32px;border:1px solid #e2e8f0;">
      <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;">Newsjacking Articles</p>
      <p style="margin:0 0 28px;font-size:20px;font-weight:700;color:#0f172a;">Today's Website + LinkedIn Picks</p>

      <p style="margin:0 0 8px;font-size:15px;font-weight:700;color:#0f172a;">Website Articles</p>
      {website_html}

      <p style="margin:20px 0 8px;font-size:15px;font-weight:700;color:#0f172a;">LinkedIn Posts</p>
      {linkedin_html}

      <p style="margin:20px 0 8px;font-size:15px;font-weight:700;color:#0f172a;">Competitor Updates</p>
      {competitor_html}
    </div>
  </div>
</body></html>"""


def _send_via_resend(subject: str, html_body: str, to_email: str) -> dict[str, Any]:
    # A dry run still collects, scores and writes the run log — useful for checking which
    # sources survive a move to new infrastructure without mailing anyone the result.
    if os.environ.get("SEND_EMAIL", "true").strip().lower() in ("false", "0", "no"):
        log.info("SEND_EMAIL is off — digest built and logged, not sent")
        return {"success": False, "skipped": True, "reason": "SEND_EMAIL disabled"}

    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        return {"success": False, "error": "RESEND_API_KEY not configured"}
    from_addr = os.environ.get("RESEND_FROM", "onboarding@resend.dev")

    payload = json.dumps({
        "from": f"Newsjacking Articles <{from_addr}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "newsjacking-articles/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
        return {"success": True, "id": data.get("id")}
    except urllib.error.HTTPError as exc:
        return {"success": False, "error": f"Resend {exc.code}: {exc.read().decode(errors='replace')}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_newsjacking(root: Path, to_email: str, hours_window: int | None = None) -> dict[str, Any]:
    """The full daily job: run both pipelines, build the email, send it via Resend.

    `hours_window` defaults to the weekday-aware window (72h on Monday so it reaches back to
    Friday's run, 24h otherwise). It is resolved to a concrete number here so the website and
    LinkedIn halves always cover the same period.
    """
    hours_window = get_window_hours(hours_window)
    website_result = run_discovery_pipeline(root=root, hours_window=hours_window)
    linkedin_result = run_linkedin_pipeline(root=root, hours_window=hours_window)

    # The website pipeline already drops previously-emailed URLs internally; LinkedIn posts
    # are filtered here so a post that stays highly-commented for days isn't resent nightly.
    already_sent = load_sent_urls(root)
    website_articles = website_result.get("top_articles", [])

    # Drop posts already sent, then drop any group left with nothing to show.
    groups = []
    for group in linkedin_result.get("groups", []):
        unsent = [p for p in group.get("posts", []) if _post_url(p) not in already_sent]
        if not unsent:
            continue
        groups.append({**group, "posts": unsent, "primary": unsent[0],
                       "total_comments": sum((p.get("engagements") or {}).get("commentsCount", 0)
                                             for p in unsent)})

    for article in website_articles:
        if article.get("coverage"):
            article["group_title"] = build_group_title(article)

    # Competitor tracking reuses the articles the website pipeline already fetched, so the
    # trade-press half of it costs no extra requests.
    competitor_seen_pending: list[str] = []
    try:
        competitor_items = run_competitor_watch(
            root,
            trade_articles=website_result.get("all_candidates") or website_articles,
            hours_window=24,
            seen_sink=competitor_seen_pending,
        )
        competitor_items = [c for c in competitor_items if c.get("url") not in already_sent]
    except Exception as exc:
        log.warning("competitor watch failed, sending without that section: %s", exc)
        competitor_items = []

    subject = f"Newsjacking Articles - {format_month_day_year(datetime.now(timezone.utc))}"
    html = _build_html(website_articles, groups, competitor_items)
    send_result = _send_via_resend(subject, html, to_email)

    # Every score, gate verdict and reason behind this digest — including the candidates
    # that were rejected — so "why did you pick that?" has an answer after the fact.
    write_run_log(
        root,
        subject=subject,
        send_result=send_result,
        website_result=website_result,
        linkedin_result=linkedin_result,
        competitor_items=competitor_items,
        emailed_website=website_articles,
        emailed_linkedin=groups,
    )

    # Only remember what actually went out — a failed send must not suppress tomorrow's run.
    if send_result.get("success"):
        record_competitors_seen(root, competitor_seen_pending)
        record_sent_urls(
            root,
            [a.get("url") for a in website_articles]
            + [_post_url(p) for g in groups for p in g.get("posts", [])]
            + [c.get("url") for c in competitor_items],
        )

    return {
        "subject": subject,
        "send_result": send_result,
        "website_usage_stats": website_result.get("usage_stats"),
        "linkedin_summary": {
            "tier1_count": len(linkedin_result.get("tier1", [])),
            "tier2_count": len(linkedin_result.get("tier2", [])),
            "errors": linkedin_result.get("errors", []),
        },
    }
