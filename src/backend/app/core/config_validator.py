"""Configuration validation for Aegis Marketing Cloud.

Provides ``validate_config()`` called at startup to verify that all required
environment variables are set and that production-critical settings are
properly configured.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from app.config import settings

logger = logging.getLogger("amc.config")

# ── Validation rules ─────────────────────────────────────────────────────────
# Each entry: (field_name, display_name, critical, condition_fn)
#   critical=True  → app must halt if missing
#   critical=False → warning only

_REQUIRED_VARS: list[tuple[str, str, bool, Any]] = [
    # Critical — app cannot function without these
    ("database_url", "DATABASE_URL", True, None),
    ("secret_key", "SECRET_KEY", True, None),
    # Critical in production
    ("sentry_dsn", "SENTRY_DSN", False, None),
    ("stripe_api_key", "STRIPE_API_KEY", False, None),
    # Important but optional
    ("redis_url", "REDIS_URL", False, None),
    ("rabbitmq_url", "RABBITMQ_URL", False, None),
    ("qdrant_host", "QDRANT_HOST", False, None),
    ("minio_endpoint", "MINIO_ENDPOINT", False, None),
    ("minio_access_key", "MINIO_ACCESS_KEY", False, None),
    ("minio_secret_key", "MINIO_SECRET_KEY", False, None),
    ("smtp_host", "SMTP_HOST", False, None),
    ("smtp_from", "SMTP_FROM", False, None),
    ("n8n_url", "N8N_URL", False, None),
    # SSO / OAuth
    ("google_oauth_client_id", "GOOGLE_OAUTH_CLIENT_ID", False, None),
    ("google_oauth_client_secret", "GOOGLE_OAUTH_CLIENT_SECRET", False, None),
    ("microsoft_oauth_client_id", "MICROSOFT_OAUTH_CLIENT_ID", False, None),
    ("microsoft_oauth_client_secret", "MICROSOFT_OAUTH_CLIENT_SECRET", False, None),
    ("github_oauth_client_id", "GITHUB_OAUTH_CLIENT_ID", False, None),
    ("github_oauth_client_secret", "GITHUB_OAUTH_CLIENT_SECRET", False, None),
]


def validate_config() -> list[str]:
    """Validate the application configuration.

    Checks all ``_REQUIRED_VARS`` entries and returns a list of warning
    messages. Critical failures are logged at ERROR level and the function
    still returns them; the caller (``main.py`` lifespan) decides whether
    to halt the process.

    Returns:
        A list of warning / error messages.

    """
    messages: list[str] = []

    # ── 1. Check for placeholder / default values ─────────────────────────
    if settings.secret_key == "changeme":
        messages.append(
            "CRITICAL: SECRET_KEY is still set to the default 'changeme'. "
            "Generate a cryptographically random value for production.",
        )

    if settings.environment == "production":
        # Production-specific checks
        if settings.debug:
            messages.append(
                "CRITICAL: DEBUG is enabled in production environment. "
                "Set DEBUG=false in your .env file.",
            )

        if settings.cors_origins == ["*"] or "http://localhost" in str(settings.cors_origins):
            messages.append(
                "WARNING: CORS_ORIGINS contains localhost entries in production. "
                "Restrict to your actual domain(s).",
            )

        # Ensure database_url is not using the default dev credentials
        if "amc_secret" in settings.database_url or "changeme" in settings.database_url:
            messages.append(
                "CRITICAL: DATABASE_URL still uses default/placeholder credentials. "
                "Update with your production database credentials.",
            )

        # Ensure encryption key is set
        if not settings.encryption_key:
            messages.append(
                "CRITICAL: ENCRYPTION_KEY is not set. This is required for "
                "pgcrypto-based field encryption in production.",
            )

    # ── 2. Check each required variable ───────────────────────────────────
    for field_name, display_name, critical, _condition_fn in _REQUIRED_VARS:
        value = getattr(settings, field_name, None)
        if value is None or (isinstance(value, str) and value.strip() in ("", "changeme")):
            if critical:
                messages.append(f"CRITICAL: {display_name} is not set or is a placeholder.")
            else:
                messages.append(f"WARNING: {display_name} is not set — feature may be unavailable.")

    # ── 3. Environment file check ─────────────────────────────────────────
    env_file = os.getenv("AMC_ENV_FILE", "")
    if not env_file:
        # Check if .env exists in the project root
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        dotenv = project_root / ".env"
        if not dotenv.exists():
            messages.append(
                "WARNING: No .env file found and AMC_ENV_FILE is not set. "
                "Environment variables must be provided via the shell environment.",
            )

    # ── Log results ───────────────────────────────────────────────────────
    if messages:
        for msg in messages:
            if msg.startswith("CRITICAL"):
                logger.error(msg)
            else:
                logger.warning(msg)
    else:
        logger.info("Configuration validation passed.")

    return messages


def halt_on_critical(messages: list[str]) -> None:
    """Exit the process if any critical validation messages are present.

    Args:
        messages: Output from ``validate_config()``.

    """
    criticals = [m for m in messages if m.startswith("CRITICAL")]
    if criticals:
        logger.critical("Configuration validation FAILED — %d critical issue(s)", len(criticals))
        for msg in criticals:
            logger.critical("  • %s", msg)
        sys.exit(1)
