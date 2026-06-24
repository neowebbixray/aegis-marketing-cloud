"""Analytics models — events, metric snapshots, dashboards, scheduled reports.

All models are multi-tenant (tenant_id scoped).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AnalyticsEvent(BaseModel):
    """Raw analytics event for tracking user actions and system events.

    Stores arbitrary event data with optional entity association for
    drill-down analysis. The ``processed`` flag is set to ``True`` after
    the event has been aggregated into ``MetricSnapshot`` records.
    """

    __tablename__ = "analytics_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_name} @ {self.timestamp}>"


class MetricSnapshot(BaseModel):
    """Pre-aggregated metric data point for efficient querying.

    Populated by the aggregation pipeline after events are ingested.
    Dimensions are stored as a JSONB dict for flexible filtering
    (e.g. ``{"entity_type": "campaign", "channel": "email"}``).
    """

    __tablename__ = "metric_snapshots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<MetricSnapshot {self.metric_name}={self.value} @ {self.timestamp}>"


class Dashboard(BaseModel):
    """User-defined dashboard with widget configuration.

    Widgets are stored as a JSONB array of objects, each containing
    ``widget_id``, ``type``, ``title``, ``config``, ``position``, and ``size``.
    """

    __tablename__ = "dashboards"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    widgets: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Dashboard {self.title}>"


class ScheduledReport(BaseModel):
    """Scheduled report definition with cron expression and recipient list.

    When ``schedule`` is set, a background Celery task generates the
    report and delivers it to the configured recipients.
    """

    __tablename__ = "scheduled_reports"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)  # cron expression
    recipients: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    last_generated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ScheduledReport {self.title} ({self.report_type})>"
