"""Pydantic schemas for the webhooks module: event catalog, registration, delivery logs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ── Event Catalog ─────────────────────────────────────────────────────────────


class WebhookEventType(StrEnum):
    """All supported webhook event types per Volume 6 API spec."""

    # ── CRM events ────────────────────────────────────────────────────────
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    DEAL_CREATED = "deal.created"
    DEAL_UPDATED = "deal.updated"
    DEAL_STAGE_CHANGED = "deal.stage_changed"
    PIPELINE_CREATED = "pipeline.created"
    PIPELINE_UPDATED = "pipeline.updated"

    # ── Marketing events ──────────────────────────────────────────────────
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_UPDATED = "campaign.updated"
    CAMPAIGN_SENT = "campaign.sent"
    CAMPAIGN_COMPLETED = "campaign.completed"
    EMAIL_OPENED = "email.opened"
    EMAIL_CLICKED = "email.clicked"
    EMAIL_BOUNCED = "email.bounced"
    SEGMENT_UPDATED = "segment.updated"

    # ── Billing events ────────────────────────────────────────────────────
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAST_DUE = "invoice.past_due"
    INVOICE_FAILED = "invoice.failed"
    CREDIT_USAGE_EXCEEDED = "credit.usage_exceeded"

    # ── System events ─────────────────────────────────────────────────────
    WEBHOOK_TEST = "webhook.test"
    WEBHOOK_ENABLED = "webhook.enabled"
    WEBHOOK_DISABLED = "webhook.disabled"

    # ── AI events ─────────────────────────────────────────────────────────
    AI_AGENT_EXECUTED = "ai.agent_executed"
    AI_AGENT_FAILED = "ai.agent_failed"
    KNOWLEDGE_DOCUMENT_PROCESSED = "knowledge.document_processed"


# Map each event type to its expected payload schema description
WEBHOOK_EVENT_CATALOG: dict[str, dict[str, Any]] = {
    # CRM
    WebhookEventType.CONTACT_CREATED.value: {
        "description": "A new contact was created",
        "payload_schema": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string"},
                "email": {"type": "string"},
                "name": {"type": "string"},
            },
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.CONTACT_UPDATED.value: {
        "description": "An existing contact was updated",
        "payload_schema": {
            "type": "object",
            "properties": {"contact_id": {"type": "string"}, "changes": {"type": "array"}},
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.CONTACT_DELETED.value: {
        "description": "A contact was deleted",
        "payload_schema": {"type": "object", "properties": {"contact_id": {"type": "string"}}},
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.DEAL_CREATED.value: {
        "description": "A new deal was created",
        "payload_schema": {
            "type": "object",
            "properties": {
                "deal_id": {"type": "string"},
                "amount": {"type": "number"},
                "stage": {"type": "string"},
            },
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.DEAL_UPDATED.value: {
        "description": "A deal was updated",
        "payload_schema": {
            "type": "object",
            "properties": {"deal_id": {"type": "string"}, "changes": {"type": "array"}},
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.DEAL_STAGE_CHANGED.value: {
        "description": "A deal moved to a different pipeline stage",
        "payload_schema": {
            "type": "object",
            "properties": {
                "deal_id": {"type": "string"},
                "from_stage": {"type": "string"},
                "to_stage": {"type": "string"},
            },
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.PIPELINE_CREATED.value: {
        "description": "A new pipeline was created",
        "payload_schema": {
            "type": "object",
            "properties": {"pipeline_id": {"type": "string"}, "name": {"type": "string"}},
        },
        "category": "crm",
        "version": "v1",
    },
    WebhookEventType.PIPELINE_UPDATED.value: {
        "description": "A pipeline was updated",
        "payload_schema": {
            "type": "object",
            "properties": {"pipeline_id": {"type": "string"}, "changes": {"type": "array"}},
        },
        "category": "crm",
        "version": "v1",
    },
    # Marketing
    WebhookEventType.CAMPAIGN_CREATED.value: {
        "description": "A campaign was created",
        "payload_schema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}, "name": {"type": "string"}},
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.CAMPAIGN_UPDATED.value: {
        "description": "A campaign was updated",
        "payload_schema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}, "changes": {"type": "array"}},
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.CAMPAIGN_SENT.value: {
        "description": "A campaign was sent out",
        "payload_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "recipient_count": {"type": "integer"},
            },
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.CAMPAIGN_COMPLETED.value: {
        "description": "A campaign finished sending",
        "payload_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "sent": {"type": "integer"},
                "opened": {"type": "integer"},
                "clicked": {"type": "integer"},
            },
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.EMAIL_OPENED.value: {
        "description": "An email was opened by a recipient",
        "payload_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "recipient_email": {"type": "string"},
                "timestamp": {"type": "string"},
            },
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.EMAIL_CLICKED.value: {
        "description": "A link in an email was clicked",
        "payload_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "recipient_email": {"type": "string"},
                "link_url": {"type": "string"},
                "timestamp": {"type": "string"},
            },
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.EMAIL_BOUNCED.value: {
        "description": "An email bounced",
        "payload_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "recipient_email": {"type": "string"},
                "bounce_type": {"type": "string"},
            },
        },
        "category": "marketing",
        "version": "v1",
    },
    WebhookEventType.SEGMENT_UPDATED.value: {
        "description": "A segment definition or membership changed",
        "payload_schema": {
            "type": "object",
            "properties": {"segment_id": {"type": "string"}, "member_count": {"type": "integer"}},
        },
        "category": "marketing",
        "version": "v1",
    },
    # Billing
    WebhookEventType.SUBSCRIPTION_CREATED.value: {
        "description": "A new subscription was created",
        "payload_schema": {
            "type": "object",
            "properties": {
                "subscription_id": {"type": "string"},
                "plan": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.SUBSCRIPTION_UPDATED.value: {
        "description": "A subscription was updated",
        "payload_schema": {
            "type": "object",
            "properties": {"subscription_id": {"type": "string"}, "changes": {"type": "array"}},
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.SUBSCRIPTION_CANCELLED.value: {
        "description": "A subscription was cancelled",
        "payload_schema": {
            "type": "object",
            "properties": {
                "subscription_id": {"type": "string"},
                "cancelled_at": {"type": "string"},
            },
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.INVOICE_PAID.value: {
        "description": "An invoice was paid",
        "payload_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
            },
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.INVOICE_PAST_DUE.value: {
        "description": "An invoice became past due",
        "payload_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "amount_due": {"type": "number"},
                "due_date": {"type": "string"},
            },
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.INVOICE_FAILED.value: {
        "description": "Invoice payment failed",
        "payload_schema": {
            "type": "object",
            "properties": {"invoice_id": {"type": "string"}, "reason": {"type": "string"}},
        },
        "category": "billing",
        "version": "v1",
    },
    WebhookEventType.CREDIT_USAGE_EXCEEDED.value: {
        "description": "Credit wallet usage exceeded threshold",
        "payload_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "balance": {"type": "number"},
                "threshold": {"type": "number"},
            },
        },
        "category": "billing",
        "version": "v1",
    },
    # System
    WebhookEventType.WEBHOOK_TEST.value: {
        "description": "A test event sent to verify webhook connectivity",
        "payload_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}, "timestamp": {"type": "string"}},
        },
        "category": "system",
        "version": "v1",
    },
    WebhookEventType.WEBHOOK_ENABLED.value: {
        "description": "A webhook was enabled",
        "payload_schema": {
            "type": "object",
            "properties": {"webhook_id": {"type": "string"}, "url": {"type": "string"}},
        },
        "category": "system",
        "version": "v1",
    },
    WebhookEventType.WEBHOOK_DISABLED.value: {
        "description": "A webhook was disabled",
        "payload_schema": {
            "type": "object",
            "properties": {"webhook_id": {"type": "string"}, "url": {"type": "string"}},
        },
        "category": "system",
        "version": "v1",
    },
    # AI
    WebhookEventType.AI_AGENT_EXECUTED.value: {
        "description": "An AI agent completed execution",
        "payload_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "execution_id": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        "category": "ai",
        "version": "v1",
    },
    WebhookEventType.AI_AGENT_FAILED.value: {
        "description": "An AI agent execution failed",
        "payload_schema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "execution_id": {"type": "string"},
                "error": {"type": "string"},
            },
        },
        "category": "ai",
        "version": "v1",
    },
    WebhookEventType.KNOWLEDGE_DOCUMENT_PROCESSED.value: {
        "description": "A knowledge document was processed (indexed/chunked)",
        "payload_schema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "status": {"type": "string"},
                "chunks": {"type": "integer"},
            },
        },
        "category": "ai",
        "version": "v1",
    },
}


# ── Webhook CRUD schemas ─────────────────────────────────────────────────────

DEFAULT_RETRY_CONFIG = {
    "max_retries": 5,
    "initial_interval_seconds": 10,
    "multiplier": 2.0,
    "max_interval_seconds": 3600,
}


class RetryConfig(BaseModel):
    """Exponential backoff retry configuration for webhook delivery."""

    max_retries: int = Field(default=5, ge=0, le=20)
    initial_interval_seconds: int = Field(default=10, ge=1, le=300)
    multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    max_interval_seconds: int = Field(default=3600, ge=60, le=86400)


class WebhookCreate(BaseModel):
    """Payload for POST /webhooks — register a new webhook endpoint."""

    url: str = Field(..., max_length=2048, min_length=1)
    events: list[WebhookEventType] = Field(..., min_length=1)
    description: str | None = Field(None, max_length=255)
    secret: str | None = Field(None, min_length=16, max_length=128)
    api_version: str = Field(default="v1", max_length=10)
    retry_config: RetryConfig | None = None
    is_active: bool = Field(default=True)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[WebhookEventType]) -> list[WebhookEventType]:
        if not v:
            raise ValueError("At least one event type is required")
        return v


class WebhookUpdate(BaseModel):
    """Payload for PATCH /webhooks/{id} — partial update."""

    url: str | None = Field(None, max_length=2048)
    events: list[WebhookEventType] | None = None
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    api_version: str | None = Field(None, max_length=10)
    retry_config: RetryConfig | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookResponse(BaseModel):
    """Webhook representation returned by the API."""

    id: UUID
    tenant_id: UUID
    url: str
    events: list[str]
    is_active: bool
    api_version: str
    retry_config: dict[str, Any] | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Delivery schemas ──────────────────────────────────────────────────────────


class DeliveryStatus(StrEnum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    DELIVERING = "delivering"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class WebhookDeliveryResponse(BaseModel):
    """Delivery attempt record returned by the API."""

    id: UUID
    webhook_id: UUID
    event_type: str
    status: str
    request_headers: dict[str, Any] | None = None
    response_status: int | None = None
    response_body: str | None = None
    duration_ms: int | None = None
    attempt: int
    max_attempts: int
    next_retry_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookEventCatalogResponse(BaseModel):
    """Event catalog entry returned by the API."""

    event_type: str
    description: str
    payload_schema: dict[str, Any]
    category: str
    version: str


class WebhookSecretRotateResponse(BaseModel):
    """Response after rotating a webhook secret."""

    id: UUID
    message: str = "Secret rotated successfully. The new secret is shown once."


class WebhookTestResponse(BaseModel):
    """Response from sending a test event."""

    delivery_id: UUID
    status: str
    message: str = "Test event sent."
