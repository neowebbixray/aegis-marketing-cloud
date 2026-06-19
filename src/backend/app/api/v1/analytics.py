"""
Analytics router: campaign analytics, funnel analytics, custom reports,
dashboard widgets.

All list responses use the docs-mandated ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.analytics import (
    CampaignAnalyticsResponse,
    FunnelAnalyticsResponse,
    ReportCreate,
    ReportResponse,
    ReportUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
)
from app.services.analytics import (
    CampaignAnalyticsService,
    DashboardService,
    FunnelAnalyticsService,
    ReportService,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Campaign Analytics ──────────────────────────────────────────────────────


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


# ── Funnel Analytics ────────────────────────────────────────────────────────


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


# ── Custom Reports ──────────────────────────────────────────────────────────


@router.post("/reports", status_code=201)
async def create_report(
    body: ReportCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new custom analytics report.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = ReportService(db)
    report = await service.create_report(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        report_type=body.report_type,
        config=body.config,
        schedule=body.schedule,
        recipients=body.recipients,
    )
    return build_single_response(report)


@router.get("/reports")
async def list_reports(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    report_type: str | None = Query(None),
) -> dict:
    """List custom analytics reports.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = ReportService(db)
    items, total = await service.list_reports(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        report_type=report_type,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single custom report with its latest data.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ReportService(db)
    report = await service.get_report(report_id, tenant_id=tenant_id)
    return build_single_response(report)


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: UUID,
    body: ReportUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a custom analytics report.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ReportService(db)
    report = await service.update_report(
        report_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(report)


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom analytics report."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ReportService(db)
    await service.delete_report(report_id, tenant_id=tenant_id)
    return None


# ── Dashboard Widgets ───────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the dashboard with all widget data.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = DashboardService(db)
    dashboard = await service.get_dashboard_data(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    return build_single_response(dashboard)


@router.post("/dashboard/widgets", status_code=201)
async def create_widget(
    body: DashboardWidgetCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a new widget to the dashboard.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = DashboardService(db)
    widget = await service.create_widget(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title=body.title,
        widget_type=body.widget_type,
        config=body.config,
        position=body.position,
        size=body.size,
    )
    return build_single_response(widget)


@router.get("/dashboard/widgets")
async def list_widgets(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all dashboard widgets.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = DashboardService(db)
    widgets = await service.list_widgets(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    return build_single_response({"widgets": widgets})


@router.patch("/dashboard/widgets/{widget_id}")
async def update_widget(
    widget_id: UUID,
    body: DashboardWidgetCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a dashboard widget.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DashboardService(db)
    widget = await service.update_widget(
        widget_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(widget)


@router.delete("/dashboard/widgets/{widget_id}", status_code=204)
async def delete_widget(
    widget_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a widget from the dashboard."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DashboardService(db)
    await service.delete_widget(widget_id, tenant_id=tenant_id)
    return None
