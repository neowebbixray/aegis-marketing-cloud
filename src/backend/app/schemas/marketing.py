"""Marketing Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    campaign_type: str = "email"
    status: str = "draft"
    channel: str | None = None
    budget: Decimal | None = None
    target_audience: dict | None = None
    schedule_start: datetime | None = None
    schedule_end: datetime | None = None
    ai_optimized: bool = False
    metrics: dict | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    campaign_type: str | None = None
    status: str | None = None
    channel: str | None = None
    budget: Decimal | None = None
    target_audience: dict | None = None
    schedule_start: datetime | None = None
    schedule_end: datetime | None = None
    ai_optimized: bool | None = None
    metrics: dict | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    campaign_type: str
    status: str
    channel: str | None
    budget: Decimal | None
    target_audience: dict | None
    schedule_start: datetime | None
    schedule_end: datetime | None
    ai_optimized: bool
    metrics: dict | None
    tenant_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str
    body_text: str | None = None
    category: str | None = None
    preheader: str | None = None
    variables: list | None = None


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    category: str | None = None
    preheader: str | None = None
    variables: list | None = None


class EmailTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    subject: str
    body_html: str
    body_text: str | None
    category: str | None
    preheader: str | None
    variables: list | None
    tenant_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class FunnelCreate(BaseModel):
    name: str
    description: str | None = None
    steps: list = []
    ai_optimized: bool = False


class FunnelUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list | None = None
    ai_optimized: bool | None = None


class FunnelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    steps: list
    conversion_rate: Decimal | None
    ai_optimized: bool
    tenant_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class LandingPageCreate(BaseModel):
    title: str
    slug: str
    content: dict = {}
    status: str = "draft"
    seo_meta: dict | None = None
    ai_generated: bool = False


class LandingPageUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: dict | None = None
    status: str | None = None
    seo_meta: dict | None = None
    ai_generated: bool | None = None


class LandingPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    slug: str
    content: dict
    published_url: str | None
    status: str
    seo_meta: dict | None
    ai_generated: bool
    version: int
    tenant_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SegmentCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: dict = {}
    is_dynamic: bool = True


class SegmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: dict | None = None
    is_dynamic: bool | None = None


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    criteria: dict
    contact_count: int
    is_dynamic: bool
    tenant_id: UUID
    workspace_id: UUID | None
    created_at: datetime
    updated_at: datetime
