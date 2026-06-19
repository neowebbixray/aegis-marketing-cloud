"""
Pydantic schemas for the Analytics module: event tracking, metrics querying,
dashboards, and scheduled reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Event Tracking ───────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    """Payload for POST /analytics/events — track a single event."""

    event_name: str = Field(..., min_length=1, max_length=255)
    properties: dict[str, Any] = Field(default_factory=dict)
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    session_id: Optional[str] = Field(None, max_length=255)
    timestamp: Optional[datetime] = None  # defaults to server time


class EventResponse(BaseModel):
    """Event representation returned after ingestion."""

    id: UUID
    tenant_id: UUID
    event_name: str
    properties: Optional[dict[str, Any]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    session_id: Optional[str] = None
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """Paginated list of events."""

    items: list[EventResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


# ── Metrics ──────────────────────────────────────────────────────────────────

class MetricDefinition(BaseModel):
    """Definition of a tracked metric with its metadata."""

    name: str = Field(..., max_length=255)
    type: str = Field(default="counter")  # counter | gauge | histogram
    description: Optional[str] = None
    unit: Optional[str] = None
    aggregation: str = Field(default="sum")  # sum | avg | min | max | count | distinct


class MetricQuery(BaseModel):
    """Query parameters for fetching metric data points."""

    metric_names: list[str] = Field(..., min_length=1)
    granularity: str = Field(default="hour")  # hour | day | week | month
    start_date: datetime
    end_date: datetime
    filters: Optional[dict[str, Any]] = None  # dimension filters


class MetricDataPoint(BaseModel):
    """A single time-series data point for a metric."""

    timestamp: datetime
    value: float
    dimensions: Optional[dict[str, Any]] = None


# ── Dashboards ───────────────────────────────────────────────────────────────

class WidgetConfig(BaseModel):
    """A single dashboard widget's inline configuration."""

    widget_id: Optional[str] = None
    type: str = Field(..., max_length=64)  # chart, number, table, etc.
    title: str = Field(..., max_length=128)
    metric: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    position: int = 0
    size: str = Field(default="medium", max_length=16)  # small, medium, large, full


class DashboardCreate(BaseModel):
    """Payload for POST /analytics/dashboards."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    widgets: list[WidgetConfig] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    """Payload for PATCH /analytics/dashboards/{id}."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    widgets: Optional[list[WidgetConfig]] = None


class DashboardResponse(BaseModel):
    """Dashboard representation with inline widget data."""

    id: UUID
    tenant_id: UUID
    title: str
    description: Optional[str] = None
    widgets: Optional[list[dict[str, Any]]] = None  # data-enriched widgets
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ──────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    """Payload for creating a scheduled report definition."""

    title: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = Field(None, max_length=100)  # cron expression
    recipients: Optional[list[str]] = None  # email addresses


class ReportUpdate(BaseModel):
    """Payload for updating a scheduled report."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict[str, Any]] = None
    schedule: Optional[str] = Field(None, max_length=100)
    recipients: Optional[list[str]] = None


class ReportResponse(BaseModel):
    """Scheduled report representation."""

    id: UUID
    tenant_id: UUID
    title: str
    report_type: str
    config: dict[str, Any]
    schedule: Optional[str] = None
    recipients: Optional[list[str]] = None
    last_generated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportGenerateResponse(BaseModel):
    """Response returned after triggering report generation."""

    report_id: UUID
    status: str  # queued, generating, completed, failed
    task_id: Optional[str] = None
    detail: str = "Report generation queued."


class ScheduleReportRequest(BaseModel):
    """Payload for POST /analytics/reports/schedule."""

    report_id: UUID
    cron_expression: str = Field(..., max_length=100)


# ── Existing Campaign & Funnel Analytics (kept for backwards compat) ─────────

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


class FunnelAnalyticsResponse(BaseModel):
    """Funnel analytics with stage-by-stage conversion."""

    funnel_id: UUID
    funnel_name: str
    total_entries: int = 0
    total_conversions: int = 0
    overall_conversion_rate: Optional[float] = None
    stages: Optional[list[dict[str, Any]]] = None
    average_time_to_convert: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    model_config = {"from_attributes": True}
