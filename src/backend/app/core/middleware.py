"""
Custom ASGI middleware for request ID tracing, tenant context extraction,
rate limiting, and structured logging.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.schemas.base import build_problem_response


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


# ── Rate Limiting Middleware ─────────────────────────────────────────────────
# Redis Lua script for atomic sliding-window rate-limit check-and-add.
#
# Keys:  1 — rate_limit:<identity>:<path>
# Args:  now (str), window (str), limit (str)
# Returns:
#   {1, current_count, now}          — allowed (request counted)
#   {0, current_count, oldest_score} — denied  (rate limit exceeded)
#
# The script:
#   1. Removes entries outside [now - window, now]
#   2. Counts remaining entries
#   3. If count >= limit, returns denied + oldest score (for Retry-After)
#   4. Otherwise, adds current timestamp and sets TTL, returns allowed
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

local cutoff = now - window

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)

-- Count remaining entries in the window
local count = redis.call('ZCARD', key)

if count >= limit then
    -- Get the oldest entry's score for Retry-After calculation
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = 0
    if #oldest > 0 then
        oldest_score = tonumber(oldest[2])
    end
    return {0, count, oldest_score}
end

-- Record this request
redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, window)

return {1, count + 1, now}
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Uses a Redis sorted set per ``(tenant_id | client_ip, endpoint_path)`` to
    track request timestamps. On each request, the set is trimmed to the
    configured window and the remaining count is checked against the configured
    limit.

    When ``settings.rate_limit_enabled`` is ``False``, all requests pass through
    without any rate check.

    Rate limit headers (``X-RateLimit-Limit``, ``X-RateLimit-Remaining``,
    ``X-RateLimit-Reset``) are added to every response.  When the limit is
    exceeded, a ``429 Too Many Requests`` response is returned with an RFC 7807
    problem detail body and a ``Retry-After`` header.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._redis: Any = None  # redis.asyncio.Redis | None — lazily imported
        self._script_hash: str | None = None

    async def _get_redis(self) -> Any:
        """Return a lazily-initialised Redis client."""
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def _load_script(self, r: Any) -> str:
        """Load (or retrieve) the SHA1 of the rate-limit Lua script."""
        if self._script_hash is None:
            self._script_hash = await r.script_load(_RATE_LIMIT_LUA)
        return self._script_hash

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # ── Short-circuit if rate limiting is disabled ────────────────
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # ── Resolve identity ──────────────────────────────────────────
        tenant_id: str | None = getattr(request.state, "tenant_id", None)
        if tenant_id:
            identity = tenant_id
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                identity = forwarded.split(",")[0].strip()
            elif request.client is not None:
                identity = request.client.host
            else:
                identity = "unknown"

        # ── Build Redis key ───────────────────────────────────────────
        key = f"rate_limit:{identity}:{request.url.path}"
        now = time.time()
        window = float(settings.rate_limit_window)
        limit = float(settings.rate_limit_requests)

        # ── Atomic check-and-increment via Lua script ─────────────────
        try:
            r = await self._get_redis()
            script_hash = await self._load_script(r)
            allowed, current_count, oldest_ts = await r.evalsha(
                script_hash, 1, key, now, window, limit
            )
            allowed = bool(allowed)
            current_count = int(current_count)
            oldest_ts = float(oldest_ts)
        except Exception:
            # Degrade gracefully — if Redis is unavailable let the
            # request through rather than blocking all traffic.
            return await call_next(request)

        # ── Rate limit exceeded → 429 ─────────────────────────────────
        if not allowed:
            retry_after = max(1, int(oldest_ts + window - now + 0.5))
            response = build_problem_response(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                title="Rate Limit Exceeded",
                detail=f"Too many requests. Try again in {retry_after} second(s).",
                request=request,
            )
            # Ensure response is a Response object (for header manipulation)
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(now + retry_after))
            return response

        # ── Within limit → forward request ───────────────────────────
        response = await call_next(request)

        # Attach rate-limit headers to the real response
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, settings.rate_limit_requests - current_count)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(now + settings.rate_limit_window)
        )

        return response


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
