"""Marketing service classes — CampaignService, EmailTemplateService, LandingPageService, FunnelService, SegmentService."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select

from app.models.marketing import Campaign, EmailTemplate, Funnel, LandingPage, Segment
from app.services.base import BaseService

logger = logging.getLogger("amc.services.marketing")


class CampaignService(BaseService[Campaign]):
    """CRUD for marketing campaigns."""

    model = Campaign

    async def create(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        created_by: UUID | None = None,
        **kwargs: Any,
    ) -> Campaign:
        campaign = Campaign(
            tenant_id=tenant_id,
            workspace_id=workspace_id or kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            description=kwargs.pop("description", None),
            campaign_type=kwargs.pop("campaign_type", "email"),
            status=kwargs.pop("status", "draft"),
            channel=kwargs.pop("channel", None),
            budget=kwargs.pop("budget", None),
            target_audience=kwargs.pop("target_audience", None),
            schedule_start=kwargs.pop("schedule_start", None),
            schedule_end=kwargs.pop("schedule_end", None),
            ai_optimized=kwargs.pop("ai_optimized", False),
            metrics=kwargs.pop("metrics", None),
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.debug("Created Campaign %s", campaign.id)
        return campaign

    async def list(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[Campaign], int]:
        conditions = [Campaign.tenant_id == tenant_id, Campaign.deleted_at.is_(None)]
        if workspace_id:
            conditions.append(Campaign.workspace_id == workspace_id)
        if status:
            conditions.append(Campaign.status == status)

        count_stmt = select(func.count()).select_from(Campaign).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Campaign)
            .where(*conditions)
            .order_by(desc(Campaign.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total


class EmailTemplateService(BaseService[EmailTemplate]):
    """CRUD for email templates."""

    model = EmailTemplate

    async def create(
        self,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> EmailTemplate:
        template = EmailTemplate(
            tenant_id=tenant_id,
            workspace_id=kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            subject=kwargs.pop("subject", ""),
            preheader=kwargs.pop("preheader", None),
            body_html=kwargs.pop("body_html", ""),
            body_text=kwargs.pop("body_text", None),
            category=kwargs.pop("category", None),
            variables=kwargs.pop("variables", None),
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
    ) -> tuple[list[EmailTemplate], int]:
        conditions = [EmailTemplate.tenant_id == tenant_id, EmailTemplate.deleted_at.is_(None)]
        if category:
            conditions.append(EmailTemplate.category == category)

        count_stmt = select(func.count()).select_from(EmailTemplate).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(EmailTemplate)
            .where(*conditions)
            .order_by(desc(EmailTemplate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total


class LandingPageService(BaseService[LandingPage]):
    """CRUD for landing pages."""

    model = LandingPage

    async def create(
        self,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> LandingPage:
        page = LandingPage(
            tenant_id=tenant_id,
            workspace_id=kwargs.pop("workspace_id", None),
            title=kwargs.pop("title"),
            slug=kwargs.pop("slug"),
            content=kwargs.pop("content", {}),
            status=kwargs.pop("status", "draft"),
            seo_meta=kwargs.pop("seo_meta", None),
            ai_generated=kwargs.pop("ai_generated", False),
        )
        self.db.add(page)
        await self.db.flush()
        await self.db.refresh(page)
        return page

    async def list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[LandingPage], int]:
        conditions = [LandingPage.tenant_id == tenant_id, LandingPage.deleted_at.is_(None)]
        if status:
            conditions.append(LandingPage.status == status)

        count_stmt = select(func.count()).select_from(LandingPage).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(LandingPage)
            .where(*conditions)
            .order_by(desc(LandingPage.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total


class FunnelService(BaseService[Funnel]):
    """CRUD for marketing funnels."""

    model = Funnel

    async def create(
        self,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> Funnel:
        funnel = Funnel(
            tenant_id=tenant_id,
            workspace_id=kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            description=kwargs.pop("description", None),
            steps=kwargs.pop("steps", []),
            ai_optimized=kwargs.pop("ai_optimized", False),
        )
        self.db.add(funnel)
        await self.db.flush()
        await self.db.refresh(funnel)
        return funnel

    async def list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Funnel], int]:
        conditions = [Funnel.tenant_id == tenant_id, Funnel.deleted_at.is_(None)]

        count_stmt = select(func.count()).select_from(Funnel).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Funnel)
            .where(*conditions)
            .order_by(desc(Funnel.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total


class SegmentService(BaseService[Segment]):
    """CRUD for audience segments."""

    model = Segment

    async def create(
        self,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> Segment:
        segment = Segment(
            tenant_id=tenant_id,
            workspace_id=kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            description=kwargs.pop("description", None),
            criteria=kwargs.pop("criteria", {}),
            is_dynamic=kwargs.pop("is_dynamic", True),
        )
        self.db.add(segment)
        await self.db.flush()
        await self.db.refresh(segment)
        return segment

    async def list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Segment], int]:
        conditions = [Segment.tenant_id == tenant_id]

        count_stmt = select(func.count()).select_from(Segment).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Segment)
            .where(*conditions)
            .order_by(desc(Segment.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total
