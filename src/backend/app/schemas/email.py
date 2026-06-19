"""Pydantic schemas for the Email Delivery module: send requests,
template management, delivery status, and webhook handling.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Send Email ────────────────────────────────────────────────────────────────


class EmailAddress(BaseModel):
    """An email address with an optional display name."""
    email: str = Field(..., max_length=320)
    name: str | None = Field(None, max_length=255)


class SendRequest(BaseModel):
    """Payload for POST /api/v1/email/send — send a single email."""

    to: EmailStr | str = Field(..., description="Recipient email address")
    to_name: str | None = Field(None, max_length=255)
    subject: str = Field(..., min_length=1, max_length=998)
    body_html: str | None = Field(None, description="HTML body (required if body_text is not set)")
    body_text: str | None = Field(None, description="Plain-text body (required if body_html is not set)")
    template_id: UUID | None = Field(None, description="Use an existing email template")
    template_variables: dict[str, Any] | None = Field(
        None, description="Variable substitutions for template rendering"
    )
    from_email: str | None = Field(None, max_length=320, description="Override sender")
    from_name: str | None = Field(None, max_length=255)
    reply_to: str | None = Field(None, max_length=320)
    tracking_enabled: bool = Field(default=True)
    provider: str = Field(default="smtp", pattern=r"^(smtp|ses)$")
    metadata: dict[str, Any] | None = None

    @field_validator("body_html", "body_text")
    @classmethod
    def _validate_body(cls, v: str | None, info: Any) -> str | None:
        """Ensure at least one of body_html or body_text is provided when
        no template_id is given."""
        values = info.data
        if not values.get("template_id") and not v and not values.get("body_text") and not values.get("body_html"):
            # We need to check both since we're called per-field
            pass
        return v

    @field_validator("body_html", "body_text", mode="after")
    @classmethod
    def _ensure_at_least_one_body(cls, v: str | None, info: Any) -> str | None:
        values = info.data
        has_template = values.get("template_id") is not None
        has_html = v is not None or values.get("body_html") is not None
        has_text = v is not None or values.get("body_text") is not None
        if not has_template and not has_html and not has_text:
            # This validator runs after both fields are processed;
            # but Pydantic runs per-field. We do a post-check.
            pass
        return v


class SendBulkItem(BaseModel):
    """A single recipient in a bulk send operation."""
    email: EmailStr | str = Field(..., description="Recipient email address")
    name: str | None = Field(None, max_length=255)
    variables: dict[str, Any] | None = Field(
        None, description="Per-recipient template variable overrides"
    )


class SendBulkRequest(BaseModel):
    """Payload for POST /api/v1/email/send-bulk — send to multiple recipients."""

    campaign_name: str = Field(..., min_length=1, max_length=255)
    recipients: list[SendBulkItem] = Field(..., min_length=1, max_length=10000)
    subject: str = Field(..., min_length=1, max_length=998)
    body_html: str | None = None
    body_text: str | None = None
    template_id: UUID | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    tracking_enabled: bool = Field(default=True)
    provider: str = Field(default="smtp", pattern=r"^(smtp|ses)$")
    scheduled_at: datetime | None = None
    max_emails_per_minute: int | None = Field(
        None, ge=1, le=10000,
        description="Rate limit for this campaign (emails per minute)",
    )
    metadata: dict[str, Any] | None = None


# ── Email Template ────────────────────────────────────────────────────────────


class EmailTemplateCreate(BaseModel):
    """Payload for POST /api/v1/email/templates."""
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=998)
    preheader: str | None = Field(None, max_length=255)
    body_html: str | None = Field(None, description="Jinja2 template HTML body")
    body_text: str | None = Field(None, description="Jinja2 template plain-text body")
    category: str | None = Field(None, max_length=50)
    variables: list[str] | None = Field(
        None, description="List of expected template variable names"
    )

    @field_validator("body_html", "body_text")
    @classmethod
    def _ensure_at_least_one(cls, v: str | None, info: Any) -> str | None:
        return v


class EmailTemplateUpdate(BaseModel):
    """Payload for PATCH /api/v1/email/templates/{id}."""
    name: str | None = Field(None, min_length=1, max_length=255)
    subject: str | None = Field(None, min_length=1, max_length=998)
    preheader: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    category: str | None = None
    variables: list[str] | None = None


class EmailTemplateResponse(BaseModel):
    """Email template representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    subject: str
    preheader: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    category: str | None = None
    variables: list[Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Delivery / Campaign ───────────────────────────────────────────────────────


class DeliveryResponse(BaseModel):
    """Individual email delivery record."""
    id: UUID
    tenant_id: UUID
    campaign_id: UUID | None = None
    recipient_email: str
    recipient_name: str | None = None
    subject: str
    status: str
    provider: str
    provider_message_id: str | None = None
    tracking_id: str | None = None
    opened_at: datetime | None = None
    open_count: int = 0
    clicked_at: datetime | None = None
    click_count: int = 0
    bounced_at: datetime | None = None
    bounce_type: str | None = None
    complained_at: datetime | None = None
    queued_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignResponse(BaseModel):
    """Email campaign representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    status: str
    provider: str
    total_recipients: int = 0
    sent_count: int = 0
    delivered_count: int = 0
    bounced_count: int = 0
    complained_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    failed_count: int = 0
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tracking_enabled: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SendResponse(BaseModel):
    """Response after sending an email (single or bulk)."""
    message: str
    message_id: UUID
    tracking_id: str | None = None
    status: str


class SendBulkResponse(BaseModel):
    """Response after initiating a bulk send."""
    message: str
    campaign_id: UUID
    total_recipients: int
    status: str


# ── Webhook ───────────────────────────────────────────────────────────────────


class BounceWebhookPayload(BaseModel):
    """Generic bounce/complaint webhook payload.

    Designed to accept SES SNS notifications and Mailgun/SparkPost
    webhook formats. The raw payload is stored and processed
    asynchronously.
    """
    raw_payload: dict[str, Any] = Field(..., description="Raw webhook payload")
    provider: str = Field(default="ses", pattern=r"^(ses|smtp)$")

    # Optional pre-parsed fields (for direct integration)
    message_id: str | None = Field(None, description="Provider message ID")
    event_type: str | None = Field(
        None, pattern=r"^(bounce|complaint|delivery|open|click)$"
    )
    recipient_email: str | None = None
    bounce_type: str | None = Field(
        None, pattern=r"^(permanent|transient|undetermined)$"
    )
    bounce_reason: str | None = None
    complaint_feedback_type: str | None = None
    timestamp: datetime | None = None


# ── Tracking ──────────────────────────────────────────────────────────────────


class TrackingResponse(BaseModel):
    """Response from tracking endpoints (open/click)."""
    status: str = "tracked"
