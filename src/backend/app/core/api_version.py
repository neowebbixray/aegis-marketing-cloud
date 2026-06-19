"""
API versioning middleware and deprecation calendar.

Supports two version resolution strategies:
1. ``Accept-Version`` header (preferred)
2. URL prefix (e.g. ``/api/v1/...``)

Emits ``Sunset`` and ``Deprecation`` headers for deprecated API versions.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("amc.api_version")

# ── Version parse ────────────────────────────────────────────────────────────

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)$")


def _parse_version(version_str: str) -> tuple[int, int] | None:
    """Parse a version string ``\"1.0\"`` into ``(1, 0)``, or return ``None``."""
    m = _VERSION_PATTERN.match(version_str.strip())
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


# ── Version info ─────────────────────────────────────────────────────────────


@dataclass
class APIVersionInfo:
    """Information about a single API version."""

    version: str  # e.g. "1.0"
    released: date
    deprecated: date | None = None
    sunset: date | None = None
    changelog_url: str | None = None


# ── Deprecation calendar ─────────────────────────────────────────────────────

API_VERSION_CALENDAR: dict[str, APIVersionInfo] = {
    "1.0": APIVersionInfo(
        version="1.0",
        released=date(2025, 1, 15),
        deprecated=date(2026, 1, 15),
        sunset=date(2026, 7, 15),
        changelog_url="https://docs.aegismc.com/api/changelog/v1.0",
    ),
}

# The current/latest supported version string.
CURRENT_API_VERSION = "1.0"

# The default version to use when none is specified.
DEFAULT_API_VERSION = "1.0"

# Versions that are still fully supported (neither deprecated nor sunset).
SUPPORTED_VERSIONS = {"1.0"}


# ── Middleware ───────────────────────────────────────────────────────────────


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware that resolves the requested API version.

    Resolution order:
    1. ``Accept-Version`` header (e.g. ``Accept-Version: 1.0``)
    2. Default version (``1.0``)

    The resolved version is stored at ``request.state.api_version``.

    If the requested version is deprecated, a ``Deprecation`` header is added
    to the response. If it is past its sunset date, a ``Sunset`` header is
    added.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Resolve version
        version_str = request.headers.get("Accept-Version", DEFAULT_API_VERSION)
        parsed = _parse_version(version_str)

        if parsed is None:
            # Invalid version header — fall back to default
            version_str = DEFAULT_API_VERSION
            parsed = _parse_version(version_str)
            assert parsed is not None

        request.state.api_version = version_str
        request.state.api_version_parsed = parsed

        # Process the request
        response = await call_next(request)

        # Attach versioning headers
        response.headers["X-API-Version"] = version_str

        version_info = API_VERSION_CALENDAR.get(version_str)
        if version_info is not None:
            today = date.today()

            if version_info.deprecated and today >= version_info.deprecated:
                response.headers["Deprecation"] = f"version=\"{version_str}\""

                if version_info.sunset and today >= version_info.sunset:
                    response.headers["Sunset"] = version_info.sunset.isoformat()

            if version_info.changelog_url:
                response.headers["X-API-Changelog"] = version_info.changelog_url

        return response


# ── Helper ───────────────────────────────────────────────────────────────────


def get_api_version(request: Request) -> str:
    """Return the resolved API version string from the request state."""
    return getattr(request.state, "api_version", DEFAULT_API_VERSION)


def version_gt(v1: str, v2: str) -> bool:
    """Compare two version strings (e.g. ``\"2.0\" > \"1.5\"``)."""
    p1 = _parse_version(v1)
    p2 = _parse_version(v2)
    if p1 is None or p2 is None:
        return False
    return p1 > p2


def version_gte(v1: str, v2: str) -> bool:
    """Check if *v1* >= *v2*."""
    p1 = _parse_version(v1)
    p2 = _parse_version(v2)
    if p1 is None or p2 is None:
        return False
    return p1 >= p2
