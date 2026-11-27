from __future__ import annotations

import json
import os
import ssl

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
from typing import Any


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)



def _pov(item: dict) -> str:
    """Return TADA's 1-2 sentence contrarian POV for this item, no article explanation."""
    # Newer discovery/contrarian pipeline shape
    pov = item.get("tada_pov") or item.get("pov")
    if pov:
        sentences = [s.strip() for s in pov.replace("\n", " ").split(". ") if s.strip()]
        return ". ".join(sentences[:2]).rstrip(".") + "."
    # Reference pipeline shape (tada_ci.pipeline / DigestItem)
    perspective = item.get("tada_perspective", {})
    tada_response = perspective.get("tada_response", "")
    if tada_response:
        sentences = [s.strip() for s in tada_response.replace("\n", " ").split(". ") if s.strip()]
        return ". ".join(sentences[:2]).rstrip(".") + "."
    return "No POV available for this signal."


def _build_html(
    signals: list[dict],
    recipient_name: str,
    sender_name: str,
) -> str:
    articles_html = ""
    for i, item in enumerate(signals[:3], start=1):
        sig = item.get("signal", {})
        headline = sig.get("headline") or item.get("title", "No headline")
        pov = _pov(item)
        url = sig.get("url") or item.get("url", "#")

        articles_html += f"""
        <div style="margin-bottom:28px;padding-bottom:28px;border-bottom:1px solid #e2e8f0;">
          <p style="margin:0 0 4px;font-size:12px;color:#94a3b8;font-weight:600;text-transform:uppercase;">Article {i}</p>
          <p style="margin:0 0 6px;font-size:15px;font-weight:700;color:#1e293b;line-height:1.4;"><strong>{headline}</strong></p>
          <p style="margin:0 0 10px;font-size:13px;color:#475569;line-height:1.6;"><strong>TADA's POV:</strong> {pov}</p>
          <p style="margin:0;font-size:13px;color:#475569;"><a href="{url}" style="color:#3b82f6;text-decoration:none;">Read full article →</a></p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:32px 16px;">
    <div style="background:#ffffff;border-radius:8px;padding:32px;border:1px solid #e2e8f0;">

      <p style="margin:0 0 20px;font-size:14px;color:#1e293b;">Hi {recipient_name},</p>
      <p style="margin:0 0 28px;font-size:14px;color:#475569;">We found the following articles that may be relevant for TADA:</p>

      {articles_html}

      <p style="margin:28px 0 4px;font-size:14px;color:#1e293b;">Regards,</p>
      <p style="margin:0;font-size:14px;color:#1e293b;font-weight:600;">{sender_name}</p>
    </div>
  </div>
</body>
</html>"""


def _build_plain(
    signals: list[dict],
    recipient_name: str,
    sender_name: str,
) -> str:
    lines = [f"Hi {recipient_name},\n",
             "We found the following articles that may be relevant for TADA:\n"]

    for i, item in enumerate(signals[:3], start=1):
        sig = item.get("signal", {})
        lines.append(f"Article {i}")
        lines.append(f"Headline: {sig.get('headline') or item.get('title', '')}")
        lines.append(f"TADA's POV: {_pov(item)}")
        lines.append(f"Read full article: {sig.get('url') or item.get('url', '')}")
        lines.append("---")

    lines += [f"\nRegards,", sender_name]
    return "\n".join(lines)


def send_digest_email(
    digest: dict[str, Any],
    to_email: str | list[str],
    subject: str | None = None,
    recipient_name: str = "Team",
    sender_name: str = "TADA Intelligence",
    cc: str | list[str] | None = None,
) -> dict[str, Any]:
    import urllib.request as _urllib
    import urllib.error as _urlerr

    signals = digest.get("top_signals", [])
    if not signals:
        return {"success": False, "error": "No signals in digest to send"}

    subject = subject or "Articles relevant to TADA"

    # Normalise to lists
    to_list = [to_email] if isinstance(to_email, str) else list(to_email)
    cc_list: list[str] = []
    if cc:
        cc_list = [cc] if isinstance(cc, str) else list(cc)

    resend_key = _env("RESEND_API_KEY")
    if not resend_key:
        return {"success": False, "error": "RESEND_API_KEY not configured in .env"}

    from_addr = _env("RESEND_FROM", "onboarding@resend.dev")
    html_body = _build_html(signals, recipient_name, sender_name)
    plain_body = _build_plain(signals, recipient_name, sender_name)

    payload_dict = {
        "from": f"{sender_name} <{from_addr}>",
        "to": to_list,
        "subject": subject,
        "html": html_body,
        "text": plain_body,
    }
    if cc_list:
        payload_dict["cc"] = cc_list

    payload = json.dumps(payload_dict).encode()

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
    except _urlerr.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return {"success": False, "to": to_list, "cc": cc_list, "subject": subject, "error": f"Resend error {exc.code}: {body}"}
    except Exception as exc:
        return {"success": False, "to": to_list, "cc": cc_list, "subject": subject, "error": f"Resend request failed: {exc}"}

    return {
        "success": True,
        "to": to_list,
        "cc": cc_list,
        "subject": subject,
        "articles_sent": min(len(signals), 3),
        "id": resp_data.get("id"),
    }
