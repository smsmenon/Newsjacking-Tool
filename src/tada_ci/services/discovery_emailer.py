"""
Discovery email sender for the TADA Content Intelligence Platform.

Sends a clean, professional executive-focused email summarising the top
articles surfaced by the discovery pipeline via the Resend API
(RESEND_API_KEY / RESEND_FROM).
"""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# SSL context — bypass certificate verification (matches project pattern)
# ---------------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def format_month_day_year(dt: datetime) -> str:
    """'Month D, YYYY' (e.g. 'June 18, 2026') without the platform-specific %-d strftime
    extension, which is Unix-only and raises 'Invalid format string' on Windows."""
    return f"{dt.strftime('%B')} {dt.day}, {dt.strftime('%Y')}"


def _today_label() -> str:
    return format_month_day_year(datetime.now(timezone.utc))


def _format_date(iso_str: str) -> str:
    """Best-effort ISO → human-readable date."""
    if not iso_str:
        return "Unknown date"
    # Previously used fmt.rstrip("%z")/.rstrip("%Z") to try to derive a bare format string —
    # str.rstrip() strips trailing *characters* found in its argument, not a suffix string,
    # so that only "worked" by coincidence for these two specific formats. Trying each real
    # format directly against the input is both correct and simpler.
    cleaned = iso_str.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%B %-d, %Y")
        except ValueError:
            pass
    return iso_str[:10]  # fallback: show YYYY-MM-DD


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _two_line_summary(article: dict) -> str:
    """Return the top 2 insights in INSIGHT → CAUSE → ACTION format."""
    bullets = article.get("summary_bullets", [])
    if bullets:
        clean = [b.strip().rstrip(".") for b in bullets if b.strip()]
        if len(clean) >= 2:
            return f"{clean[0]}.<br><br>{clean[1]}."
        if clean:
            return f"{clean[0]}."
    content = article.get("content", "") or article.get("title", "")
    sents = [s.strip() for s in content.replace("\n", " ").split(".") if len(s.strip()) > 30]
    if len(sents) >= 2:
        return f"{sents[0]}. {sents[1]}."
    return sents[0] + "." if sents else article.get("title", "")


def _build_html(
    articles: list[dict],
    recipient_name: str,
    sender_name: str,
    usage_stats: dict,
) -> str:
    article_blocks = ""
    for i, article in enumerate(articles, start=1):
        title = article.get("title", "Untitled")
        url = article.get("url", "#")
        summary = _two_line_summary(article)
        sep = '<hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">' if i < len(articles) else ""
        article_blocks += f"""
        <p style="margin:0 0 6px;">
          <a href="{url}" style="font-size:14px;font-weight:600;color:#1e293b;text-decoration:none;line-height:1.5;">{title}</a>
        </p>
        <p style="margin:0 0 4px;font-size:13px;color:#475569;line-height:1.6;">{summary}</p>
        <p style="margin:0;font-size:13px;"><a href="{url}" style="color:#3b82f6;text-decoration:none;">Read article &rarr;</a></p>
        {sep}"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:580px;margin:0 auto;padding:32px 16px;">
    <div style="background:#ffffff;border-radius:8px;padding:32px;border:1px solid #e2e8f0;">
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;">TADA Content Intelligence</p>
      <p style="margin:0 0 28px;font-size:20px;font-weight:700;color:#0f172a;">TADA — Today's Top Articles</p>

      <p style="margin:0 0 24px;font-size:14px;color:#475569;">Hi {recipient_name},</p>

      {article_blocks}

      <p style="margin:28px 0 4px;font-size:14px;color:#1e293b;">Regards,</p>
      <p style="margin:0;font-size:14px;font-weight:600;color:#1e293b;">{sender_name}</p>
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Plain-text builder
# ---------------------------------------------------------------------------

def _build_plain(
    articles: list[dict],
    recipient_name: str,
    sender_name: str,
    usage_stats: dict,
) -> str:
    lines: list[str] = [
        f"Hi {recipient_name},",
        "",
        "TADA Content Intelligence — Today's Top Articles",
        "",
    ]

    for i, article in enumerate(articles, start=1):
        title = article.get("title", "Untitled")
        url = article.get("url", "#")
        bullets = article.get("summary_bullets", [])
        lines.append(f"{i}. {title}")
        for b in bullets[:2]:
            lines.append(f"   {b.strip()}")
        lines.append(f"   {url}")
        lines.append("")

    lines += ["Regards,", sender_name]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public send function
# ---------------------------------------------------------------------------

def send_discovery_email(
    result: dict,
    to_email: str,
    recipient_name: str = "Team",
    sender_name: str = "TADA Intelligence",
) -> dict[str, Any]:
    """
    Send the discovery pipeline results as a professional executive email.

    Parameters
    ----------
    result:
        The dict returned by ``run_discovery_pipeline()``.
    to_email:
        Recipient email address.
    recipient_name:
        Name used in the greeting (default "Team").
    sender_name:
        Display name in the From field (default "TADA Intelligence").

    Returns
    -------
    dict with success status and metadata.
    """
    import urllib.request as _urllib
    import urllib.error as _urlerr

    top_articles: list[dict] = result.get("top_articles", [])
    usage_stats: dict = result.get("usage_stats", {})

    # Guard: nothing to send
    if not top_articles:
        return {
            "success": False,
            "reason": "no_relevant_articles_found",
            "articles_reviewed": usage_stats.get("articles_fetched", 0),
        }

    today = _today_label()
    subject = f"TADA Content Intelligence — {today}"
    n_articles = len(top_articles)

    html_body = _build_html(top_articles, recipient_name, sender_name, usage_stats)
    plain_body = _build_plain(top_articles, recipient_name, sender_name, usage_stats)

    # ------------------------------------------------------------------
    # Send via Resend API
    # ------------------------------------------------------------------
    resend_key = _env("RESEND_API_KEY")
    if not resend_key:
        return {
            "success": False,
            "to": to_email,
            "subject": subject,
            "error": "RESEND_API_KEY not configured in environment.",
        }

    from_addr = _env("RESEND_FROM", "onboarding@resend.dev")
    payload = json.dumps({
        "from": f"{sender_name} <{from_addr}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": plain_body,
    }).encode()

    req = _urllib.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "tada-intelligence/1.0",
        },
        method="POST",
    )
    try:
        with _urllib.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            resp_data = json.loads(resp.read())
        return {
            "success": True,
            "to": to_email,
            "subject": subject,
            "articles_sent": n_articles,
            "id": resp_data.get("id"),
        }
    except _urlerr.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return {
            "success": False,
            "to": to_email,
            "subject": subject,
            "error": f"Resend error {exc.code}: {body}",
        }
    except Exception as exc:
        return {
            "success": False,
            "to": to_email,
            "subject": subject,
            "error": f"Resend request failed: {exc}",
        }
