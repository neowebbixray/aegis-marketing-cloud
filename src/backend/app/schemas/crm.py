"""Pydantic schemas for the CRM module: contacts, deals, pipelines, activities, custom field definitions, and lead scoring."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Activity Schemas ─────────────────────────────────────────────────────────────
class ActivityCreate(BaseModel):
    """Payload for creating a new activity."""

    type: str = Field(
        ..., min_length=1, max_length=16, description="Activity type (call, email, meeting, etc.)"
    )
    subject: str = Field(..., min_length=1, max_length=512)
    description: str | None = Field(None, max_length=5000)
    contact_id: UUID | None = Field(None, description="Associated contact ID")
    deal_id: UUID | None = Field(None, description="Associated deal ID")
    user_id: UUID | None = Field(None, description="User who performed the activity")

    model_config = ConfigDict(from_attributes=True)


class ActivityResponse(BaseModel):
    """Activity representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    type: str
    subject: str
    description: str | None
    contact_id: UUID | None
    deal_id: UUID | None
    user_id: UUID | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityUpdate(BaseModel):
    """Payload for updating an activity (all fields optional)."""

    type: str | None = Field(None, min_length=1, max_length=16)
    subject: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = Field(None, max_length=5000)
    contact_id: UUID | None = Field(None)
    deal_id: UUID | None = Field(None)
    user_id: UUID | None = Field(None)
    is_deleted: bool | None = Field(None)

    model_config = ConfigDict(from_attributes=True)


# ── Contact Schemas ─────────────────────────────────────────────────────────────
class ContactCreate(BaseModel):
    """Payload for creating a new contact."""

    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=256)
    position: str | None = Field(None, max_length=256)  # job title
    lifecycle_stage: str | None = Field("lead", max_length=32)
    source: str | None = Field(None, max_length=64)
    custom_fields: dict[str, Any] | None = Field(None)
    tags: list[str] | None = Field(None)
    owner_id: UUID | None = Field(None)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    """Contact representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    company: str | None
    position: str | None
    lifecycle_stage: str
    source: str | None
    custom_fields: dict[str, Any]
    tags: list[str]
    owner_id: UUID | None
    is_deleted: bool
    score: int | None = Field(None, ge=0, le=100)
    score_updated_at: datetime | None = Field(None)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactUpdate(BaseModel):
    """Payload for updating a contact (all fields optional)."""

    first_name: str | None = Field(None, min_length=1, max_length=128)
    last_name: str | None = Field(None, min_length=1, max_length=128)
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=256)
    position: str | None = Field(None, max_length=256)
    lifecycle_stage: str | None = Field(None, max_length=32)
    source: str | None = Field(None, max_length=64)
    custom_fields: dict[str, Any] | None = Field(None)
    tags: list[str] | None = Field(None)
    owner_id: UUID | None = Field(None)
    is_deleted: bool | None = Field(None)

    model_config = ConfigDict(from_attributes=True)


# ── Custom Field Definition Schemas ─────────────────────────────────────────────
class CustomFieldDefinitionCreate(BaseModel):
    """Payload for creating a custom field definition."""

    name: str = Field(..., min_length=1, max_length=128)
    key: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None)
    field_type: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="text, number, date, dropdown, multi_select, url",
    )
    config: dict[str, Any] | None = Field(default_factory=dict)
    is_required: bool = Field(False)
    is_active: bool = Field(True)
    display_order: int = Field(0, ge=0)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class CustomFieldDefinitionResponse(BaseModel):
    """Custom field definition representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    key: str
    description: str | None
    field_type: str
    config: dict[str, Any]
    is_required: bool
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomFieldDefinitionUpdate(BaseModel):
    """Payload for updating a custom field definition (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=128)
    key: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None)
    field_type: str | None = Field(None, min_length=1, max_length=32)
    config: dict[str, Any] | None = Field(None)
    is_required: bool | None = Field(None)
    is_active: bool | None = Field(None)
    display_order: int | None = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)


# ── Deal Schemas ───────────────────────────────────────────────────────────────
class DealCreate(BaseModel):
    """Payload for creating a new deal."""

    name: str = Field(..., min_length=1, max_length=512)
    value: float | None = Field(None, ge=0)
    currency: str | None = Field("USD", min_length=3, max_length=3)
    pipeline_stage_id: UUID = Field(..., description="Stage ID")
    contact_id: UUID | None = Field(None, description="Associated contact ID")
    organization_label: str | None = Field(None, max_length=256)
    owner_id: UUID | None = Field(None)
    probability: float | None = Field(None, ge=0, le=100)
    expected_close_date: date | None = Field(None)
    custom_fields: dict[str, Any] | None = Field(None)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class DealResponse(BaseModel):
    """Deal representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    value: float | None
    currency: str
    pipeline_stage_id: UUID
    contact_id: UUID | None
    organization_label: str | None
    owner_id: UUID | None
    probability: float | None
    expected_close_date: date | None
    custom_fields: dict[str, Any]
    # Win/Loss tracking fields
    lost_reason: str | None = Field(None)
    lost_at: datetime | None = Field(None)
    won_reason: str | None = Field(None)
    won_at: datetime | None = Field(None)
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealUpdate(BaseModel):
    """Payload for updating a deal (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=512)
    value: float | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    pipeline_stage_id: UUID | None = Field(None)
    contact_id: UUID | None = Field(None)
    organization_label: str | None = Field(None, max_length=256)
    owner_id: UUID | None = Field(None)
    probability: float | None = Field(None, ge=0, le=100)
    expected_close_date: date | None = Field(None)
    custom_fields: dict[str, Any] | None = Field(None)
    # Win/Loss tracking fields
    lost_reason: str | None = Field(None)
    lost_at: datetime | None = Field(None)
    won_reason: str | None = Field(None)
    won_at: datetime | None = Field(None)

    model_config = ConfigDict(from_attributes=True)


class DealStageChangeRequest(BaseModel):
    """Payload for changing a deal's pipeline stage."""

    pipeline_stage_id: UUID = Field(..., description="Target stage ID")
    reason: str | None = Field(None, max_length=500)  # General reason for stage change
    won_reason: str | None = Field(
        None, max_length=500
    )  # Reason for winning (if stage is closed_won)
    lost_reason: str | None = Field(
        None, max_length=500
    )  # Reason for losing (if stage is closed_lost)

    model_config = ConfigDict(from_attributes=True)


# ── Lead Score Schemas ─────────────────────────────────────────────────────────
class LeadScoreUpdate(BaseModel):
    """Payload for updating a lead score."""

    score: int = Field(..., ge=0, le=100, description="Score from 0 to 100")
    score_source: str = Field(..., description="Source of the score (ai, rule_based, manual, etc.)")
    scoring_factors: dict[str, Any] | None = Field(
        None, description="Factors that contributed to the score"
    )
    agent_id: UUID | None = Field(None, description="AI agent or rule set that generated the score")

    model_config = ConfigDict(from_attributes=True)


class LeadScoreHistoryResponse(BaseModel):
    """Lead score history representation."""

    id: UUID
    tenant_id: UUID
    contact_id: UUID
    score: int = Field(..., ge=0, le=100)
    score_source: str
    scoring_factors: dict[str, Any] | None = Field(None)
    agent_id: UUID | None = Field(None)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Pipeline Schemas ───────────────────────────────────────────────────────────
class PipelineCreate(BaseModel):
    """Payload for creating a new pipeline."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None)
    is_default: bool = Field(False)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class PipelineResponse(BaseModel):
    """Pipeline representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    is_default: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── ActivityType Schemas (optional) ─────────────────────────────────────────────
class ActivityTypeCreate(BaseModel):
    """Payload for creating an activity type."""

    name: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None)
    colour: str | None = Field(None, max_length=7)  # hex color
    is_active: bool = Field(True)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class ActivityTypeResponse(BaseModel):
    """Activity type representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    colour: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityTypeUpdate(BaseModel):
    """Payload for updating an activity type (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None)
    colour: str | None = Field(None, max_length=7)
    is_active: bool | None = Field(None)

    model_config = ConfigDict(from_attributes=True)
