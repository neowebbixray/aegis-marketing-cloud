"""
Pydantic schemas for the CRM module: contacts, deals, pipelines, activities.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Contact ──────────────────────────────────────────────────────────────────
class ContactCreate(BaseModel):
    """Payload for POST /contacts."""

    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)
    company: Optional[str] = Field(None, max_length=256)
    position: Optional[str] = Field(None, max_length=256)
    lifecycle_stage: str = Field(default="lead", max_length=32)
    source: Optional[str] = Field(None, max_length=64)
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    owner_id: Optional[UUID] = None


class ContactUpdate(BaseModel):
    """Payload for PATCH /contacts/{id}. All fields optional."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=128)
    last_name: Optional[str] = Field(None, min_length=1, max_length=128)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)
    company: Optional[str] = Field(None, max_length=256)
    position: Optional[str] = Field(None, max_length=256)
    lifecycle_stage: Optional[str] = Field(None, max_length=32)
    source: Optional[str] = Field(None, max_length=64)
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    owner_id: Optional[UUID] = None


class ContactResponse(BaseModel):
    """Contact representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    lifecycle_stage: str
    source: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    owner_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    """Paginated list of contacts."""

    items: list[ContactResponse]
    total: int
    page: int = 1
    page_size: int = 50


# ── Deal ─────────────────────────────────────────────────────────────────────
class DealCreate(BaseModel):
    """Payload for POST /deals."""

    name: str = Field(..., min_length=1, max_length=512)
    value: Optional[Decimal] = Field(None, ge=0)
    currency: str = "USD"
    pipeline_stage_id: UUID
    contact_id: Optional[UUID] = None
    organization_label: Optional[str] = Field(None, max_length=256)
    owner_id: Optional[UUID] = None
    probability: Optional[float] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = None
    custom_fields: Optional[dict[str, Any]] = None


class DealUpdate(BaseModel):
    """Payload for PATCH /deals/{id}. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=512)
    value: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = None
    pipeline_stage_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    organization_label: Optional[str] = Field(None, max_length=256)
    owner_id: Optional[UUID] = None
    probability: Optional[float] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = None
    custom_fields: Optional[dict[str, Any]] = None


class DealStageChangeRequest(BaseModel):
    """Payload for PATCH /deals/{id}/stage."""

    pipeline_stage_id: UUID
    reason: Optional[str] = Field(None, max_length=512)


class DealResponse(BaseModel):
    """Deal representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    value: Optional[Decimal] = None
    currency: str
    pipeline_stage_id: UUID
    contact_id: Optional[UUID] = None
    organization_label: Optional[str] = None
    owner_id: Optional[UUID] = None
    probability: Optional[float] = None
    expected_close_date: Optional[date] = None
    custom_fields: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Pipeline ─────────────────────────────────────────────────────────────────
class PipelineStageCreate(BaseModel):
    """Payload for creating a pipeline stage."""

    name: str = Field(..., min_length=1, max_length=256)
    order: int = 0
    probability: Optional[float] = Field(None, ge=0, le=100)
    colour: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class PipelineCreate(BaseModel):
    """Payload for POST /pipelines."""

    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    is_default: bool = False
    stages: Optional[list[PipelineStageCreate]] = None


class PipelineStageResponse(BaseModel):
    """Pipeline stage representation."""

    id: UUID
    pipeline_id: UUID
    name: str
    order: int
    probability: Optional[float] = None
    colour: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineResponse(BaseModel):
    """Pipeline representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    stages: Optional[list[PipelineStageResponse]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Activity ─────────────────────────────────────────────────────────────────
class ActivityCreate(BaseModel):
    """Payload for POST /activities."""

    type: str = Field(..., pattern=r"^(note|call|email|meeting|task)$")
    subject: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    contact_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class ActivityResponse(BaseModel):
    """Activity representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    type: str
    subject: str
    description: Optional[str] = None
    contact_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
