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
    redis_url: str = Field(
        default="redis://:aegis_redis@localhost:6379/0",
        alias="REDIS_URL",
    )

    # ── RabbitMQ ────────────────────────────────────────────────────────────
    rabbitmq_url: str = Field(
        default="amqp://aegis:***@localhost:5672/",
        alias="RABBITMQ_URL",
    )

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

    # ── Media / MinIO ───────────────────────────────────────────────────────────
    media_library_root: str = Field(
        default="media-library",
        alias="MEDIA_LIBRARY_ROOT",
    )

    # ── Prometheus Metrics ─────────────────────────────────────────────────────
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # seconds

    # ── SSO / OAuth ────────────────────────────────────────────────────────────
    sso_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/sso/callback",
        alias="SSO_REDIRECT_URI",
    )

    google_oauth_client_id: str | None = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str | None = Field(default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET")
    microsoft_oauth_client_id: str | None = Field(default=None, alias="MICROSOFT_OAUTH_CLIENT_ID")
    microsoft_oauth_client_secret: str | None = Field(default=None, alias="MICROSOFT_OAUTH_CLIENT_SECRET")
    microsoft_oauth_tenant: str | None = Field(default=None, alias="MICROSOFT_OAUTH_TENANT")
    github_oauth_client_id: str | None = Field(default=None, alias="GITHUB_OAUTH_CLIENT_ID")
    github_oauth_client_secret: str | None = Field(default=None, alias="GITHUB_OAUTH_CLIENT_SECRET")

    # ── SAML ───────────────────────────────────────────────────────────────────
    saml_idp_metadata_url: str | None = Field(default=None, alias="SAML_IDP_METADATA_URL")
    saml_idp_entity_id: str | None = Field(default=None, alias="SAML_IDP_ENTITY_ID")
    saml_sp_entity_id: str | None = Field(default=None, alias="SAML_SP_ENTITY_ID")
    saml_sp_acs_url: str | None = Field(default=None, alias="SAML_SP_ACS_URL")
    saml_sp_x509_cert: str | None = Field(default=None, alias="SAML_SP_X509_CERT")
    saml_sp_private_key: str | None = Field(default=None, alias="SAML_SP_PRIVATE_KEY")

    # ── Qdrant Vector Store ────────────────────────────────────────────────────
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_prefer_grpc: bool = Field(default=False, alias="QDRANT_PREFER_GRPC")
    qdrant_https: bool = Field(default=False, alias="QDRANT_HTTPS")

    # ── Embeddings ─────────────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_endpoint: str | None = Field(default=None, alias="EMBEDDING_ENDPOINT")
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")

    # ── Knowledge / Chunking ───────────────────────────────────────────────────
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")

    # ── Celery (optional) ──────────────────────────────────────────────────────
    celery_broker_url: str = Field(
        default="redis://:aegis_redis@localhost:6379/0",
        alias="CELERY_BROKER_URL",
    )

    # ── Trusted Hosts ────────────────────────────────────────────────────────
    trusted_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        alias="TRUSTED_HOSTS",
    )

    # ── MinIO / S3 ─────────────────────────────────────────────────────────────
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")
    minio_bucket_assets: str = Field(default="assets", alias="MINIO_BUCKET_ASSETS")
    minio_bucket_media: str = Field(default="media", alias="MINIO_BUCKET_MEDIA")
    minio_bucket_backups: str = Field(default="backups", alias="MINIO_BUCKET_BACKUPS")

    # ── Stripe / Billing ────────────────────────────────────────────────────────
    stripe_api_key: str | None = Field(default=None, alias="STRIPE_API_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_free: str | None = Field(default=None, alias="STRIPE_PRICE_ID_FREE")
    stripe_price_id_pro: str | None = Field(default=None, alias="STRIPE_PRICE_ID_PRO")
    stripe_price_id_enterprise: str | None = Field(default=None, alias="STRIPE_PRICE_ID_ENTERPRISE")

    # ── SMTP / Email ─────────────────────────────────────────────────────────────
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@aegismc.com", alias="SMTP_FROM")
    smtp_tls: bool = Field(default=False, alias="SMTP_TLS")

    # ── Sentry / Error Tracking ──────────────────────────────────────────────────
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_environment: str | None = Field(default=None, alias="SENTRY_ENVIRONMENT")

    # ── OpenTelemetry ─────────────────────────────────────────────────────────────
    otel_service_name: str = Field(default="aegis-marketing-cloud", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    # ── n8n Workflow Engine ──────────────────────────────────────────────────────
    n8n_url: str = Field(default="http://localhost:5678", alias="N8N_URL")
    n8n_api_key: str | None = Field(default=None, alias="N8N_API_KEY")
    n8n_webhook_url: str | None = Field(default=None, alias="N8N_WEBHOOK_URL")

    # ── AI / LLM Provider ────────────────────────────────────────────────────────
    ai_provider: str = Field(default="nvidia-nim", alias="AI_PROVIDER")
    ai_model: str = Field(default="meta/llama-3.1-70b-instruct", alias="AI_MODEL")
    nvidia_nim_api_key: str | None = Field(default=None, alias="NVIDIA_NIM_API_KEY")
    nvidia_nim_base_url: str | None = Field(default=None, alias="NVIDIA_NIM_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # ── Feature Flags ────────────────────────────────────────────────────────────
    feature_ai_agents: bool = Field(default=True, alias="FEATURE_AI_AGENTS")
    feature_marketplace: bool = Field(default=False, alias="FEATURE_MARKETPLACE")
    feature_white_label: bool = Field(default=False, alias="FEATURE_WHITE_LABEL")
    feature_billing_enabled: bool = Field(default=False, alias="FEATURE_BILLING_ENABLED")

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
