"""
CRM router: contacts, deals, pipelines, activities.

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
from app.schemas.crm import (
    ActivityCreate,
    ActivityResponse,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DealCreate,
    DealResponse,
    DealStageChangeRequest,
    DealUpdate,
    PipelineCreate,
    PipelineResponse,
)
from app.services.crm import ActivityService, ContactService, DealService, PipelineService

router = APIRouter(prefix="/crm", tags=["crm"])


# ── Contacts ─────────────────────────────────────────────────────────────────


@router.get("/contacts")
async def list_contacts(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List contacts in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = ContactService(db)
    items, total = await service.list(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        filters=[service.model.workspace_id == UUID(workspace_id)] if workspace_id else None,
    )
    return build_list_response(
        data=[ContactResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/contacts", status_code=201)
async def create_contact(
    body: ContactCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new contact.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = ContactService(db)
    contact = await service.create(
        tenant_id=tenant_id,
        workspace_id=workspace_id or body.workspace_id,
        **body.model_dump(exclude={"workspace_id"}),
    )
    return build_single_response(ContactResponse.model_validate(contact))


@router.post("/contacts/search")
async def search_contacts(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Search contacts by name, email, company, or phone.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = ContactService(db)
    items, total = await service.search(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        query=query,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[ContactResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single contact.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ContactService(db)
    contact = await service.get(contact_id, tenant_id=tenant_id)
    return build_single_response(ContactResponse.model_validate(contact))


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: UUID,
    body: ContactUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a contact.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ContactService(db)
    contact = await service.update(
        contact_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(ContactResponse.model_validate(contact))


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a contact."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ContactService(db)
    await service.soft_delete(contact_id, tenant_id=tenant_id)
    return None


# ── Deals ────────────────────────────────────────────────────────────────────


@router.get("/deals")
async def list_deals(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List deals in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = DealService(db)
    items, total = await service.list(tenant_id=tenant_id, skip=skip, limit=limit)
    return build_list_response(
        data=[DealResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/deals", status_code=201)
async def create_deal(
    body: DealCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new deal.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = DealService(db)
    deal = await service.create(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        **body.model_dump(),
    )
    return build_single_response(DealResponse.model_validate(deal))


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single deal.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DealService(db)
    deal = await service.get(deal_id, tenant_id=tenant_id)
    return build_single_response(DealResponse.model_validate(deal))


@router.patch("/deals/{deal_id}")
async def update_deal(
    deal_id: UUID,
    body: DealUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a deal.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DealService(db)
    deal = await service.update(
        deal_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(DealResponse.model_validate(deal))


@router.patch("/deals/{deal_id}/stage")
async def change_deal_stage(
    deal_id: UUID,
    body: DealStageChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Move a deal to a different pipeline stage.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DealService(db)
    deal = await service.move_stage(
        deal_id=deal_id,
        new_stage_id=body.pipeline_stage_id,
        tenant_id=tenant_id,
        reason=body.reason,
    )
    return build_single_response(DealResponse.model_validate(deal))


@router.delete("/deals/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a deal."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DealService(db)
    await service.soft_delete(deal_id, tenant_id=tenant_id)
    return None


# ── Pipelines ────────────────────────────────────────────────────────────────


@router.get("/pipelines")
async def list_pipelines(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List pipelines in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = PipelineService(db)
    items, total = await service.list(tenant_id=tenant_id, skip=skip, limit=limit)
    return build_list_response(
        data=[PipelineResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/pipelines", status_code=201)
async def create_pipeline(
    body: PipelineCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new pipeline with optional stages.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = PipelineService(db)
    stages_data = [s.model_dump() for s in body.stages] if body.stages else None
    pipeline = await service.create_with_stages(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        stages=stages_data,
    )
    return build_single_response(PipelineResponse.model_validate(pipeline))


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a pipeline with its stages.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = PipelineService(db)
    pipeline = await service.get_with_stages(pipeline_id)
    return build_single_response(PipelineResponse.model_validate(pipeline))


# ── Activities ───────────────────────────────────────────────────────────────


@router.get("/activities")
async def list_activities(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List activities in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = ActivityService(db)
    items, total = await service.list(tenant_id=tenant_id, skip=skip, limit=limit)
    return build_list_response(
        data=[ActivityResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/activities", status_code=201)
async def create_activity(
    body: ActivityCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new activity.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = ActivityService(db)
    activity = await service.create(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        **body.model_dump(),
    )
    return build_single_response(ActivityResponse.model_validate(activity))


@router.get("/activities/{activity_id}")
async def get_activity(
    activity_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single activity.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ActivityService(db)
    activity = await service.get(activity_id, tenant_id=tenant_id)
    return build_single_response(ActivityResponse.model_validate(activity))
