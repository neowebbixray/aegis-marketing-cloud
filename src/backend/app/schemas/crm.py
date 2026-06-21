"""
Pydantic schemas for the CRM module: contacts, deals, pipelines, activities, custom field definitions, and lead scoring.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

# ── Activity Schemas ─────────────────────────────────────────────────────────────
class ActivityCreate(BaseModel):
    """Payload for creating a new activity."""
    type: str = Field(..., min_length=1, max_length=16, description="Activity type (call, email, meeting, etc.)")
    subject: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = Field(None, max_length=5000)
    contact_id: Optional[UUID] = Field(None, description="Associated contact ID")
    deal_id: Optional[UUID] = Field(None, description="Associated deal ID")
    user_id: Optional[UUID] = Field(None, description="User who performed the activity")

    model_config = ConfigDict(from_attributes=True)


class ActivityResponse(BaseModel):
    """Activity representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    type: str
    subject: str
    description: Optional[str]
    contact_id: Optional[UUID]
    deal_id: Optional[UUID]
    user_id: Optional[UUID]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityUpdate(BaseModel):
    """Payload for updating an activity (all fields optional)."""
    type: Optional[str] = Field(None, min_length=1, max_length=16)
    subject: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = Field(None, max_length=5000)
    contact_id: Optional[UUID] = Field(None)
    deal_id: Optional[UUID] = Field(None)
    user_id: Optional[UUID] = Field(None)
    is_deleted: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)


# ── Contact Schemas ─────────────────────────────────────────────────────────────
class ContactCreate(BaseModel):
    """Payload for creating a new contact."""
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    email: Optional[str] = Field(None, max_length=320)
    phone: Optional[str] = Field(None, max_length=32)
    company: Optional[str] = Field(None, max_length=256)
    position: Optional[str] = Field(None, max_length=256)  # job title
    lifecycle_stage: Optional[str] = Field("lead", max_length=32)
    source: Optional[str] = Field(None, max_length=64)
    custom_fields: Optional[dict[str, Any]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    owner_id: Optional[UUID] = Field(None)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class ContactResponse(BaseModel):
    """Contact representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    position: Optional[str]
    lifecycle_stage: str
    source: Optional[str]
    custom_fields: dict[str, Any]
    tags: List[str]
    owner_id: Optional[UUID]
    is_deleted: bool
    score: Optional[int] = Field(None, ge=0, le=100)
    score_updated_at: Optional[datetime] = Field(None)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactUpdate(BaseModel):
    """Payload for updating a contact (all fields optional)."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(None, min_length=1, max_length=128)
    email: Optional[str] = Field(None, max_length=320)
    phone: Optional[str] = Field(None, max_length=32)
    company: Optional[str] = Field(None, max_length=256)
    position: Optional[str] = Field(None, max_length=256)
    lifecycle_stage: Optional[str] = Field(None, max_length=32)
    source: Optional[str] = Field(None, max_length=64)
    custom_fields: Optional[dict[str, Any]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    owner_id: Optional[UUID] = Field(None)
    is_deleted: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)


# ── Custom Field Definition Schemas ─────────────────────────────────────────────
class CustomFieldDefinitionCreate(BaseModel):
    """Payload for creating a custom field definition."""
    name: str = Field(..., min_length=1, max_length=128)
    key: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None)
    field_type: str = Field(..., min_length=1, max_length=32, description="text, number, date, dropdown, multi_select, url")
    config: Optional[dict[str, Any]] = Field(default_factory=dict)
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
    description: Optional[str]
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
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    key: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None)
    field_type: Optional[str] = Field(None, min_length=1, max_length=32)
    config: Optional[dict[str, Any]] = Field(None)
    is_required: Optional[bool] = Field(None)
    is_active: Optional[bool] = Field(None)
    display_order: Optional[int] = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)


# ── Deal Schemas ───────────────────────────────────────────────────────────────
class DealCreate(BaseModel):
    """Payload for creating a new deal."""
    name: str = Field(..., min_length=1, max_length=512)
    value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field("USD", min_length=3, max_length=3)
    pipeline_stage_id: UUID = Field(..., description="Stage ID")
    contact_id: Optional[UUID] = Field(None, description="Associated contact ID")
    organization_label: Optional[str] = Field(None, max_length=256)
    owner_id: Optional[UUID] = Field(None)
    probability: Optional[float] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = Field(None)
    custom_fields: Optional[dict[str, Any]] = Field(None)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class DealResponse(BaseModel):
    """Deal representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    value: Optional[float]
    currency: str
    pipeline_stage_id: UUID
    contact_id: Optional[UUID]
    organization_label: Optional[str]
    owner_id: Optional[UUID]
    probability: Optional[float]
    expected_close_date: Optional[date]
    custom_fields: dict[str, Any]
    # Win/Loss tracking fields
    lost_reason: Optional[str] = Field(None)
    lost_at: Optional[datetime] = Field(None)
    won_reason: Optional[str] = Field(None)
    won_at: Optional[datetime] = Field(None)
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealUpdate(BaseModel):
    """Payload for updating a deal (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=512)
    value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    pipeline_stage_id: Optional[UUID] = Field(None)
    contact_id: Optional[UUID] = Field(None)
    organization_label: Optional[str] = Field(None, max_length=256)
    owner_id: Optional[UUID] = Field(None)
    probability: Optional[float] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = Field(None)
    custom_fields: Optional[dict[str, Any]] = Field(None)
    # Win/Loss tracking fields
    lost_reason: Optional[str] = Field(None)
    lost_at: Optional[datetime] = Field(None)
    won_reason: Optional[str] = Field(None)
    won_at: Optional[datetime] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class DealStageChangeRequest(BaseModel):
    """Payload for changing a deal's pipeline stage."""
    pipeline_stage_id: UUID = Field(..., description="Target stage ID")
    reason: Optional[str] = Field(None, max_length=500)  # General reason for stage change
    won_reason: Optional[str] = Field(None, max_length=500)  # Reason for winning (if stage is closed_won)
    lost_reason: Optional[str] = Field(None, max_length=500)  # Reason for losing (if stage is closed_lost)

    model_config = ConfigDict(from_attributes=True)


# ── Lead Score Schemas ─────────────────────────────────────────────────────────
class LeadScoreUpdate(BaseModel):
    """Payload for updating a lead score."""
    score: int = Field(..., ge=0, le=100, description="Score from 0 to 100")
    score_source: str = Field(..., description="Source of the score (ai, rule_based, manual, etc.)")
    scoring_factors: Optional[dict[str, Any]] = Field(None, description="Factors that contributed to the score")
    agent_id: Optional[UUID] = Field(None, description="AI agent or rule set that generated the score")

    model_config = ConfigDict(from_attributes=True)


class LeadScoreHistoryResponse(BaseModel):
    """Lead score history representation."""
    id: UUID
    tenant_id: UUID
    contact_id: UUID
    score: int = Field(..., ge=0, le=100)
    score_source: str
    scoring_factors: Optional[dict[str, Any]] = Field(None)
    agent_id: Optional[UUID] = Field(None)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Pipeline Schemas ───────────────────────────────────────────────────────────
class PipelineCreate(BaseModel):
    """Payload for creating a new pipeline."""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(None)
    is_default: bool = Field(False)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class PipelineResponse(BaseModel):
    """Pipeline representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    is_default: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── ActivityType Schemas (optional) ─────────────────────────────────────────────
class ActivityTypeCreate(BaseModel):
    """Payload for creating an activity type."""
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None)
    colour: Optional[str] = Field(None, max_length=7)  # hex color
    is_active: bool = Field(True)
    workspace_id: UUID = Field(..., description="Workspace ID")

    model_config = ConfigDict(from_attributes=True)


class ActivityTypeResponse(BaseModel):
    """Activity type representation."""
    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    colour: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityTypeUpdate(BaseModel):
    """Payload for updating an activity type (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None)
    colour: Optional[str] = Field(None, max_length=7)
    is_active: Optional[bool] = Field(None)

    model_config = ConfigDict(from_attributes=True)