"""
Application configuration via pydantic-settings.

Loads environment variables from a .env file and provides a global ``settings``
object that all application code imports from.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """Return the project root (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application-level settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("AMC_ENV_FILE", _project_root() / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Aegis Marketing Cloud"
    debug: bool = False
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://amc:amc_secret@localhost:5432/aegis_marketing_cloud",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:***@localhost:5672/", alias="RABBITMQ_URL")

    # ── Auth / JWT ───────────────────────────────────────────────────────────
    secret_key: str = Field(default="changeme", alias="SECRET_KEY")
    jwt_algorithm: str = "RS256"  # Docs mandate RS256 for production
    jwt_key_id: str = Field(default="default", alias="JWT_KEY_ID")
    jwt_access_token_expire: int = Field(default=15, alias="JWT_ACCESS_TOKEN_EXPIRE")  # minutes
    jwt_refresh_token_expire: int = Field(default=10080, alias="JWT_REFRESH_TOKEN_EXPIRE")  # 7 days

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Allow CORS_ORIGINS to be a JSON array or comma-separated string."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # ── Encryption (pgcrypto) ────────────────────────────────────────────────
    encryption_key: Optional[str] = Field(default=None, alias="ENCRYPTION_KEY")

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # seconds

    # ── Trusted Hosts ────────────────────────────────────────────────────────
    trusted_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        alias="TRUSTED_HOSTS",
    )

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [x.strip() for x in v.split(",") if x.strip()]
        return v


settings = Settings()  # type: ignore[call-arg]
"""Global application settings singleton."""
