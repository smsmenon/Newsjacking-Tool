"""
Persist every decision a run made, so a picked article can be questioned afterwards.

Scores, gate verdicts and the reasoning behind them used to go to the console and vanish
with the process. When asked why a particular article was chosen, the answer was
unavailable — the only honest response was "I don't know". One JSON file per run fixes that.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_KEEP_RUNS = 60


def _runs_dir(root: Path) -> Path:
    return Path(root) / "data" / "runs"


def _trim(value: Any, limit: int = 600) -> Any:
    """Keep the log readable — reasoning is worth storing, full article bodies are not."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…"
    return value


def _article_record(article: dict) -> dict:
    gate = article.get("source_gate") or {}
    return {
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "source": article.get("source", ""),
        "published_at": article.get("published_at", ""),
        "score": article.get("relevance_score"),
        "audience_fit": article.get("audience_fit", ""),
        "recommendation": article.get("recommendation", ""),
        "matched_themes": article.get("matched_themes", []),
        "score_reasoning": _trim(article.get("reasoning", "")),
        "gate_pass": gate.get("pass"),
        "gate_reason": _trim(gate.get("reason", "")),
        "gate_overridden": gate.get("overridden"),
        "relaxed_selection": article.get("relaxed_selection"),
        "tada_pov": _trim(article.get("tada_pov", "")),
        "hater_bot": article.get("hater_bot", {}),
        "coverage": [c.get("source") for c in (article.get("coverage") or [])],
    }


def write_run_log(
    root: Path,
    *,
    subject: str,
    send_result: dict,
    website_result: dict,
    linkedin_result: dict,
    competitor_items: list[dict],
    emailed_website: list[dict],
    emailed_linkedin: list[dict],
) -> Path | None:
    """Write one audit file for this run. Never raises — logging must not break a send."""
    try:
        now = datetime.now(timezone.utc)
        selected_urls = {a.get("url") for a in emailed_website}
        candidates = website_result.get("all_candidates") or []

        payload = {
            "run_at": now.isoformat(),
            "subject": subject,
            "sent": bool(send_result.get("success")),
            "send_result": send_result,
            "website": {
                "usage_stats": website_result.get("usage_stats", {}),
                "selected": [_article_record(a) for a in emailed_website],
                # Everything scored but not sent, with the reason — this is the half that
                # answers "why wasn't X included?" as well as "why was Y?".
                "rejected": [
                    _article_record(a) for a in candidates
                    if a.get("url") not in selected_urls and a.get("relevance_score") is not None
                ],
            },
            "linkedin": {
                "total_fetched": linkedin_result.get("total_fetched"),
                "api_calls_used": linkedin_result.get("api_calls_used"),
                "errors": linkedin_result.get("errors", []),
                "groups": [
                    {
                        "label": g.get("label", ""),
                        "post_count": g.get("post_count"),
                        "total_comments": g.get("total_comments"),
                        "tier": g.get("tier"),
                        "pov": _trim(g.get("pov", "")),
                        "urls": [
                            (p.get("url") or p.get("urn") or "") for p in (g.get("posts") or [])
                        ],
                    }
                    for g in emailed_linkedin
                ],
            },
            "competitors": competitor_items,
        }

        directory = _runs_dir(root)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{now.strftime('%Y-%m-%d_%H%M')}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

        # Keep the directory from growing without bound.
        existing = sorted(directory.glob("*.json"))
        for stale in existing[:-_KEEP_RUNS]:
            stale.unlink(missing_ok=True)

        log.info("run log written: %s", path)
        return path
    except Exception as exc:
        log.warning("could not write run log: %s", exc)
        return None
