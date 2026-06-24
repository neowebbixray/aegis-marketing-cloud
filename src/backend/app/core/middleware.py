"""Custom ASGI middleware for request ID tracing, tenant context extraction,
rate limiting, and structured logging.

All middleware classes are pure ASGI middleware (not BaseHTTPMiddleware) to
avoid event-loop issues with httpx.AsyncClient in tests.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings

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


class RequestIDMiddleware:
    """Pure ASGI middleware — ensures every request has an ``X-Request-ID``.

    If the client provides one it is used; otherwise a new UUID is generated.
    The value is also stored at ``request.state.request_id``.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        # Extract X-Request-ID from request headers
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-request-id":
                request_id = value.decode("utf-8")
                break

        if not request_id:
            request_id = uuid.uuid4().hex

        # Store request_id in scope state
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        request_id_bytes = request_id.encode("utf-8")

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"X-Request-ID", request_id_bytes))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ── Tenant Context Middleware ────────────────────────────────────────────────


class TenantContextMiddleware:
    """Pure ASGI middleware — parse ``X-Tenant-ID`` and ``X-Workspace-ID`` headers.

    Values are stored at ``scope.state.tenant_id`` and
    ``scope.state.workspace_id`` (both optional strings).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tenant_id = None
        workspace_id = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-tenant-id":
                tenant_id = value.decode("utf-8")
            elif name.lower() == b"x-workspace-id":
                workspace_id = value.decode("utf-8")

        scope.setdefault("state", {})
        scope["state"]["tenant_id"] = tenant_id
        scope["state"]["workspace_id"] = workspace_id

        await self.app(scope, receive, send)


# ── Rate Limiting Middleware ─────────────────────────────────────────────────

# Redis Lua script for atomic sliding-window rate-limit check-and-add.
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


class RateLimitMiddleware:
    """Pure ASGI — Redis-backed sliding window rate limiter.

    Uses a Redis sorted set per ``(tenant_id | client_ip, endpoint_path)`` to
    track request timestamps. On each request, the set is trimmed to the
    configured window and the remaining count is checked against the configured
    limit.

    When ``settings.rate_limit_enabled`` is ``False``, all requests pass through
    without any rate check.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._redis: Any = None  # redis.asyncio.Redis | None
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Short-circuit if rate limiting is disabled
        if not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        # Extract identity and path from scope
        headers = dict(scope.get("headers", []))
        state = scope.get("state", {})

        tenant_id: str | None = state.get("tenant_id")
        if tenant_id:
            identity = tenant_id
        else:
            forwarded = headers.get(b"x-forwarded-for", b"").decode("utf-8")
            if forwarded:
                identity = forwarded.split(",")[0].strip()
            else:
                identity = headers.get(b"host", b"unknown").decode("utf-8")

        # Check for a tier hint
        tier_hint_bytes = headers.get(b"x-rate-limit-tier", b"")
        tier_hint = tier_hint_bytes.decode("utf-8").lower()
        identity_with_tier = f"{identity}:{tier_hint}" if tier_hint in _TIER_LIMITS else identity

        per_minute, per_hour = _resolve_rate_limits(identity_with_tier)

        now = time.time()
        window_min = 60
        window_hour = 3600
        path = scope.get("path", "/unknown")

        try:
            r = await self._get_redis()
            script_hash = await self._load_script(r)

            key_min = f"rate_limit:{identity}:{path}:min"
            allowed_min, count_min, oldest_min = await r.evalsha(
                script_hash,
                1,
                key_min,
                float(now),
                float(window_min),
                float(per_minute),
            )
            allowed_min = bool(allowed_min)
            count_min = int(count_min)

            allowed_hour = True
            count_hour = 0
            if per_hour > 0:
                key_hour = f"rate_limit:{identity}:{path}:hour"
                allowed_hour, count_hour, _oldest_hour = await r.evalsha(
                    script_hash,
                    1,
                    key_hour,
                    float(now),
                    float(window_hour),
                    float(per_hour),
                )
                allowed_hour = bool(allowed_hour)
                count_hour = int(count_hour)

        except Exception:
            # Degrade gracefully
            await self.app(scope, receive, send)
            return

        if not allowed_min or not allowed_hour:
            if not allowed_min:
                retry_after = max(1, int(float(oldest_min) + window_min - now + 0.5))
            else:
                retry_after = max(1, int(window_hour))

            # Build 429 response — inline JSON to avoid Request dependency
            import json
            from uuid import uuid4

            from app.schemas.base import ERROR_TYPE_BASE, ERROR_TYPE_PATHS

            type_path = ERROR_TYPE_PATHS.get(HTTP_429_TOO_MANY_REQUESTS, "rate-limit-error")
            body_payload = {
                "error": {
                    "type": f"{ERROR_TYPE_BASE}/{type_path}",
                    "title": "Rate Limit Exceeded",
                    "status": HTTP_429_TOO_MANY_REQUESTS,
                    "detail": f"Too many requests. Try again in {retry_after} second(s).",
                    "trace_id": uuid4().hex[:12],
                },
            }
            body_bytes = json.dumps(body_payload).encode("utf-8")
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body_bytes)).encode("utf-8")),
                (b"Retry-After", str(retry_after).encode("utf-8")),
                (
                    b"X-RateLimit-Limit",
                    str(per_minute if not allowed_min else per_hour).encode("utf-8"),
                ),
                (b"X-RateLimit-Remaining", b"0"),
                (b"X-RateLimit-Reset", str(int(now + retry_after)).encode("utf-8")),
                (b"X-RateLimit-Tier", (tier_hint or "free").encode("utf-8")),
            ]
            await send(
                {
                    "type": "http.response.start",
                    "status": HTTP_429_TOO_MANY_REQUESTS,
                    "headers": headers,
                }
            )
            await send({"type": "http.response.body", "body": body_bytes})
            return

        # Within limit — forward request and attach headers
        captured_status = [0]

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                captured_status[0] = message.get("status", 0)
                headers_list = list(message.get("headers", []))
                remaining = max(0, per_minute - count_min)
                headers_list.append((b"X-RateLimit-Limit", str(per_minute).encode("utf-8")))
                headers_list.append((b"X-RateLimit-Remaining", str(remaining).encode("utf-8")))
                headers_list.append(
                    (b"X-RateLimit-Reset", str(int(now + window_min)).encode("utf-8"))
                )
                per_hour_str = str(per_hour).encode("utf-8")
                headers_list.append((b"X-RateLimit-Hour-Limit", per_hour_str))
                remaining_hour = (
                    str(max(0, per_hour - count_hour)).encode("utf-8")
                    if per_hour > 0
                    else b"unlimited"
                )
                headers_list.append((b"X-RateLimit-Hour-Remaining", remaining_hour))
                headers_list.append((b"X-RateLimit-Tier", (tier_hint or "free").encode("utf-8")))
                message["headers"] = headers_list
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ── Logging Middleware ───────────────────────────────────────────────────────


class LoggingMiddleware:
    """Pure ASGI middleware that logs structured request / response summaries.

    Emits a single log line per request with method, path, status, duration,
    request_id, and tenant_id.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        logger = logging.getLogger("amc.access")

        start = time.monotonic()
        state = scope.get("state", {})
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/unknown")
        request_id = state.get("request_id")
        tenant_id = state.get("tenant_id")

        captured_status = [0]

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                captured_status[0] = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        elapsed = time.monotonic() - start
        status = captured_status[0]

        logger.info(
            "%s %s %s %.4fs",
            method,
            path,
            status,
            elapsed,
            extra={
                "request_id": request_id,
                "tenant_id": tenant_id,
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(elapsed * 1000, 2),
            },
        )
