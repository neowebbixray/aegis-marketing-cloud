"""Pydantic schemas for the Analytics module: event tracking, metrics querying,
dashboards, and scheduled reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Event Tracking ───────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    """Payload for POST /analytics/events — track a single event."""

    event_name: str = Field(..., min_length=1, max_length=255)
    properties: dict[str, Any] = Field(default_factory=dict)
    entity_type: str | None = Field(None, max_length=100)
    entity_id: UUID | None = None
    user_id: UUID | None = None
    session_id: str | None = Field(None, max_length=255)
    timestamp: datetime | None = None  # defaults to server time


class EventResponse(BaseModel):
    """Event representation returned after ingestion."""

    id: UUID
    tenant_id: UUID
    event_name: str
    properties: dict[str, Any] | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    user_id: UUID | None = None
    session_id: str | None = None
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
    description: str | None = None
    unit: str | None = None
    aggregation: str = Field(default="sum")  # sum | avg | min | max | count | distinct


class MetricQuery(BaseModel):
    """Query parameters for fetching metric data points."""

    metric_names: list[str] = Field(..., min_length=1)
    granularity: str = Field(default="hour")  # hour | day | week | month
    start_date: datetime
    end_date: datetime
    filters: dict[str, Any] | None = None  # dimension filters


class MetricDataPoint(BaseModel):
    """A single time-series data point for a metric."""

    timestamp: datetime
    value: float
    dimensions: dict[str, Any] | None = None


# ── Dashboards ───────────────────────────────────────────────────────────────


class WidgetConfig(BaseModel):
    """A single dashboard widget's inline configuration."""

    widget_id: str | None = None
    type: str = Field(..., max_length=64)  # chart, number, table, etc.
    title: str = Field(..., max_length=128)
    metric: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, Any] = Field(
        default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4},
        description="Grid position: {x, y, w, h}",
    )
    size: str = Field(default="medium", max_length=16)  # small, medium, large, full


class DashboardCreate(BaseModel):
    """Payload for POST /analytics/dashboards."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    widgets: list[WidgetConfig] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    """Payload for PATCH /analytics/dashboards/{id}."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    widgets: list[WidgetConfig] | None = None


class DashboardResponse(BaseModel):
    """Dashboard representation with inline widget data."""

    id: UUID
    tenant_id: UUID
    title: str
    description: str | None = None
    widgets: list[dict[str, Any]] | None = None  # data-enriched widgets
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ──────────────────────────────────────────────────────────────────


class ReportCreate(BaseModel):
    """Payload for creating a scheduled report definition."""

    title: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = Field(None, max_length=100)  # cron expression
    recipients: list[str] | None = None  # email addresses


class ReportUpdate(BaseModel):
    """Payload for updating a scheduled report."""

    title: str | None = Field(None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    schedule: str | None = Field(None, max_length=100)
    recipients: list[str] | None = None


class ReportResponse(BaseModel):
    """Scheduled report representation."""

    id: UUID
    tenant_id: UUID
    title: str
    report_type: str
    config: dict[str, Any]
    schedule: str | None = None
    recipients: list[str] | None = None
    last_generated: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportGenerateResponse(BaseModel):
    """Response returned after triggering report generation."""

    report_id: UUID
    status: str  # queued, generating, completed, failed
    task_id: str | None = None
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
    open_rate: float | None = None
    click_through_rate: float | None = None
    conversion_rate: float | None = None
    bounce_rate: float | None = None
    revenue_generated: float | None = None
    roi: float | None = None
    daily_breakdown: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class FunnelAnalyticsResponse(BaseModel):
    """Funnel analytics with stage-by-stage conversion."""

    funnel_id: UUID
    funnel_name: str
    total_entries: int = 0
    total_conversions: int = 0
    overall_conversion_rate: float | None = None
    stages: list[dict[str, Any]] | None = None
    average_time_to_convert: float | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    model_config = {"from_attributes": True}
