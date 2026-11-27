from __future__ import annotations

import hashlib
from typing import Any


def content_hash(title: str, body: str) -> str:
    return hashlib.sha256(f"{title}\n{body}".encode("utf-8")).hexdigest()


def normalize_article(raw: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    title = raw.get("title", "").strip()
    body = raw.get("full_text") or raw.get("summary") or ""
    return {
        "title": title,
        "source": source["name"],
        "category": source["category"],
        "url": raw.get("url", source["url"]),
        "publication_date": raw.get("publication_date", ""),
        "author": raw.get("author"),
        "full_text": body.strip(),
        "content_hash": content_hash(title, body),
    }

