"""
Pydantic schemas for tenant and workspace management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Workspace ────────────────────────────────────────────────────────────────
class WorkspaceCreate(BaseModel):
    """Payload for POST /workspaces."""

    name: str = Field(..., min_length=1, max_length=256)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9\-]+$")


class WorkspaceUpdate(BaseModel):
    """Payload for PATCH /workspaces/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=256)
    slug: Optional[str] = Field(None, min_length=1, max_length=128, pattern=r"^[a-z0-9\-]+$")
    settings: Optional[dict[str, Any]] = None
    branding: Optional[dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    """Workspace representation."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    is_default: bool
    settings: Optional[dict[str, Any]] = None
    branding: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Tenant ───────────────────────────────────────────────────────────────────
class TenantResponse(BaseModel):
    """Tenant representation."""

    id: UUID
    name: str
    slug: str
    domain: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Invitation ───────────────────────────────────────────────────────────────
class InviteUserRequest(BaseModel):
    """Payload for POST /workspaces/{id}/invite."""

    email: str = Field(..., max_length=320)
    role_id: UUID


# ── Roles ────────────────────────────────────────────────────────────────────
class RoleResponse(BaseModel):
    """Role representation."""

    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}
