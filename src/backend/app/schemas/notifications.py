"""Pydantic schemas for notifications and WebSocket messages."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Notification Types ─────────────────────────────────────────────────────────


class NotificationType(StrEnum):
    """All supported notification types."""

    EMAIL_SENT = "email_sent"
    WEBHOOK_FAILED = "webhook_failed"
    INVOICE_PAID = "invoice_paid"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    CREDIT_LOW = "credit_low"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CONTACT_IMPORTED = "contact_imported"
    SYSTEM_ALERT = "system_alert"
    TASK_ASSIGNED = "task_assigned"
    MENTION = "mention"
    WEBHOOK_DELIVERED = "webhook_delivered"
    BILLING_ISSUE = "billing_issue"
    DATA_EXPORT_READY = "data_export_ready"
    API_KEY_CREATED = "api_key_created"


# ── Notification Schemas ───────────────────────────────────────────────────────


class NotificationCreate(BaseModel):
    """Payload for creating a notification programmatically."""

    user_id: UUID
    workspace_id: UUID | None = None
    notification_type: NotificationType
    title: str = Field(..., max_length=255)
    message: str = Field(..., max_length=2000)
    data: dict[str, Any] = Field(default_factory=dict)
    action_url: str | None = Field(None, max_length=2048)
    priority: str = Field(default="normal", pattern=r"^(low|normal|high|critical)$")


class NotificationUpdate(BaseModel):
    """Payload for updating a notification (e.g. marking as read)."""

    is_read: bool = True


class NotificationResponse(BaseModel):
    """Notification representation returned by the API."""

    id: UUID
    user_id: UUID
    workspace_id: UUID | None = None
    notification_type: str
    title: str
    message: str
    data: dict[str, Any]
    action_url: str | None = None
    priority: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    data: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int


# ── WebSocket Message Schemas ──────────────────────────────────────────────────


class WebSocketMessageType(StrEnum):
    """Types of messages sent over the WebSocket connection."""

    NOTIFICATION = "notification"
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    TYPING = "typing"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    CONNECTED = "connected"


class WebSocketMessage(BaseModel):
    """Standard WebSocket message envelope."""

    type: WebSocketMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    notification_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "notification",
                "payload": {"title": "Email sent", "message": "Campaign completed"},
                "timestamp": "2026-06-19T12:00:00Z",
            }
        }
    }
