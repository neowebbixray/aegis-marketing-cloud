"""Marketing API router — campaigns, email templates, funnels, landing pages, segments."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.marketing import (
    CampaignCreate,
    CampaignUpdate,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    FunnelCreate,
    FunnelUpdate,
    LandingPageCreate,
    LandingPageUpdate,
    SegmentCreate,
    SegmentUpdate,
)
from app.services.marketing import (
    CampaignService,
    EmailTemplateService,
    FunnelService,
    LandingPageService,
    SegmentService,
)

router = APIRouter(prefix="/marketing", tags=["Marketing"])


# ── Campaigns ──────────────────────────────────────────────────────────────


@router.get("/campaigns", response_model=dict)
async def list_campaigns(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = CampaignService(db)
    items, total = await service.list(
        tenant_id, skip=(page - 1) * per_page, limit=per_page, status=status
    )
    return build_list_response(items, total, page, per_page, request)


@router.get("/campaigns/{campaign_id}", response_model=dict)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = CampaignService(db)
    item = await service.get(campaign_id)
    return build_single_response(item)


@router.post("/campaigns", response_model=dict, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = CampaignService(db)
    item = await service.create(tenant_id=tenant_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.patch("/campaigns/{campaign_id}", response_model=dict)
async def update_campaign(
    campaign_id: UUID,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = CampaignService(db)
    item = await service.update(campaign_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = CampaignService(db)
    await service.soft_delete(campaign_id)


# ── Email Templates ────────────────────────────────────────────────────────


@router.get("/email-templates", response_model=dict)
async def list_email_templates(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = EmailTemplateService(db)
    items, total = await service.list(
        tenant_id, skip=(page - 1) * per_page, limit=per_page, category=category
    )
    return build_list_response(items, total, page, per_page, request)


@router.get("/email-templates/{template_id}", response_model=dict)
async def get_email_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = EmailTemplateService(db)
    item = await service.get(template_id)
    return build_single_response(item)


@router.post("/email-templates", response_model=dict, status_code=201)
async def create_email_template(
    body: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = EmailTemplateService(db)
    item = await service.create(tenant_id=tenant_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.patch("/email-templates/{template_id}", response_model=dict)
async def update_email_template(
    template_id: UUID,
    body: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = EmailTemplateService(db)
    item = await service.update(template_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.delete("/email-templates/{template_id}", status_code=204)
async def delete_email_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = EmailTemplateService(db)
    await service.soft_delete(template_id)


# ── Landing Pages ──────────────────────────────────────────────────────────


@router.get("/landing-pages", response_model=dict)
async def list_landing_pages(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = LandingPageService(db)
    items, total = await service.list(
        tenant_id, skip=(page - 1) * per_page, limit=per_page, status=status
    )
    return build_list_response(items, total, page, per_page, request)


@router.get("/landing-pages/{page_id}", response_model=dict)
async def get_landing_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = LandingPageService(db)
    item = await service.get(page_id)
    return build_single_response(item)


@router.post("/landing-pages", response_model=dict, status_code=201)
async def create_landing_page(
    body: LandingPageCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = LandingPageService(db)
    item = await service.create(tenant_id=tenant_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.patch("/landing-pages/{page_id}", response_model=dict)
async def update_landing_page(
    page_id: UUID,
    body: LandingPageUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = LandingPageService(db)
    item = await service.update(page_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.delete("/landing-pages/{page_id}", status_code=204)
async def delete_landing_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = LandingPageService(db)
    await service.soft_delete(page_id)


# ── Funnels ────────────────────────────────────────────────────────────────


@router.get("/funnels", response_model=dict)
async def list_funnels(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = FunnelService(db)
    items, total = await service.list(tenant_id, skip=(page - 1) * per_page, limit=per_page)
    return build_list_response(items, total, page, per_page, request)


@router.get("/funnels/{funnel_id}", response_model=dict)
async def get_funnel(
    funnel_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = FunnelService(db)
    item = await service.get(funnel_id)
    return build_single_response(item)


@router.post("/funnels", response_model=dict, status_code=201)
async def create_funnel(
    body: FunnelCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = FunnelService(db)
    item = await service.create(tenant_id=tenant_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.patch("/funnels/{funnel_id}", response_model=dict)
async def update_funnel(
    funnel_id: UUID,
    body: FunnelUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = FunnelService(db)
    item = await service.update(funnel_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.delete("/funnels/{funnel_id}", status_code=204)
async def delete_funnel(
    funnel_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = FunnelService(db)
    await service.soft_delete(funnel_id)


# ── Segments ───────────────────────────────────────────────────────────────


@router.get("/segments", response_model=dict)
async def list_segments(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = SegmentService(db)
    items, total = await service.list(tenant_id, skip=(page - 1) * per_page, limit=per_page)
    return build_list_response(items, total, page, per_page, request)


@router.get("/segments/{segment_id}", response_model=dict)
async def get_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = SegmentService(db)
    item = await service.get(segment_id)
    return build_single_response(item)


@router.post("/segments", response_model=dict, status_code=201)
async def create_segment(
    body: SegmentCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = SegmentService(db)
    item = await service.create(tenant_id=tenant_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.patch("/segments/{segment_id}", response_model=dict)
async def update_segment(
    segment_id: UUID,
    body: SegmentUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    service = SegmentService(db)
    item = await service.update(segment_id, **body.model_dump(exclude_unset=True))
    return build_single_response(item)


@router.delete("/segments/{segment_id}", status_code=204)
async def delete_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = SegmentService(db)
    await service.soft_delete(segment_id)
