"""
Custom ASGI middleware for request ID tracing, tenant context extraction,
rate limiting (stub), and structured logging.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings


# ── Request ID Middleware ────────────────────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has an ``X-Request-ID`` header.

    If the client provides one it is used; otherwise a new UUID is generated.
    The value is also stored at ``request.state.request_id``.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── Tenant Context Middleware ────────────────────────────────────────────────
class TenantContextMiddleware(BaseHTTPMiddleware):
    """Parse ``X-Tenant-ID`` and ``X-Workspace-ID`` headers into request state.

    Values are stored at ``request.state.tenant_id`` and
    ``request.state.workspace_id`` (both optional strings).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.tenant_id = request.headers.get("X-Tenant-ID")
        request.state.workspace_id = request.headers.get("X-Workspace-ID")
        return await call_next(request)


# ── Rate Limiting Middleware (stub) ──────────────────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Placeholder for Redis-backed rate limiting.

    When ``settings.rate_limit_enabled`` is ``True``, this middleware should
    check a sliding-window counter in Redis and return 429 if exceeded.
    Currently it passes all requests through.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # TODO: Implement Redis sliding-window rate limiting here.
        # Key:  rate_limit:{tenant_id or client_ip}:{endpoint}
        # Use:  redis_client.incr() + expire()
        # If exceeded: raise RateLimitExceeded("Too many requests")

        return await call_next(request)


# ── Logging Middleware ───────────────────────────────────────────────────────
class LoggingMiddleware(BaseHTTPMiddleware):
    """Log structured request / response summaries.

    Emits a single log line per request with method, path, status, duration,
    request_id, and tenant_id.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        import logging

        logger = logging.getLogger("amc.access")

        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        logger.info(
            "%s %s %s %.4fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "tenant_id": getattr(request.state, "tenant_id", None),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            },
        )
        return response
