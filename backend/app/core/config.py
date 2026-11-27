"""Application settings — loaded from environment variables."""
from __future__ import annotations

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://tada:tada@localhost:5432/tada"

    # ── Auth (Clerk) ──────────────────────────────────────────────────────────
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = "https://api.clerk.dev/v1/jwks"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://app.tada.ai",
    ]

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Alerts ────────────────────────────────────────────────────────────────
    SLACK_WEBHOOK_URL: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    ALERT_EMAIL_FROM: str = "alerts@tada.ai"
    ALERT_EMAIL_TO: Optional[str] = None

    # ── Observability ─────────────────────────────────────────────────────────
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4317"
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None

    # ── n8n ───────────────────────────────────────────────────────────────────
    N8N_WEBHOOK_SECRET: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = Settings()
