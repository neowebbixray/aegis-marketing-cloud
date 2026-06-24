"""Analytics service: event tracking, metrics aggregation, dashboards, reports,
and analytical queries.

All tenant-scoped operations require a ``tenant_id`` UUID.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Date, and_, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.analytics import AnalyticsEvent, Dashboard, MetricSnapshot, ScheduledReport
from app.models.marketing import Campaign, Funnel
from app.schemas.analytics import EventCreate
from app.services.base import BaseService

logger = logging.getLogger("amc.services.analytics")


# ── Constants ────────────────────────────────────────────────────────────────

SUPPORTED_GRANULARITIES = {"hour", "day", "week", "month"}
DEFAULT_METRICS_TTL_DAYS = 90


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsService — comprehensive analytics pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class AnalyticsService:
    """High-level analytics operations for a single tenant context.

    Provides event ingestion, metric aggregation, dashboard management,
    report generation, and common analytical queries.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Event Tracking ─────────────────────────────────────────────────────

    async def track_event(
        self,
        tenant_id: UUID,
        event: EventCreate,
    ) -> AnalyticsEvent:
        """Ingest a single analytics event.

        The event is persisted to ``AnalyticsEvent`` and immediately
        aggregated into ``MetricSnapshot`` if it matches known metric
        patterns (e.g. counter-type events).
        """
        now = event.timestamp or datetime.now(UTC)
        db_event = AnalyticsEvent(
            tenant_id=tenant_id,
            user_id=event.user_id,
            session_id=event.session_id,
            event_name=event.event_name,
            properties=event.properties or {},
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            timestamp=now,
            processed=False,
        )
        self.db.add(db_event)
        await self.db.flush()
        await self.db.refresh(db_event)

        # Inline aggregation for simple counter metrics
        await self._aggregate_event(db_event)

        logger.debug("Tracked event '%s' for tenant %s", event.event_name, tenant_id)
        return db_event

    async def track_events_bulk(
        self,
        tenant_id: UUID,
        events: list[EventCreate],
    ) -> list[AnalyticsEvent]:
        """Ingest multiple analytics events in a single batch."""
        db_events: list[AnalyticsEvent] = []
        now = datetime.now(UTC)

        for event in events:
            ts = event.timestamp or now
            db_event = AnalyticsEvent(
                tenant_id=tenant_id,
                user_id=event.user_id,
                session_id=event.session_id,
                event_name=event.event_name,
                properties=event.properties or {},
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                timestamp=ts,
                processed=False,
            )
            self.db.add(db_event)
            db_events.append(db_event)

        await self.db.flush()

        for db_event in db_events:
            await self._aggregate_event(db_event)
            self.db.add(db_event)

        await self.db.flush()

        for db_event in db_events:
            await self.db.refresh(db_event)

        logger.info("Tracked %d events for tenant %s", len(events), tenant_id)
        return db_events

    async def _aggregate_event(self, event: AnalyticsEvent) -> None:
        """Aggregate a raw event into a ``MetricSnapshot`` record.

        Currently creates a simple counter snapshot for the event name
        keyed by hour.  More sophisticated aggregation (e.g. gauges,
        histograms, dimension roll-ups) can be added here.
        """
        # Truncate timestamp to hour for roll-up
        hour_start = event.timestamp.replace(minute=0, second=0, microsecond=0)

        snapshot = MetricSnapshot(
            tenant_id=event.tenant_id,
            metric_name=f"event.{event.event_name}.count",
            value=1.0,
            dimensions={
                "event_name": event.event_name,
                "entity_type": event.entity_type,
                "entity_id": str(event.entity_id) if event.entity_id else None,
                "user_id": str(event.user_id) if event.user_id else None,
            },
            timestamp=hour_start,
        )
        self.db.add(snapshot)

        # Mark event as processed
        event.processed = True

    # ── Metrics Querying ───────────────────────────────────────────────────

    async def query_metrics(
        self,
        tenant_id: UUID,
        metric_names: list[str],
        granularity: str = "day",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Query aggregated metric data points.

        Returns a dict mapping each metric name to a list of
        ``{timestamp, value, dimensions}`` data points.
        """
        if granularity not in SUPPORTED_GRANULARITIES:
            raise ValidationException(
                detail=f"Unsupported granularity '{granularity}'. "
                f"Must be one of: {', '.join(sorted(SUPPORTED_GRANULARITIES))}",
            )

        now = datetime.now(UTC)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now

        # Date-truncation expression for grouping
        trunc_map = {
            "hour": func.date_trunc("hour", MetricSnapshot.timestamp),
            "day": func.date_trunc("day", MetricSnapshot.timestamp),
            "week": func.date_trunc("week", MetricSnapshot.timestamp),
            "month": func.date_trunc("month", MetricSnapshot.timestamp),
        }
        trunc_expr = trunc_map[granularity]

        results: dict[str, list[dict[str, Any]]] = {}
        for metric_name in metric_names:
            stmt = (
                select(
                    trunc_expr.label("bucket"),
                    func.sum(MetricSnapshot.value).label("total"),
                )
                .where(
                    and_(
                        MetricSnapshot.tenant_id == tenant_id,
                        MetricSnapshot.metric_name == metric_name,
                        MetricSnapshot.timestamp >= start,
                        MetricSnapshot.timestamp <= end,
                    ),
                )
                .group_by("bucket")
                .order_by("bucket")
            )

            # Apply dimension filters if provided
            if filters:
                for dim_key, dim_value in filters.items():
                    # JSONB field access
                    stmt = stmt.where(
                        MetricSnapshot.dimensions[dim_key].as_string() == str(dim_value),
                    )

            result = await self.db.execute(stmt)
            rows = result.all()
            results[metric_name] = [
                {
                    "timestamp": row.bucket.isoformat()
                    if hasattr(row.bucket, "isoformat")
                    else str(row.bucket),
                    "value": float(row.total),
                    "dimensions": filters or {},
                }
                for row in rows
            ]

        return results

    # ── Dashboards ─────────────────────────────────────────────────────────

    async def get_dashboard(
        self,
        tenant_id: UUID,
        dashboard_id: UUID,
    ) -> Dashboard:
        """Fetch a dashboard and compute live data for each widget."""
        stmt = select(Dashboard).where(
            Dashboard.id == dashboard_id,
            Dashboard.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            raise NotFoundException(detail="Dashboard not found")

        # Enrich widgets with computed data
        enriched_widgets = []
        widgets = dashboard.widgets or []
        for widget in widgets:
            widget_data = dict(widget) if isinstance(widget, dict) else widget
            if isinstance(widget_data, dict):
                computed = await self._compute_widget_data(
                    tenant_id,
                    widget_data,
                )
                widget_data["data"] = computed
                enriched_widgets.append(widget_data)

        dashboard.widgets = enriched_widgets  # type: ignore[assignment]
        return dashboard

    async def _compute_widget_data(
        self,
        tenant_id: UUID,
        widget: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute live data for a single dashboard widget.

        Uses the widget's ``metric`` and ``config`` to query ``MetricSnapshot``.
        """
        metric = widget.get("metric", "")
        config = widget.get("config", {})
        if not metric:
            return {"value": None, "error": "No metric configured"}

        granularity = config.get("granularity", "day")
        days_back = config.get("days_back", 30)
        now = datetime.now(UTC)

        stmt = select(
            func.sum(MetricSnapshot.value).label("total"),
        ).where(
            and_(
                MetricSnapshot.tenant_id == tenant_id,
                MetricSnapshot.metric_name == metric,
                MetricSnapshot.timestamp >= (now - timedelta(days=days_back)),
            ),
        )
        # Apply optional dimension filter from widget config
        dimension_filter = config.get("dimension_filter")
        if dimension_filter and isinstance(dimension_filter, dict):
            for k, v in dimension_filter.items():
                stmt = stmt.where(
                    MetricSnapshot.dimensions[k].as_string() == str(v),
                )

        result = await self.db.execute(stmt)
        total = result.scalar() or 0.0

        return {
            "value": float(total),
            "metric": metric,
            "granularity": granularity,
            "period_days": days_back,
        }

    async def list_dashboards(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Dashboard], int]:
        """List dashboards for the tenant with pagination."""
        count_stmt = (
            select(func.count()).select_from(Dashboard).where(Dashboard.tenant_id == tenant_id)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            select(Dashboard)
            .where(Dashboard.tenant_id == tenant_id)
            .order_by(desc(Dashboard.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def create_dashboard(
        self,
        tenant_id: UUID,
        title: str,
        widgets: list[dict[str, Any]] | None = None,
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            tenant_id=tenant_id,
            title=title,
            description=description,
            widgets=widgets or [],
            created_by=created_by,
        )
        self.db.add(dashboard)
        await self.db.flush()
        await self.db.refresh(dashboard)
        logger.info("Created dashboard '%s' for tenant %s", title, tenant_id)
        return dashboard

    async def update_dashboard(
        self,
        dashboard_id: UUID,
        tenant_id: UUID,
        **updates: Any,
    ) -> Dashboard:
        """Update an existing dashboard."""
        stmt = select(Dashboard).where(
            Dashboard.id == dashboard_id,
            Dashboard.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            raise NotFoundException(detail="Dashboard not found")

        for key, value in updates.items():
            if value is not None:
                setattr(dashboard, key, value)

        await self.db.flush()
        await self.db.refresh(dashboard)
        logger.info("Updated dashboard %s for tenant %s", dashboard_id, tenant_id)
        return dashboard

    async def delete_dashboard(
        self,
        dashboard_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete a dashboard."""
        stmt = select(Dashboard).where(
            Dashboard.id == dashboard_id,
            Dashboard.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            raise NotFoundException(detail="Dashboard not found")

        await self.db.delete(dashboard)
        await self.db.flush()
        logger.info("Deleted dashboard %s for tenant %s", dashboard_id, tenant_id)

    # ── Reports ────────────────────────────────────────────────────────────

    async def generate_report(
        self,
        tenant_id: UUID,
        report_id: UUID,
    ) -> dict[str, Any]:
        """Generate a report by computing snapshot data.

        Queries the relevant ``MetricSnapshot`` records based on the
        report's config and returns the computed data without persisting
        it (the caller / Celery task is responsible for storage).
        """
        stmt = select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        report = result.scalars().first()
        if report is None:
            raise NotFoundException(detail="Scheduled report not found")

        config = report.config or {}
        metric_names = config.get("metric_names", [f"event.{report.report_type}.count"])
        granularity = config.get("granularity", "day")
        days_back = config.get("days_back", 30)
        now = datetime.now(UTC)

        metrics_data = await self.query_metrics(
            tenant_id=tenant_id,
            metric_names=metric_names,
            granularity=granularity,
            start_date=now - timedelta(days=days_back),
            end_date=now,
            filters=config.get("filters"),
        )

        # Update last_generated timestamp
        report.last_generated = now
        await self.db.flush()

        return {
            "report_id": str(report_id),
            "title": report.title,
            "report_type": report.report_type,
            "generated_at": now.isoformat(),
            "period": {
                "start": (now - timedelta(days=days_back)).isoformat(),
                "end": now.isoformat(),
            },
            "metrics": metrics_data,
            "config": config,
        }

    async def schedule_report(
        self,
        report_id: UUID,
        cron_expression: str,
        tenant_id: UUID | None = None,
    ) -> ScheduledReport:
        """Set or update the cron schedule for a report.

        In production this would also register/update a Celery Beat
        periodic task entry.
        """
        stmt = select(ScheduledReport).where(ScheduledReport.id == report_id)
        if tenant_id:
            stmt = stmt.where(ScheduledReport.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        report = result.scalars().first()
        if report is None:
            raise NotFoundException(detail="Scheduled report not found")

        report.schedule = cron_expression
        await self.db.flush()
        await self.db.refresh(report)

        logger.info(
            "Scheduled report %s with cron '%s'",
            report_id,
            cron_expression,
        )
        return report

    # ── Analytical Queries ─────────────────────────────────────────────────

    async def get_active_users(
        self,
        tenant_id: UUID,
        period_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get distinct active user counts per day for the given period."""
        now = datetime.now(UTC)
        start = now - timedelta(days=period_days)

        # Truncate to day
        day_expr = cast(
            func.date_trunc("day", AnalyticsEvent.timestamp),
            Date,
        )

        stmt = (
            select(
                day_expr.label("date"),
                func.count(func.distinct(AnalyticsEvent.user_id)).label("active_users"),
            )
            .where(
                and_(
                    AnalyticsEvent.tenant_id == tenant_id,
                    AnalyticsEvent.timestamp >= start,
                    AnalyticsEvent.user_id.isnot(None),
                ),
            )
            .group_by("date")
            .order_by("date")
        )

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "date": str(row.date),
                "active_users": row.active_users,
            }
            for row in rows
        ]

    async def get_events_summary(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get event count summaries grouped by event name."""
        stmt = (
            select(
                AnalyticsEvent.event_name,
                func.count(AnalyticsEvent.id).label("count"),
            )
            .where(
                and_(
                    AnalyticsEvent.tenant_id == tenant_id,
                    AnalyticsEvent.timestamp >= start_date,
                    AnalyticsEvent.timestamp <= end_date,
                ),
            )
            .group_by(AnalyticsEvent.event_name)
            .order_by(desc("count"))
        )

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "event_name": row.event_name,
                "count": row.count,
            }
            for row in rows
        ]

    async def get_top_entities(
        self,
        tenant_id: UUID,
        entity_type: str,
        metric: str = "count",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top entities by event count for a given entity type."""
        metric_name = f"event.{metric}.count" if not metric.startswith("event.") else metric

        stmt = (
            select(
                MetricSnapshot.dimensions["entity_id"].as_string().label("entity_id"),
                func.sum(MetricSnapshot.value).label("total"),
            )
            .where(
                and_(
                    MetricSnapshot.tenant_id == tenant_id,
                    MetricSnapshot.metric_name == metric_name,
                    MetricSnapshot.dimensions["entity_type"].as_string() == entity_type,
                ),
            )
            .group_by("entity_id")
            .order_by(desc("total"))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "entity_id": row.entity_id,
                f"total_{metric}": float(row.total),
            }
            for row in rows
            if row.entity_id
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Services (kept for backwards compatibility with existing router)
# ═══════════════════════════════════════════════════════════════════════════════


class CampaignAnalyticsService:
    """Compute and retrieve analytics for marketing campaigns."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_campaign_analytics(
        self,
        campaign_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Get detailed analytics for a specific campaign."""
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
                Campaign.deleted_at.is_(None),
            ),
        )
        campaign = result.scalars().first()
        if campaign is None:
            raise NotFoundException(detail="Campaign not found")

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "status": campaign.status,
            "total_sent": 0,
            "total_delivered": 0,
            "total_opened": 0,
            "total_clicked": 0,
            "total_bounced": 0,
            "total_unsubscribed": 0,
            "total_converted": 0,
            "open_rate": None,
            "click_through_rate": None,
            "conversion_rate": None,
            "bounce_rate": None,
            "revenue_generated": None,
            "roi": None,
            "daily_breakdown": [],
            "metadata": campaign.metrics or {},
        }

    async def list_campaign_analytics(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List campaign analytics summaries."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total


class FunnelAnalyticsService:
    """Compute funnel-stage conversion analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_funnel_analytics(
        self,
        tenant_id: UUID,
        funnel_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Get funnel analytics with stage-by-stage conversion data."""
        if funnel_id:
            result = await self.db.execute(
                select(Funnel).where(
                    Funnel.id == funnel_id,
                    Funnel.tenant_id == tenant_id,
                    Funnel.deleted_at.is_(None),
                ),
            )
            funnel = result.scalars().first()
            if funnel is None:
                raise NotFoundException(detail="Funnel not found")

            return {
                "funnel_id": funnel_id,
                "funnel_name": funnel.name,
                "total_entries": 0,
                "total_conversions": 0,
                "overall_conversion_rate": None,
                "stages": [],
                "average_time_to_convert": None,
            }

        return []


class ReportService(BaseService):
    """Create, schedule, and manage custom analytics reports.

    Wraps the new ``ScheduledReport`` model with the legacy ``BaseService``
    CRUD interface for backwards compatibility.
    """

    model = ScheduledReport

    async def create_report(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        name: str,
        report_type: str,
        config: dict[str, Any],
        description: str | None = None,
        schedule: str | None = None,
        recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new custom analytics report."""
        report = ScheduledReport(
            tenant_id=tenant_id,
            title=name,
            report_type=report_type,
            config=config,
            schedule=schedule,
            recipients=recipients or [],
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)

        logger.info("Created report '%s' (type=%s) for tenant %s", name, report_type, tenant_id)
        return {
            "id": str(report.id),
            "name": report.title,
            "description": description,
            "report_type": report.report_type,
            "config": report.config,
            "schedule": report.schedule,
            "recipients": report.recipients,
            "status": "active",
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }

    async def list_reports(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        report_type: str | None = None,
    ) -> tuple[list[ScheduledReport], int]:
        """List custom reports."""
        stmt = select(ScheduledReport).where(
            ScheduledReport.tenant_id == tenant_id,
        )
        if report_type:
            stmt = stmt.where(ScheduledReport.report_type == report_type)
        stmt = stmt.order_by(desc(ScheduledReport.created_at)).offset(skip).limit(limit)

        count_stmt = (
            select(func.count())
            .select_from(ScheduledReport)
            .where(
                ScheduledReport.tenant_id == tenant_id,
            )
        )
        if report_type:
            count_stmt = count_stmt.where(ScheduledReport.report_type == report_type)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_report(self, report_id: UUID, tenant_id: UUID) -> ScheduledReport:
        """Fetch a single report."""
        stmt = select(ScheduledReport).where(
            ScheduledReport.id == report_id,
            ScheduledReport.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        report = result.scalars().first()
        if report is None:
            raise NotFoundException(detail="Report not found")
        return report

    async def update_report(
        self,
        report_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> ScheduledReport:
        """Update a custom report."""
        report = await self.get_report(report_id, tenant_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(report, key, value)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def delete_report(self, report_id: UUID, tenant_id: UUID) -> None:
        """Delete a custom report."""
        report = await self.get_report(report_id, tenant_id)
        await self.db.delete(report)
        await self.db.flush()
        logger.info("Deleted report %s for tenant %s", report_id, tenant_id)


class DashboardService(BaseService):
    """Manage dashboards and widgets.

    Provides a legacy interface for the existing dashboard widget
    endpoints, backed by the new ``Dashboard`` model.
    """

    model = Dashboard

    async def create_widget(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        title: str,
        widget_type: str,
        config: dict[str, Any],
        position: int = 0,
        size: str = "medium",
    ) -> dict[str, Any]:
        """Add a new widget to the tenant's primary dashboard.

        NOTE: This legacy method creates a single-widget dashboard if
        none exists.  The new ``AnalyticsService.create_dashboard`` is
        preferred.
        """
        # Find or create a default dashboard
        stmt = select(Dashboard).where(Dashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()

        if dashboard is None:
            dashboard = Dashboard(
                tenant_id=tenant_id,
                title="Default Dashboard",
                widgets=[],
            )
            self.db.add(dashboard)
            await self.db.flush()

        widget_entry = {
            "widget_id": str(UUID(int=0)),  # placeholder
            "type": widget_type,
            "title": title,
            "config": config,
            "position": position,
            "size": size,
        }
        widgets = list(dashboard.widgets or [])
        widgets.append(widget_entry)
        dashboard.widgets = widgets
        await self.db.flush()

        logger.info("Created dashboard widget '%s' (%s)", title, widget_type)
        return widget_entry

    async def list_widgets(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """List all dashboard widgets for the tenant."""
        stmt = select(Dashboard).where(Dashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        return list(dashboard.widgets or []) if dashboard else []

    async def update_widget(
        self,
        widget_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a dashboard widget."""
        stmt = select(Dashboard).where(Dashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            raise NotFoundException(detail="No dashboard found")

        widgets = list(dashboard.widgets or [])
        for i, w in enumerate(widgets):
            if isinstance(w, dict) and w.get("widget_id") == str(widget_id):
                for k, v in kwargs.items():
                    if v is not None:
                        widgets[i][k] = v
                dashboard.widgets = widgets
                await self.db.flush()
                return w

        raise NotFoundException(detail="Widget not found")

    async def delete_widget(self, widget_id: UUID, tenant_id: UUID) -> None:
        """Remove a widget from the dashboard."""
        stmt = select(Dashboard).where(Dashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            raise NotFoundException(detail="No dashboard found")

        widgets = [
            w
            for w in (dashboard.widgets or [])
            if not (isinstance(w, dict) and w.get("widget_id") == str(widget_id))
        ]
        dashboard.widgets = widgets
        await self.db.flush()
        logger.info("Deleted dashboard widget %s", widget_id)

    async def get_dashboard_data(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """Fetch rendered data for all dashboard widgets."""
        stmt = select(Dashboard).where(Dashboard.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalars().first()
        if dashboard is None:
            return {"widgets": []}

        return {
            "id": str(dashboard.id),
            "title": dashboard.title,
            "description": dashboard.description,
            "widgets": list(dashboard.widgets or []),
        }
