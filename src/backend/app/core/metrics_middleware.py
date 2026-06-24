"""Prometheus metrics ASGI middleware for Aegis Marketing Cloud.

Records HTTP request count and duration histograms for every request passing
through the ASGI pipeline, exposes a ``/metrics`` endpoint in Prometheus text
format, and tracks database connection pool size.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.core.metrics import (
    ACTIVE_WS_CONNECTIONS,
    DB_CONNECTION_ACTIVE,
    HTTP_REQUEST_COUNT,
    HTTP_REQUEST_DURATION,
)

logger = logging.getLogger("amc.metrics")


def _init_db_pool_metric() -> None:
    """Set the ``DB_CONNECTION_ACTIVE`` gauge from the configured pool limits.

    This provides a baseline value at startup.  For a live view of actual
    pool utilisation a callback or periodic refresh would be needed.
    """
    try:
        from app.database import engine

        pool = engine.sync_engine.pool
        total = pool.total()
        DB_CONNECTION_ACTIVE.set(total)
    except Exception:
        # Fall back to configured limits when pool is not yet initialised
        DB_CONNECTION_ACTIVE.set(
            settings.database_pool_size + settings.database_max_overflow,
        )


class PrometheusMetricsMiddleware:
    """ASGI middleware that records Prometheus metrics for every request.

    Behaviour is gated by ``settings.prometheus_enabled``.  When disabled the
    middleware acts as a transparent pass-through (except for disabling the
    ``/metrics`` endpoint).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._enabled = settings.prometheus_enabled

        if self._enabled:
            _init_db_pool_metric()
            logger.info(
                "Prometheus metrics enabled — /metrics endpoint active",
            )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        # ── Pass-through when disabled ──────────────────────────────────
        if not self._enabled:
            await self.app(scope, receive, send)
            return

        # ── WebSocket tracking ─────────────────────────────────────────
        if scope["type"] == "websocket":
            ACTIVE_WS_CONNECTIONS.inc()
            await self.app(scope, receive, send)
            return

        # ── /metrics endpoint ──────────────────────────────────────────
        if scope["type"] == "http":
            path = scope.get("path", "/unknown")
            method = scope.get("method", "UNKNOWN")

            if path == "/metrics" and method == "GET":
                data = generate_latest()
                headers = [
                    (b"content-type", CONTENT_TYPE_LATEST.encode("utf-8")),
                    (b"content-length", str(len(data)).encode("utf-8")),
                ]
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": headers,
                    },
                )
                await send({"type": "http.response.body", "body": data})
                return

            # ── Record metrics for all other requests ──────────────────
            start = time.monotonic()

            async def _send_wrapper(message: dict[str, Any]) -> None:
                if message["type"] == "http.response.start":
                    status = message.get("status", 0)
                    elapsed = time.monotonic() - start
                    HTTP_REQUEST_COUNT.labels(
                        method=method,
                        endpoint=path,
                        status=status,
                    ).inc()
                    HTTP_REQUEST_DURATION.labels(
                        method=method,
                        endpoint=path,
                    ).observe(elapsed)
                await send(message)

            await self.app(scope, receive, _send_wrapper)
            return

        # ── Non-HTTP, non-WebSocket (e.g. lifespan) ────────────────────
        await self.app(scope, receive, send)
