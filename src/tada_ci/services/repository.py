from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tada_ci.pipeline import build_digest, load_articles
from tada_ci.services.rss_fetcher import fetch_live_articles


class JsonRepository:
    """Small file-backed repository for local demos and integration tests."""

    def __init__(self, root: Path):
        self.root = root
        self.examples_dir = root / "examples"
        self.work_dir = root / "work"
        self.config_dir = root / "config"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    @property
    def digest_path(self) -> Path:
        return self.work_dir / "daily_digest.json"

    @property
    def review_events_path(self) -> Path:
        return self.work_dir / "review_events.json"

    def read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def get_sources(self) -> list[dict[str, Any]]:
        return self.read_json(self.config_dir / "sources.json", [])

    def get_digest(self) -> dict[str, Any]:
        if not self.digest_path.exists():
            self.refresh_digest()
        return self.read_json(self.digest_path, {})

    def refresh_digest(self) -> dict[str, Any]:
        articles = load_articles(self.examples_dir / "sample_articles.json")
        digest = build_digest(articles).to_dict()
        digest["data_mode"] = "sample"
        self.write_json(self.digest_path, digest)
        return digest

    def refresh_live_digest(self) -> dict[str, Any]:
        rss_articles, rss_errors = fetch_live_articles(self.get_sources())
        all_errors = rss_errors

        articles = rss_articles
        if not articles:
            digest = self.refresh_digest()
            digest["data_mode"] = "sample_fallback"
            digest["fetch_errors"] = all_errors
            self.write_json(self.digest_path, digest)
            return digest

        digest = build_digest(articles).to_dict()
        digest["data_mode"] = "live_rss"
        digest["fetch_errors"] = all_errors
        digest["fetched_articles"] = [
            {
                "title": a.title,
                "source": a.source,
                "url": a.url,
                "publication_date": a.publication_date,
            }
            for a in articles
        ]
        self.write_json(self.digest_path, digest)
        return digest

    def get_signals(self) -> list[dict[str, Any]]:
        return self.get_digest().get("top_signals", [])

    def get_review_events(self) -> list[dict[str, Any]]:
        return self.read_json(self.review_events_path, [])

    def append_review_event(self, event: dict[str, Any]) -> dict[str, Any]:
        events = self.get_review_events()
        events.append(event)
        self.write_json(self.review_events_path, events)
        return event
