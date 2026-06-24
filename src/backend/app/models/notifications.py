"""Notification model — persisted in-app notifications with read tracking.

Notifications are user-scoped (and optionally workspace-scoped) and carry
a type, title, message, priority, and optional action URL.  They are created
by the notification service and delivered in real-time via WebSocket.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Notification(BaseModel):
    """A single in-app notification for a user."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    action_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Notification {self.id} user={self.user_id} "
            f"type={self.notification_type} read={self.is_read}>"
        )
