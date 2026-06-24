"""Pydantic schemas for authentication and identity endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Requests ─────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=128)
    tenant_name: str | None = Field(None, max_length=256)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str


class CreateApiKeyRequest(BaseModel):
    """Payload for POST /auth/api-keys."""

    name: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=list)


class ChangePasswordRequest(BaseModel):
    """Payload for POST /auth/password/change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UpdateMeRequest(BaseModel):
    """Payload for PATCH /auth/me."""

    display_name: str | None = Field(None, min_length=1, max_length=128)
    avatar_url: str | None = None
    locale: str | None = Field(None, max_length=10)
    timezone: str | None = Field(None, max_length=64)


# ── Responses ────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    """Response for successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Public user profile."""

    id: UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    """API key representation (never exposes the full key)."""

    id: UUID
    name: str
    key_prefix: str
    scopes: list[str] | None = None
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned when a new API key is created — includes the full key once."""

    full_key: str
