"""
Alert service — sends alerts via Slack, email (SendGrid), and Teams.
Includes deduplication to prevent alert storms.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import httpx
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings

logger = logging.getLogger("tada.alert_service")


class AlertService:
    """
    Unified alert dispatching with deduplication.

    Dedup strategy:
      - Build a dedup key from (alert_type + title hash)
      - Check DB for existing active alert with same key
      - If found and within dedup window (default 1h), skip dispatch
    """

    DEDUP_WINDOW_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=10.0)

    async def dispatch(
        self,
        alert_type: str,
        title: str,
        description: str,
        severity: str,
        channels: List[str],
        related_item_id: Optional[UUID] = None,
        related_item_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Dispatch an alert to the specified channels.
        Returns the created alert record as a dict.
        """
        dedup_key = self._build_dedup_key(alert_type, title)

        # Import here to avoid circular imports
        from app.core.database import sessionmaker
        from app.models.database import Alert

        async with sessionmaker() as db:
            # Check deduplication
            from sqlalchemy import select, and_
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.DEDUP_WINDOW_SECONDS)
            existing_q = select(Alert).where(
                and_(
                    Alert.dedup_key == dedup_key,
                    Alert.status == "active",
                    Alert.created_at >= cutoff,
                )
            )
            existing = (await db.execute(existing_q)).scalar_one_or_none()

            if existing:
                logger.info("Alert deduplicated (key=%s, existing_id=%s)", dedup_key, existing.id)
                return {"id": str(existing.id), "deduplicated": True}

            # Create alert record
            alert = Alert(
                title=title,
                description=description,
                alert_type=alert_type,
                severity=severity,
                status="active",
                channels_sent=channels,
                related_item_id=related_item_id,
                related_item_type=related_item_type,
                dedup_key=dedup_key,
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)

            alert_id = alert.id

        # Dispatch to channels (outside DB transaction)
        sent = []
        errors = []

        for channel in channels:
            try:
                if channel == "slack":
                    await self._send_slack(title, description, severity, alert_id, metadata)
                    sent.append("slack")
                elif channel == "email":
                    await self._send_email(title, description, severity, alert_id, metadata)
                    sent.append("email")
                elif channel == "teams":
                    await self._send_teams(title, description, severity, alert_id, metadata)
                    sent.append("teams")
            except Exception as exc:
                logger.error("Failed to send alert via %s: %s", channel, exc)
                errors.append({"channel": channel, "error": str(exc)})

        return {"id": str(alert_id), "sent_to": sent, "errors": errors, "deduplicated": False}

    # ─── Slack ────────────────────────────────────────────────────────────────
    async def _send_slack(
        self,
        title: str,
        description: str,
        severity: str,
        alert_id: UUID,
        metadata: Optional[dict],
    ) -> None:
        """Send a rich Slack message via incoming webhook."""
        if not settings.SLACK_WEBHOOK_URL:
            logger.warning("SLACK_WEBHOOK_URL not configured — skipping Slack alert")
            return

        color_map = {"critical": "#FF0000", "warning": "#FFA500", "info": "#36A64F"}
        color = color_map.get(severity, "#808080")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "fallback": f"[{severity.upper()}] {title}",
                    "title": f"[{severity.upper()}] {title}",
                    "text": description,
                    "footer": f"TADA Intelligence | Alert ID: {alert_id}",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                    "fields": [
                        {"title": "Severity", "value": severity.capitalize(), "short": True},
                        {"title": "Alert ID", "value": str(alert_id)[:8] + "…", "short": True},
                    ],
                }
            ]
        }

        if metadata:
            extra_fields = [
                {"title": k, "value": str(v)[:80], "short": True}
                for k, v in list(metadata.items())[:4]
            ]
            payload["attachments"][0]["fields"].extend(extra_fields)

        resp = await self._http.post(settings.SLACK_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        logger.info("Slack alert sent (id=%s, status=%d)", alert_id, resp.status_code)

    # ─── SendGrid Email ───────────────────────────────────────────────────────
    async def _send_email(
        self,
        title: str,
        description: str,
        severity: str,
        alert_id: UUID,
        metadata: Optional[dict],
    ) -> None:
        """Send alert email via SendGrid."""
        if not settings.SENDGRID_API_KEY or not settings.ALERT_EMAIL_TO:
            logger.warning("SendGrid not configured — skipping email alert")
            return

        body_html = f"""
        <html><body>
        <h2 style="color: {'red' if severity == 'critical' else 'orange' if severity == 'warning' else 'green'}">
        [{severity.upper()}] {title}
        </h2>
        <p>{description}</p>
        <hr/>
        <small>Alert ID: {alert_id} &nbsp;|&nbsp; TADA Intelligence Platform</small>
        </body></html>
        """

        message = Mail(
            from_email=settings.ALERT_EMAIL_FROM,
            to_emails=settings.ALERT_EMAIL_TO,
            subject=f"[TADA {severity.upper()}] {title}",
            html_content=body_html,
        )

        import asyncio

        loop = asyncio.get_event_loop()
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        # SendGrid SDK is sync — run in executor
        response = await loop.run_in_executor(None, sg.send, message)
        logger.info("Email alert sent (id=%s, status=%s)", alert_id, response.status_code)

    # ─── Microsoft Teams ──────────────────────────────────────────────────────
    async def _send_teams(
        self,
        title: str,
        description: str,
        severity: str,
        alert_id: UUID,
        metadata: Optional[dict],
    ) -> None:
        """Send alert card to Microsoft Teams via incoming webhook."""
        if not settings.TEAMS_WEBHOOK_URL:
            logger.warning("TEAMS_WEBHOOK_URL not configured — skipping Teams alert")
            return

        theme_map = {"critical": "attention", "warning": "warning", "info": "good"}
        theme = theme_map.get(severity, "default")

        # Adaptive Card payload
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": f"[{severity.upper()}] {title}",
                                "weight": "bolder",
                                "size": "medium",
                                "color": theme,
                            },
                            {
                                "type": "TextBlock",
                                "text": description,
                                "wrap": True,
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Severity", "value": severity},
                                    {"title": "Alert ID", "value": str(alert_id)[:8]},
                                ],
                            },
                        ],
                    },
                }
            ],
        }

        resp = await self._http.post(settings.TEAMS_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        logger.info("Teams alert sent (id=%s, status=%d)", alert_id, resp.status_code)

    # ─── Utilities ────────────────────────────────────────────────────────────
    @staticmethod
    def _build_dedup_key(alert_type: str, title: str) -> str:
        raw = f"{alert_type}:{title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def close(self) -> None:
        await self._http.aclose()


# FastAPI dependency
def get_alert_service() -> AlertService:
    return AlertService()
