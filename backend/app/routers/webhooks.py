"""
Webhooks router — n8n integration endpoints.
Called by n8n workflows when content is collected, signals are detected,
or alerts need to be dispatched.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.database import Alert, ContentItem, Signal
from app.models.schemas import (
    WebhookAlertTrigger,
    WebhookContentCollected,
    WebhookResponse,
    WebhookSignalDetected,
)
from app.services.alert_service import AlertService, get_alert_service

logger = logging.getLogger("tada.webhooks")
router = APIRouter()


@router.post("/content-collected", response_model=WebhookResponse)
async def webhook_content_collected(
    body: WebhookContentCollected,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> WebhookResponse:
    """
    Called by n8n when a content collection workflow finishes.
    Persists the raw article and queues embedding generation.
    """
    item = ContentItem(
        source_id=body.source_id,
        title=body.title,
        url=str(body.url),
        source=str(body.url).split("/")[2] if body.url else "unknown",
        topic="uncategorized",  # LangGraph agent will classify async
        full_content=body.content,
        published_at=body.published_at,
        author=body.author,
        extra_metadata=body.metadata or {},
        status="processing",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    logger.info("Content collected (id=%s, url=%s)", item.id, body.url)
    # TODO: enqueue embedding + classification task to Celery / background task

    return WebhookResponse(received=True, id=item.id, message="Content queued for processing")


@router.post("/signal-detected", response_model=WebhookResponse)
async def webhook_signal_detected(
    body: WebhookSignalDetected,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> WebhookResponse:
    """
    Called by n8n when a LangGraph agent detects a signal.
    Creates a Signal record in pending_review state.
    """
    signal = Signal(
        title=body.title,
        description=body.description,
        signal_type=body.signal_type,
        strength=body.strength,
        confidence=body.metadata.get("confidence", 0.7),
        status="pending_review",
        source_count=len(body.source_content_ids),
        langgraph_run_id=body.langgraph_run_id,
    )
    db.add(signal)
    await db.flush()  # get signal.id

    # Link source content
    from app.models.database import SignalContentLink

    for content_id in body.source_content_ids:
        link = SignalContentLink(signal_id=signal.id, content_id=content_id)
        db.add(link)

    await db.commit()
    await db.refresh(signal)

    logger.info(
        "Signal detected (id=%s, type=%s, strength=%.2f)",
        signal.id, body.signal_type, body.strength,
    )

    return WebhookResponse(received=True, id=signal.id, message="Signal created — pending review")


@router.post("/alert-trigger", response_model=WebhookResponse)
async def webhook_alert_trigger(
    body: WebhookAlertTrigger,
    alert_service: AlertService = Depends(get_alert_service),
    _user: CurrentUser = Depends(get_current_user),
) -> WebhookResponse:
    """
    Called by n8n to trigger an outbound alert across configured channels.
    Handles deduplication automatically.
    """
    channels = [c.value for c in body.channels] if body.channels else ["slack"]
    result = await alert_service.dispatch(
        alert_type=body.alert_type.value,
        title=body.title,
        description=body.description,
        severity=body.severity.value,
        channels=channels,
        related_item_id=body.related_item_id,
        related_item_type=body.related_item_type,
        metadata=body.metadata,
    )

    return WebhookResponse(
        received=True,
        id=result["id"],
        message="deduplicated" if result.get("deduplicated") else f"Alert sent to: {result.get('sent_to', [])}",
    )
