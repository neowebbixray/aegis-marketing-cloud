"""Content-Security-Policy (CSP) middleware for Aegis Marketing Cloud.

Sets strict CSP headers on every response to mitigate XSS, data injection,
and other content-based attacks.  The policy is configurable via ``CSP_*``
environment variables so operators can tighten or relax rules per deployment.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings

logger = logging.getLogger("amc.csp")

# ── Default CSP directives (OWASP-recommended strict baseline) ───────────────
_DEFAULT_DIRECTIVES: dict[str, str] = {
    "default-src": "'self'",
    # script-src includes 'unsafe-inline' for Next.js inline scripts
    "script-src": "'self' 'unsafe-inline'",
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data: blob: https://*.minio.local https://*.amazonaws.com",
    "connect-src": "'self' ws: wss:",
    "font-src": "'self' data:",
    "frame-ancestors": "'none'",
    "form-action": "'self'",
    "base-uri": "'self'",
    "object-src": "'none'",
    "upgrade-insecure-requests": "",
    "block-all-mixed-content": "",
}

# ── Report-Only mode (default: enforcement) ───────────────────────────────────
_CSP_REPORT_ONLY = getattr(settings, "csp_report_only", False)


def _build_csp_value(directives: dict[str, str]) -> str:
    """Join CSP directives into a single header value string.

    Directives with an empty-string value are set without a source (e.g.
    ``upgrade-insecure-requests``).
    """
    parts: list[str] = []
    for name, value in directives.items():
        if value == "":
            parts.append(name)
        else:
            parts.append(f"{name} {value}")
    return "; ".join(parts)


class CSPMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that attaches ``Content-Security-Policy`` headers.

    The policy is built from ``_DEFAULT_DIRECTIVES`` and can be overridden
    at runtime via ``settings.csp_directives`` (a dict) or individual
    ``CSP_<DIRECTIVE>`` env vars.

    When ``settings.csp_report_only`` is ``True`` the header is sent as
    ``Content-Security-Policy-Report-Only`` instead of the enforcement form.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._directives: dict[str, str] = self._resolve_directives()
        self._header_value: str = _build_csp_value(self._directives)
        self._header_name: str = (
            "Content-Security-Policy-Report-Only"
            if getattr(settings, "csp_report_only", False)
            else "Content-Security-Policy"
        )
        logger.info(
            "CSP middleware active — header=%s directives=%s",
            self._header_name,
            self._directives,
        )

    @staticmethod
    def _resolve_directives() -> dict[str, str]:
        """Merge env-var overrides into the default CSP directives.

        For every key in ``settings`` that starts with ``csp_`` (after the
        pydantic-settings alias normalisation), the directive name is derived by
        replacing ``_`` with ``-`` and dropping the ``csp-`` prefix.
        """
        directives = dict(_DEFAULT_DIRECTIVES)

        # If settings has a full-directive override dict, use it entirely
        overrides: dict[str, Any] | None = getattr(settings, "csp_directives", None)
        if overrides:
            logger.debug("Using fully custom CSP directives from settings")
            return {k.replace("_", "-"): v for k, v in overrides.items()}

        # Otherwise pick individual CSP_* env vars from settings
        skip_fields = {"csp_enabled", "csp_report_only", "csp_directives"}
        for field_name in dir(settings):
            if not field_name.startswith("csp_"):
                continue
            if field_name in skip_fields:
                continue
            # Normalise: csp_script_src -> script-src
            directive_name = field_name[4:].replace("_", "-").lower()
            value: str = getattr(settings, field_name)
            if value is not None and value.strip():
                directives[directive_name] = value.strip()
                logger.debug("CSP override: %s = %s", directive_name, value.strip())

        return directives

    async def dispatch(
        self,
        request: Request,
        call_next: callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        # Only add header to actual responses (skip streaming/informational)
        if isinstance(response, Response) and self._header_name not in response.headers:
            response.headers[self._header_name] = self._header_value
        return response