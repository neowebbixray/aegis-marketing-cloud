"""
Analytics service: campaign analytics, funnel analytics, custom reports,
dashboard widgets.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.marketing import Campaign, Funnel
from app.services.base import BaseService

logger = logging.getLogger("amc.services.analytics")


class CampaignAnalyticsService:
    """Compute and retrieve analytics for marketing campaigns."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_campaign_analytics(
        self,
        campaign_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Get detailed analytics for a specific campaign.

        Computes metrics from campaign events including opens, clicks,
        conversions, bounces, and revenue data.
        """
        # Fetch the campaign
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
                Campaign.deleted_at.is_(None),
            )
        )
        campaign = result.scalars().first()
        if campaign is None:
            raise NotFoundException(detail="Campaign not found")

        # Stub: compute from campaign metrics JSONB and events table
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
        """Get funnel analytics with stage-by-stage conversion data.

        Args:
            funnel_id: Specific funnel to analyse (omit for all funnels summary).
            workspace_id: Optional workspace filter.

        Returns a single funnel analytics dict if funnel_id is given,
        otherwise a list of funnel summaries.
        """
        if funnel_id:
            result = await self.db.execute(
                select(Funnel).where(
                    Funnel.id == funnel_id,
                    Funnel.tenant_id == tenant_id,
                    Funnel.deleted_at.is_(None),
                )
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
    """Create, schedule, and manage custom analytics reports."""

    model = Campaign

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
        report = {
            "name": name,
            "description": description,
            "report_type": report_type,
            "config": config,
            "schedule": schedule,
            "recipients": recipients or [],
            "status": "active",
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }
        logger.info("Created report '%s' (type=%s) for workspace %s",
                     name, report_type, workspace_id)
        # TODO: persist to reports table
        return report

    async def list_reports(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        report_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List custom reports."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_report(self, report_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Fetch a single report with its latest data."""
        raise NotFoundException(detail="Report not found")

    async def update_report(
        self,
        report_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a custom report."""
        return {}

    async def delete_report(self, report_id: UUID, tenant_id: UUID) -> None:
        """Delete a custom report."""
        logger.info("Deleted report %s", report_id)


class DashboardService(BaseService):
    """Manage dashboard widgets and layout."""

    model = Campaign

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
        """Add a new widget to the dashboard."""
        widget = {
            "title": title,
            "widget_type": widget_type,
            "config": config,
            "position": position,
            "size": size,
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }
        logger.info("Created dashboard widget '%s' (%s)", title, widget_type)
        return widget

    async def list_widgets(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """List all dashboard widgets for the workspace."""
        return []

    async def update_widget(
        self,
        widget_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a dashboard widget."""
        return {}

    async def delete_widget(self, widget_id: UUID, tenant_id: UUID) -> None:
        """Remove a widget from the dashboard."""
        logger.info("Deleted dashboard widget %s", widget_id)

    async def get_dashboard_data(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """Fetch rendered data for all dashboard widgets."""
        return {"widgets": []}
