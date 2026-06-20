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


# ── Rate Limit Tier Helpers ──────────────────────────────────────────────────

# In-memory cache of parsed tier config (refreshed at import time).
_TIER_LIMITS: dict[str, tuple[int, int]] = {}  # tier_name -> (per_minute, per_hour)


def _parse_tier_value(raw: str) -> tuple[int, int]:
    """Parse a ``"requests_per_min:requests_per_hour"`` string.

    ``0`` means *unlimited* for that window.
    """
    parts = raw.split(":", 1)
    per_min = int(parts[0].strip()) if parts else 100
    per_hour = int(parts[1].strip()) if len(parts) > 1 else 0
    return per_min, per_hour


def _load_tier_limits() -> dict[str, tuple[int, int]]:
    """Read tier limits from ``settings``."""
    return {
        "free": _parse_tier_value(settings.rate_limit_tier_free),
        "starter": _parse_tier_value(settings.rate_limit_tier_starter),
        "professional": _parse_tier_value(settings.rate_limit_tier_professional),
        "enterprise": _parse_tier_value(settings.rate_limit_tier_enterprise),
    }


_TIER_LIMITS = _load_tier_limits()


def _resolve_rate_limits(identity: str) -> tuple[int, int]:
    """Return ``(requests_per_min, requests_per_hour)`` for the given identity.

    Tries to extract a tier suffix from the identity (e.g. ``identity:tier``).
    If no tier suffix is found, returns the **free** tier limits.
    """
    if ":" in identity:
        _identity, tier = identity.rsplit(":", 1)
        tier = tier.lower()
        if tier in _TIER_LIMITS:
            return _TIER_LIMITS[tier]
    # Fallback to the simple settings-based limit or free tier
    per_min: int = settings.rate_limit_requests
    per_hour: int = _TIER_LIMITS.get("free", (100, 1000))[1]
    return per_min, per_hour


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

        # Check for a tier hint in the request header (e.g. X-RateLimit-Tier)
        tier_hint = request.headers.get("X-RateLimit-Tier", "").lower()
        if tier_hint in _TIER_LIMITS:
            identity_with_tier = f"{identity}:{tier_hint}"
        else:
            identity_with_tier = identity

        # ── Resolve limits for this identity ──────────────────────────
        per_minute, per_hour = _resolve_rate_limits(identity_with_tier)

        now = time.time()
        window_min = 60  # 1-minute window
        window_hour = 3600  # 1-hour window

        # ── Atomic check-and-increment via Lua script ─────────────────
        try:
            r = await self._get_redis()
            script_hash = await self._load_script(r)
            path = request.url.path

            # Check 1-minute window
            key_min = f"rate_limit:{identity}:{path}:min"
            allowed_min, count_min, oldest_min = await r.evalsha(
                script_hash, 1, key_min, float(now), float(window_min), float(per_minute)
            )
            allowed_min = bool(allowed_min)
            count_min = int(count_min)

            # Check 1-hour window (skip if per_hour is 0 = unlimited)
            allowed_hour = True
            count_hour = 0
            if per_hour > 0:
                key_hour = f"rate_limit:{identity}:{path}:hour"
                allowed_hour, count_hour, _oldest_hour = await r.evalsha(
                    script_hash, 1, key_hour, float(now), float(window_hour), float(per_hour)
                )
                allowed_hour = bool(allowed_hour)
                count_hour = int(count_hour)

        except Exception:
            # Degrade gracefully — if Redis is unavailable let the
            # request through rather than blocking all traffic.
            return await call_next(request)

        # ── Rate limit exceeded → 429 ─────────────────────────────────
        if not allowed_min or not allowed_hour:
            # Calculate the shortest retry-after from both windows
            if not allowed_min:
                retry_after = max(1, int(float(oldest_min) + window_min - now + 0.5))
            else:
                retry_after = max(1, int(window_hour))

            response = build_problem_response(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                title="Rate Limit Exceeded",
                detail=f"Too many requests. Try again in {retry_after} second(s).",
                request=request,
            )
            # Determine which limit was hit
            limit_exceeded = per_minute if not allowed_min else per_hour
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit_exceeded)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(now + retry_after))
            response.headers["X-RateLimit-Tier"] = tier_hint if tier_hint else "free"
            return response

        # ── Within limit → forward request ───────────────────────────
        response = await call_next(request)

        # Attach rate-limit headers to the real response
        remaining = max(0, per_minute - count_min)
        response.headers["X-RateLimit-Limit"] = str(per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window_min))
        response.headers["X-RateLimit-Hour-Limit"] = str(per_hour)
        response.headers["X-RateLimit-Hour-Remaining"] = str(
            max(0, per_hour - count_hour)
        ) if per_hour > 0 else "unlimited"
        response.headers["X-RateLimit-Tier"] = tier_hint if tier_hint else "free"

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
