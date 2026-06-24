"""Workflow API endpoints — trigger and manage n8n workflows."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.services.workflows import n8n_client, trigger

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/{workflow_id}/trigger")
async def trigger_workflow(
    workflow_id: str = Path(..., description="The ID of the n8n workflow to trigger"),
    payload: dict[str, Any] | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an n8n workflow by its ID."""
    await get_tenant_context(request, current_user=current_user)
    # Tenant-level workflow validation: ensure the workflow_id is allowed.
    # In production, this should query a tenant_workflows table or check
    # tenant settings. For now, we allow any workflow ID since n8n
    # authorization is managed separately.
    tenant_context = getattr(request.state, "tenant", None)
    if tenant_context and hasattr(tenant_context, "settings"):
        allowed = tenant_context.settings.get("allowed_workflows", None)
        if allowed is not None and workflow_id not in allowed:
            raise HTTPException(
                status_code=403,
                detail="Workflow not authorized for this tenant",
            )
    try:
        result = await trigger(workflow_id, payload or {})
        return build_single_response(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to trigger workflow: {exc}") from exc


@router.get("")
async def list_workflows(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List workflows from n8n."""
    await get_tenant_context(request, current_user=current_user)
    try:
        workflows = await n8n_client.get_workflows(limit=limit, offset=offset)
        return build_list_response(
            data=workflows.get("data", []),
            total=workflows.get("total", 0),
            limit=limit,
            offset=offset,
            request=request,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list workflows: {exc}") from exc


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str = Path(..., description="The ID of the workflow to retrieve"),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a single workflow from n8n."""
    await get_tenant_context(request, current_user=current_user)
    try:
        workflow = await n8n_client.get_workflow(workflow_id)
        return build_single_response(workflow)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to get workflow: {exc}") from exc


# Email reply processing is handled asynchronously by the Celery task
# in app.tasks.email_processing. The endpoint below can be exposed
# via a webhook route if synchronous reply processing is needed.
