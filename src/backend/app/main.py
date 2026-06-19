"""
FastAPI application factory for Aegis Marketing Cloud.

Creates and configures the ASGI application with middleware, routers,
exception handlers, and lifespan events.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as v1_router
from app.api.graphql.schema import graphql_router
from app.config import settings
from app.core.api_version import APIVersionMiddleware
from app.core.config_validator import validate_config, halt_on_critical
from app.core.exceptions import register_exception_handlers
from app.core.metrics_middleware import PrometheusMetricsMiddleware
from app.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TenantContextMiddleware,
)
from app.database import engine


# ── Logging setup ────────────────────────────────────────────────────────────
def _configure_logging() -> None:
    """Set up structured logging for the application."""
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: connect / disconnect the database pool."""
    _configure_logging()
    logger = logging.getLogger("amc")

    # Validate configuration before starting
    logger.info("Validating configuration…")
    config_warnings = validate_config()
    if settings.environment == "production":
        halt_on_critical(config_warnings)

    logger.info("Starting %s — environment: %s", settings.app_name, settings.environment)

    # Verify database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(
                # Using a raw text query that works with asyncpg
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("Database connection pool established")
    except Exception as exc:
        logger.warning("Database not reachable at startup: %s", exc)

    yield  # Application runs here

    # Shutdown: dispose of the connection pool
    await engine.dispose()
    logger.info("Database connection pool disposed")
    logger.info("Shutdown complete")


# ── Application factory ──────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Aegis Marketing Cloud — Multi-tenant SaaS Marketing Platform API",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # ── Exception handlers ───────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Middleware ────────────────────────────────────────────────────────
    # Order matters: outermost runs first on request, last on response.

    # 1. Request ID (outermost)
    app.add_middleware(RequestIDMiddleware)

    # 1b. API Versioning (very early in the chain)
    app.add_middleware(APIVersionMiddleware)

    # 2. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Prometheus metrics (after CORS, before tenant — so /metrics is
    #    accessible without tenant context)
    app.add_middleware(PrometheusMetricsMiddleware)

    # 4. Trusted Host
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

    # 5. Tenant context
    app.add_middleware(TenantContextMiddleware)

    # 6. Rate limiting (stub)
    app.add_middleware(RateLimitMiddleware)

    # 7. Logging (innermost - runs closest to the router)
    app.add_middleware(LoggingMiddleware)

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(v1_router)

    # Mount GraphQL (Strawberry) at /api/v1/graphql per docs spec
    app.include_router(graphql_router)

    # Health check
    @app.get("/health", tags=["system"], include_in_schema=False)
    async def health_check() -> dict[str, Any]:
        """Legacy health endpoint — delegates to the v1 health router."""
        from app.api.v1.health import legacy_health

        return await legacy_health()

    return app


# ── ASGI entry point ─────────────────────────────────────────────────────────
app = create_app()
