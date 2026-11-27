"""
TADA Intelligence Platform — FastAPI Application Entry Point
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings
from app.core.database import engine, sessionmaker
from app.routers import (
    alerts,
    analytics,
    competitors,
    content,
    content_ideas,
    executive,
    graph,
    recommendations,
    review,
    signals,
    sources,
    trends,
    webhooks,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("tada.main")


# ─── OpenTelemetry Setup ──────────────────────────────────────────────────────
def setup_telemetry() -> None:
    """Configure OpenTelemetry with OTLP exporter (Langfuse / Jaeger / etc.)."""
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    resource = Resource.create(
        {
            "service.name": "tada-api",
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("OpenTelemetry configured → %s", settings.OTEL_ENDPOINT)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle."""
    logger.info("Starting TADA API v%s [%s]", settings.APP_VERSION, settings.ENVIRONMENT)

    # Initialise telemetry
    setup_telemetry()

    # Verify DB connectivity
    try:
        async with sessionmaker() as session:
            await session.execute("SELECT 1")
        logger.info("Database connection OK")
    except Exception as exc:
        logger.error("Database connection FAILED: %s", exc)
        # Don't hard-crash — let health check surface the degradation

    logger.info("TADA API startup complete")
    yield
    logger.info("TADA API shutting down")


# ─── App Factory ──────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="TADA Content Intelligence Platform API",
        description="Serve signals, trends, insights and recommendations to the TADA frontend.",
        version=settings.APP_VERSION,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def request_id_and_timing(request: Request, call_next) -> Response:
        """Attach X-Request-ID and X-Process-Time headers."""
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}ms"
        return response

    # ── Routers ───────────────────────────────────────────────────────────────
    PREFIX = "/api/v1"
    app.include_router(content.router,          prefix=f"{PREFIX}/content",         tags=["Content"])
    app.include_router(signals.router,          prefix=f"{PREFIX}/signals",         tags=["Signals"])
    app.include_router(trends.router,           prefix=f"{PREFIX}/trends",          tags=["Trends"])
    app.include_router(content_ideas.router,    prefix=f"{PREFIX}",                 tags=["ContentIdeas"])
    app.include_router(recommendations.router,  prefix=f"{PREFIX}/recommendations", tags=["Recommendations"])
    app.include_router(competitors.router,      prefix=f"{PREFIX}/competitors",     tags=["Competitors"])
    app.include_router(executive.router,        prefix=f"{PREFIX}/executive",       tags=["Executive"])
    app.include_router(graph.router,            prefix=f"{PREFIX}/graph",           tags=["KnowledgeGraph"])
    app.include_router(review.router,           prefix=f"{PREFIX}/review",          tags=["Review"])
    app.include_router(sources.router,          prefix=f"{PREFIX}/sources",         tags=["Sources"])
    app.include_router(analytics.router,        prefix=f"{PREFIX}/analytics",       tags=["Analytics"])
    app.include_router(alerts.router,           prefix=f"{PREFIX}/alerts",          tags=["Alerts"])
    app.include_router(webhooks.router,         prefix=f"{PREFIX}/webhooks",        tags=["Webhooks"])

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["System"], include_in_schema=True)
    async def health_check():
        """Liveness / readiness probe."""
        from datetime import datetime, timezone

        db_status = "ok"
        try:
            async with sessionmaker() as session:
                await session.execute("SELECT 1")
        except Exception:
            db_status = "error"

        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": settings.APP_VERSION,
            "db": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Global Exception Handler ───────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
        )

    # ── OTel FastAPI instrumentation (must be after router registration) ───────
    if settings.OTEL_ENABLED:
        FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
