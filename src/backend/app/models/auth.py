"""SQLAlchemy models for authentication and identity:
User, OAuthAccount, Session, MfaDevice, ApiKey.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantMixin


class User(BaseModel, TenantMixin):
    """Primary user account. Soft-deletable, tenant-scoped."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), default="en", nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), default="UTC", nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_jsonb: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mfa_devices: Mapped[list[MfaDevice]] = relationship(
        "MfaDevice",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class OAuthAccount(BaseModel):
    """Links a user to an external OAuth provider account."""

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(256), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        Index("ix_oauth_provider_account", "provider", "provider_account_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount {self.provider}:{self.provider_account_id}>"


class Session(BaseModel, TenantMixin):
    """User session tied to a refresh token hash."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_refresh_hash", "refresh_token_hash"),
    )

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:

        return self.expires_at < datetime.now(UTC)


class MfaDevice(BaseModel):
    """Multi-factor authentication device (TOTP, SMS, or WebAuthn)."""

    __tablename__ = "mfa_devices"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )  # 'totp', 'sms', 'webauthn'
    secret: Mapped[str] = mapped_column(String(512), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mfa_devices")

    __table_args__ = (Index("ix_mfa_user_id", "user_id"),)


class ApiKey(BaseModel, TenantMixin):
    """API key for programmatic access. Supports scoping and expiry."""

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=list, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("ix_api_keys_user_id", "user_id"),)

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
