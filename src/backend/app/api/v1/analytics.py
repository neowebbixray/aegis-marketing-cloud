"""
Analytics router: event tracking, metrics querying, dashboards, reports,
and legacy campaign/funnel analytics.

All list responses use the docs-mandated ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.core.exceptions import NotFoundException, ValidationException
from app.models.auth import User
from app.models.analytics import Dashboard, ScheduledReport
from app.schemas.analytics import (
    CampaignAnalyticsResponse,
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    EventCreate,
    EventResponse,
    FunnelAnalyticsResponse,
    ReportCreate,
    ReportGenerateResponse,
    ReportResponse,
    ReportUpdate,
    ScheduleReportRequest,
)
from app.schemas.base import build_list_response, build_single_response
from app.services.analytics import (
    AnalyticsService,
    CampaignAnalyticsService,
    DashboardService,
    FunnelAnalyticsService,
    ReportService,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ═══════════════════════════════════════════════════════════════════════════════
# Event Tracking
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/events", status_code=201)
async def track_event(
    body: EventCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track a single analytics event.

    Ingests the event, aggregates it into metric snapshots, and returns
    the stored event record.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    event = await service.track_event(tenant_id=tenant_id, event=body)
    return build_single_response(EventResponse.model_validate(event))


@router.post("/events/batch", status_code=201)
async def track_events_batch(
    body: list[EventCreate],
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Track multiple analytics events in a single batch (bulk ingest)."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    events = await service.track_events_bulk(tenant_id=tenant_id, events=body)
    return build_single_response({
        "ingested": len(events),
        "events": [EventResponse.model_validate(e).model_dump() for e in events],
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Metrics Querying
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/metrics/query")
async def query_metrics(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    metric_names: str = Query(..., description="Comma-separated metric names"),
    granularity: str = Query("day", pattern=r"^(hour|day|week|month)$"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict:
    """Query aggregated metric data points.

    Returns a dict mapping each metric name to its time-series data.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    names = [m.strip() for m in metric_names.split(",") if m.strip()]
    if not names:
        raise HTTPException(status_code=422, detail="At least one metric name is required")

    service = AnalyticsService(db)
    results = await service.query_metrics(
        tenant_id=tenant_id,
        metric_names=names,
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
    )
    return build_single_response({"metrics": results})


@router.get("/metrics/active-users")
async def get_active_users(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    period: int = Query(7, ge=1, le=365, description="Number of days to look back"),
) -> dict:
    """Get distinct active user counts per day for the given period."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    data = await service.get_active_users(tenant_id=tenant_id, period_days=period)
    return build_single_response({"period_days": period, "daily": data})


@router.get("/metrics/events-summary")
async def get_events_summary(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict:
    """Get event count summaries grouped by event name."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    now = datetime.now(timezone.utc)
    start = start_date or datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    end = end_date or now

    service = AnalyticsService(db)
    data = await service.get_events_summary(
        tenant_id=tenant_id,
        start_date=start,
        end_date=end,
    )
    return build_single_response({"start": start.isoformat(), "end": end.isoformat(), "events": data})


@router.get("/metrics/top-entities")
async def get_top_entities(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    entity_type: str = Query(..., max_length=100),
    metric: str = Query("count", max_length=100),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    """Get top entities by event count for a given entity type."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    data = await service.get_top_entities(
        tenant_id=tenant_id,
        entity_type=entity_type,
        metric=metric,
        limit=limit,
    )
    return build_single_response({"entity_type": entity_type, "metric": metric, "top": data})

# ── AI Usage Metrics ───────────────────────────────────────────────────────────
@router.get("/metrics/ai-usage")
async def get_ai_usage(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregate AI inference usage for the tenant.

    Returns total token usage, total cost, and execution count across all AI agent executions.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    # Simple aggregation query – use SQLAlchemy core for performance.
    from sqlalchemy import func, select
    from app.models.ai import AIAgentExecution

    stmt = select(
        func.count(AIAgentExecution.id),
        func.coalesce(func.sum(AIAgentExecution.tokens_used), 0),
        func.coalesce(func.sum(AIAgentExecution.cost), 0.0),
    ).where(AIAgentExecution.tenant_id == tenant_id)
    result = await db.execute(stmt)
    exec_count, total_tokens, total_cost = result.one()
    return build_single_response({
        "executions": exec_count,
        "total_tokens": total_tokens,
        "total_cost": float(total_cost),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboards
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboards")
async def list_dashboards(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List dashboards for the current tenant.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = AnalyticsService(db)
    items, total = await service.list_dashboards(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[DashboardResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/dashboards", status_code=201)
async def create_dashboard(
    body: DashboardCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new dashboard with optional widgets.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    widget_dicts = [w.model_dump() for w in body.widgets] if body.widgets else []
    dashboard = await service.create_dashboard(
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        widgets=widget_dicts,
        created_by=current_user.id,
    )
    return build_single_response(DashboardResponse.model_validate(dashboard))


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single dashboard with computed widget data.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    dashboard = await service.get_dashboard(
        tenant_id=tenant_id,
        dashboard_id=dashboard_id,
    )
    return build_single_response(DashboardResponse.model_validate(dashboard))


@router.patch("/dashboards/{dashboard_id}")
async def update_dashboard(
    dashboard_id: UUID,
    body: DashboardUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a dashboard's title, description, or widgets.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    updates = body.model_dump(exclude_unset=True)
    if "widgets" in updates and updates["widgets"] is not None:
        updates["widgets"] = [w.model_dump() if hasattr(w, "model_dump") else w for w in updates["widgets"]]
    dashboard = await service.update_dashboard(
        dashboard_id=dashboard_id,
        tenant_id=tenant_id,
        **updates,
    )
    return build_single_response(DashboardResponse.model_validate(dashboard))


@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a dashboard."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    await service.delete_dashboard(
        dashboard_id=dashboard_id,
        tenant_id=tenant_id,
    )
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reports")
async def list_reports(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    report_type: str | None = Query(None),
) -> dict:
    """List scheduled reports for the current tenant.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = ReportService(db)
    items, total = await service.list_reports(
        tenant_id=tenant_id,
        workspace_id=getattr(request.state, "workspace_id", None),
        skip=skip,
        limit=limit,
        report_type=report_type,
    )
    return build_list_response(
        data=[ReportResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/reports/generate", status_code=201)
async def generate_report(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    report_id: UUID = Query(..., description="ID of the report to generate"),
) -> dict:
    """Trigger immediate generation of a scheduled report.

    Computes metric data from ``MetricSnapshot`` based on the report's
    config and returns the generated data.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    result = await service.generate_report(
        tenant_id=tenant_id,
        report_id=report_id,
    )
    return build_single_response(result)


@router.post("/reports/schedule", status_code=200)
async def schedule_report(
    body: ScheduleReportRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set or update the cron schedule for a report.

    In production this also syncs with Celery Beat.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AnalyticsService(db)
    report = await service.schedule_report(
        report_id=body.report_id,
        cron_expression=body.cron_expression,
        tenant_id=tenant_id,
    )
    return build_single_response(ReportResponse.model_validate(report))


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Campaign & Funnel Analytics (kept for backwards compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/campaigns/{campaign_id}")
async def get_campaign_analytics(
    campaign_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get detailed analytics for a specific campaign.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = CampaignAnalyticsService(db)
    analytics = await service.get_campaign_analytics(
        campaign_id=campaign_id,
        tenant_id=tenant_id,
    )
    return build_single_response(analytics)


@router.get("/campaigns")
async def list_campaign_analytics(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
) -> dict:
    """List campaign analytics summaries.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = CampaignAnalyticsService(db)
    items, total = await service.list_campaign_analytics(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        status=status,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/funnels")
async def get_funnel_analytics(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    funnel_id: UUID | None = Query(None),
) -> dict:
    """Get funnel analytics with stage-by-stage conversion data.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = FunnelAnalyticsService(db)
    analytics = await service.get_funnel_analytics(
        tenant_id=tenant_id,
        funnel_id=funnel_id,
        workspace_id=workspace_id,
    )
    return build_single_response(analytics)
