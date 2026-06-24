"""Email delivery models — campaigns, messages, and delivery tracking.

All models are multi-tenant (tenant_id + workspace_id) and include
open/click tracking, bounce handling, and delivery status history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class EmailCampaign(BaseModel, SoftDeleteMixin):
    """An outbound email campaign — a batch of emails sent to recipients."""

    __tablename__ = "email_campaigns"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str] = mapped_column(String(320), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject_override: Mapped[str | None] = mapped_column(String(998), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
    )
    # status values: draft -> scheduled -> sending -> completed -> cancelled
    # Also: paused, failed

    provider: Mapped[str] = mapped_column(String(20), default="smtp")
    # provider values: smtp, ses

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Aggregate delivery stats
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    bounced_count: Mapped[int] = mapped_column(Integer, default=0)
    complained_count: Mapped[int] = mapped_column(Integer, default=0)
    opened_count: Mapped[int] = mapped_column(Integer, default=0)
    clicked_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    max_emails_per_minute: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
    )

    def __repr__(self) -> str:
        return f"<EmailCampaign {self.name} ({self.status})>"


class EmailMessage(BaseModel):
    """Tracks a single outgoing email message through its lifecycle.

    One row per recipient; tracks delivery status, open/click events,
    and bounce/complaint feedback.
    """

    __tablename__ = "email_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Email envelope
    from_email: Mapped[str] = mapped_column(String(320), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Content snapshot (rendered at send time)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(30),
        default="queued",
        nullable=False,
        index=True,
    )
    # status values: queued -> sending -> sent -> delivered
    #                            -> bounced -> complained -> failed
    # Also: opened, clicked (supplementary, combined with delivered)

    provider: Mapped[str] = mapped_column(String(20), default="smtp")
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Tracking
    tracking_id: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )
    tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    open_count: Mapped[int] = mapped_column(Integer, default=0)

    clicked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    click_count: Mapped[int] = mapped_column(Integer, default=0)

    bounced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    bounce_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )  # permanent, transient, undetermined
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    complained_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    complaint_feedback_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Timing
    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Custom metadata
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=dict,
    )

    def __repr__(self) -> str:
        return f"<EmailMessage {self.recipient_email} ({self.status})>"
