"""Tenant and workspace router."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.models.tenant import PendingInvitation
from app.schemas.tenant import (
    InviteUserRequest,
    RoleResponse,
    TenantResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.tenant import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TenantResponse]:
    """List all tenants the current user belongs to."""
    service = TenantService(db)
    tenants = await service.list_user_tenants(user_id=current_user.id)
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get the current tenant based on X-Tenant-ID or user's default."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    return TenantResponse.model_validate(tenant)


# ── Workspaces ───────────────────────────────────────────────────────────────


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceResponse]:
    """List all workspaces in the current tenant."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = TenantService(db)
    workspaces = await service.list_workspaces(tenant_id=tenant_id)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Create a new workspace in the current tenant."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = TenantService(db)
    workspace = await service.create_workspace(
        tenant_id=tenant_id,
        name=body.name,
        slug=body.slug,
    )
    return WorkspaceResponse.model_validate(workspace)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Get workspace details."""
    service = TenantService(db)
    workspace = await service.get_workspace(workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Update workspace settings."""
    service = TenantService(db)
    workspace = await service.update_workspace(
        workspace_id=workspace_id,
        **body.model_dump(exclude_unset=True),
    )
    return WorkspaceResponse.model_validate(workspace)


@router.post("/workspaces/{workspace_id}/invite", status_code=201)
async def invite_user(
    workspace_id: UUID,
    body: InviteUserRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Invite a user to a workspace by assigning a role."""
    service = TenantService(db)
    result = await service.invite_user(
        workspace_id=workspace_id,
        email=body.email,
        role_id=body.role_id,
        invited_by_user_id=current_user.id,
    )

    if isinstance(result, PendingInvitation):
        return {"detail": "Invitation sent to email", "invitation_id": str(result.id)}
    return {"detail": "User invited successfully", "user_role_id": str(result.id)}


@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a user from a workspace."""
    service = TenantService(db)
    await service.remove_user(workspace_id=workspace_id, user_id=user_id)


# ── Roles ────────────────────────────────────────────────────────────────────


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[RoleResponse]:
    """List all roles in the current tenant."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = TenantService(db)
    roles = await service.get_roles(tenant_id=tenant_id)
    return [RoleResponse.model_validate(r) for r in roles]
