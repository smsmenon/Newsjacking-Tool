from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

VALID_STATUSES = {"draft", "under_review", "approved", "rejected", "published"}


def create_review_event(payload: dict[str, Any]) -> dict[str, Any]:
    status = payload.get("to_status")
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported review status: {status}")
    return {
        "id": str(uuid4()),
        "entity_type": payload.get("entity_type", "content_opportunity"),
        "entity_id": payload.get("entity_id", str(uuid4())),
        "from_status": payload.get("from_status", "draft"),
        "to_status": status,
        "reviewer": payload.get("reviewer", "local-reviewer@tada.example"),
        "comments": payload.get("comments", ""),
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

