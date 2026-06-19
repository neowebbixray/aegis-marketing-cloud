"""
Pydantic schemas for the Notifications module: in-app notifications, email
notifications, notification preferences, digest scheduling.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Notification ────────────────────────────────────────────────────────────
class NotificationResponse(BaseModel):
    """In-app notification representation."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    notification_type: str  # alert, mention, system, digest, campaign, workflow
    title: str
    body: Optional[str] = None
    channel: str  # in_app, email, both
    priority: str = "normal"  # low, normal, high, urgent
    is_read: bool = False
    is_dismissed: bool = False
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    """Payload for creating a notification (typically internal)."""

    tenant_id: UUID
    user_id: UUID
    notification_type: str = Field(..., max_length=64)
    title: str = Field(..., min_length=1, max_length=512)
    body: Optional[str] = None
    channel: str = Field(default="in_app", max_length=16)
    priority: str = Field(default="normal", max_length=16)
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class UnreadCountResponse(BaseModel):
    """Unread notification count."""

    total: int = 0
    by_type: Optional[dict[str, int]] = None
    by_priority: Optional[dict[str, int]] = None


# ── Notification Preferences ────────────────────────────────────────────────
class NotificationPreferencesCreate(BaseModel):
    """Payload for POST /notifications/preferences."""

    channel: str = Field(default="in_app", max_length=16)
    notification_types: list[str] = Field(default_factory=lambda: ["all"])
    enabled: bool = True
    digest_enabled: bool = False
    digest_frequency: str = Field(default="daily", max_length=16)  # daily, weekly, never
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None
    email_address: Optional[str] = None


class NotificationPreferencesResponse(BaseModel):
    """User notification preferences representation."""

    id: UUID
    user_id: UUID
    tenant_id: UUID
    channel: str
    notification_types: list[str]
    enabled: bool
    digest_enabled: bool
    digest_frequency: str
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    email_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
