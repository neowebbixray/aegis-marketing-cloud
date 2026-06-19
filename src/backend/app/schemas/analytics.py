"""
Pydantic schemas for the Analytics module: campaign analytics, funnel analytics,
custom reports, dashboard widgets.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Campaign Analytics ──────────────────────────────────────────────────────
class CampaignAnalyticsResponse(BaseModel):
    """Detailed analytics for a single campaign."""

    campaign_id: UUID
    campaign_name: str
    status: str
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    total_unsubscribed: int = 0
    total_converted: int = 0
    open_rate: Optional[float] = None
    click_through_rate: Optional[float] = None
    conversion_rate: Optional[float] = None
    bounce_rate: Optional[float] = None
    revenue_generated: Optional[float] = None
    roi: Optional[float] = None
    daily_breakdown: Optional[list[dict[str, Any]]] = None
    metadata: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


# ── Funnel Analytics ────────────────────────────────────────────────────────
class FunnelAnalyticsResponse(BaseModel):
    """Funnel analytics with stage-by-stage conversion."""

    funnel_id: UUID
    funnel_name: str
    total_entries: int = 0
    total_conversions: int = 0
    overall_conversion_rate: Optional[float] = None
    stages: Optional[list[dict[str, Any]]] = None  # [{name, entries, exits, conversion_rate}]
    average_time_to_convert: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Custom Reports ──────────────────────────────────────────────────────────
class ReportCreate(BaseModel):
    """Payload for POST /analytics/reports."""

    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    report_type: str = Field(..., max_length=64)  # campaign, funnel, seo, social, custom
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = Field(None, max_length=32)  # daily, weekly, monthly, none
    recipients: Optional[list[str]] = None  # email addresses


class ReportUpdate(BaseModel):
    """Payload for PATCH /analytics/reports/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    schedule: Optional[str] = Field(None, max_length=32)
    recipients: Optional[list[str]] = None


class ReportResponse(BaseModel):
    """Custom report representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    report_type: str
    config: dict[str, Any]
    schedule: Optional[str] = None
    last_generated_at: Optional[datetime] = None
    last_data: Optional[dict[str, Any]] = None
    recipients: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard Widgets ───────────────────────────────────────────────────────
class DashboardWidgetCreate(BaseModel):
    """Payload for creating a dashboard widget."""

    title: str = Field(..., min_length=1, max_length=128)
    widget_type: str = Field(..., max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    position: int = 0
    size: str = Field(default="medium", max_length=16)  # small, medium, large, full


class DashboardWidgetResponse(BaseModel):
    """Dashboard widget representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    title: str
    widget_type: str
    config: dict[str, Any]
    position: int
    size: str
    data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
