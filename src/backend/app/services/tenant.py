"""
Tenant and workspace management service.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.tenant import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    UserRole,
    Workspace,
)
from app.models.auth import User

logger = logging.getLogger("amc.services.tenant")


class TenantService:
    """Business logic for tenant and workspace management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Tenant ───────────────────────────────────────────────────────────────
    async def create_tenant(
        self, name: str, slug: str, domain: str | None = None
    ) -> Tenant:
        """Create a new tenant organisation."""
        existing = await self.db.execute(select(Tenant).where(Tenant.slug == slug))
        if existing.scalars().first():
            raise ConflictException(detail=f"Tenant with slug '{slug}' already exists")

        tenant = Tenant(name=name, slug=slug, domain=domain)
        self.db.add(tenant)
        await self.db.flush()
        await self.db.commit()
        logger.info("Created tenant %s (%s)", tenant.slug, tenant.id)
        return tenant

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        """Fetch a tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalars().first()
        if tenant is None:
            raise NotFoundException(detail="Tenant not found")
        return tenant

    async def list_user_tenants(self, user_id: UUID) -> list[Tenant]:
        """List all tenants the user belongs to."""
        stmt = (
            select(Tenant)
            .join(Workspace, Workspace.tenant_id == Tenant.id)
            .join(UserRole, UserRole.workspace_id == Workspace.id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Workspace ────────────────────────────────────────────────────────────
    async def create_workspace(
        self,
        tenant_id: UUID,
        name: str,
        slug: str,
        settings: dict[str, Any] | None = None,
        branding: dict[str, Any] | None = None,
    ) -> Workspace:
        """Create a new workspace within a tenant."""
        # Verify tenant exists
        await self.get_tenant(tenant_id)

        existing = await self.db.execute(
            select(Workspace).where(
                Workspace.tenant_id == tenant_id,
                Workspace.slug == slug,
                Workspace.deleted_at.is_(None),
            )
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Workspace with slug '{slug}' already exists in this tenant"
            )

        workspace = Workspace(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            settings=settings or {},
            branding=branding or {},
        )
        self.db.add(workspace)
        await self.db.flush()
        await self.db.commit()
        logger.info("Created workspace %s in tenant %s", workspace.slug, tenant_id)
        return workspace

    async def list_workspaces(self, tenant_id: UUID) -> list[Workspace]:
        """List all workspaces in a tenant."""
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.tenant_id == tenant_id,
                Workspace.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_workspace(self, workspace_id: UUID) -> Workspace:
        """Fetch a workspace by ID."""
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.deleted_at.is_(None),
            )
        )
        workspace = result.scalars().first()
        if workspace is None:
            raise NotFoundException(detail="Workspace not found")
        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        **kwargs: Any,
    ) -> Workspace:
        """Update workspace fields."""
        workspace = await self.get_workspace(workspace_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(workspace, key, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    # ── Membership & Invitations ─────────────────────────────────────────────
    async def invite_user(
        self, workspace_id: UUID, email: str, role_id: UUID
    ) -> UserRole:
        """Assign a role to a user within a workspace.

        If the user does not exist, they should be invited via email (stub).
        """
        workspace = await self.get_workspace(workspace_id)

        # Find the user
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if user is None:
            # TODO: Send invitation email; create a pending invitation record
            raise NotFoundException(detail="User not found. Invitation flow not yet implemented.")

        # Verify role belongs to the same tenant
        role_result = await self.db.execute(
            select(Role).where(Role.id == role_id, Role.tenant_id == workspace.tenant_id)
        )
        role = role_result.scalars().first()
        if role is None:
            raise NotFoundException(detail="Role not found in this tenant")

        # Check if already assigned
        existing = await self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role_id,
                UserRole.workspace_id == workspace_id,
            )
        )
        if existing.scalars().first():
            raise ConflictException(detail="User already has this role in the workspace")

        user_role = UserRole(
            user_id=user.id,
            role_id=role_id,
            workspace_id=workspace_id,
        )
        self.db.add(user_role)
        await self.db.flush()
        await self.db.commit()
        logger.info("Invited user %s to workspace %s with role %s", email, workspace_id, role_id)
        return user_role

    async def remove_user(self, workspace_id: UUID, user_id: UUID) -> None:
        """Remove a user from a workspace."""
        result = await self.db.execute(
            select(UserRole).where(
                UserRole.workspace_id == workspace_id,
                UserRole.user_id == user_id,
            )
        )
        user_role = result.scalars().first()
        if user_role is None:
            raise NotFoundException(detail="User not found in this workspace")

        await self.db.delete(user_role)
        await self.db.flush()
        await self.db.commit()
        logger.info("Removed user %s from workspace %s", user_id, workspace_id)

    # ── Roles & Permissions ──────────────────────────────────────────────────
    async def get_roles(self, tenant_id: UUID) -> list[Role]:
        """List all roles for a tenant."""
        result = await self.db.execute(
            select(Role).where(Role.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def assign_role(
        self, user_id: UUID, role_id: UUID, workspace_id: UUID
    ) -> UserRole:
        """Assign a role to a user in a workspace."""
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            workspace_id=workspace_id,
        )
        self.db.add(user_role)
        await self.db.flush()
        await self.db.commit()
        return user_role
