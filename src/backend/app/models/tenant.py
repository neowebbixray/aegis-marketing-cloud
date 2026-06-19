"""
SQLAlchemy models for multi-tenant organisation structure:
Tenant, Workspace, Team, TeamMember, Role, Permission, RolePermission, UserRole.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TenantMixin


class Tenant(BaseModel, SoftDeleteMixin):
    """Top-level organisation. Every user belongs to at least one tenant."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    features_enabled: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), default=list, nullable=True
    )

    # Relationships
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="tenant", cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"


class Workspace(BaseModel, SoftDeleteMixin):
    """A workspace / project within a tenant."""

    __tablename__ = "workspaces"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    branding: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=dict, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="workspaces")
    teams: Mapped[list["Team"]] = relationship(
        "Team", back_populates="workspace", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_workspace_tenant_slug", "tenant_id", "slug", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"


class Team(BaseModel):
    """A team group within a workspace."""

    __tablename__ = "teams"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class TeamMember(BaseModel):
    """Membership of a user in a team."""

    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), default="member", nullable=False)  # member, lead, admin

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="members")

    __table_args__ = (
        Index("ix_team_member_team_user", "team_id", "user_id", unique=True),
    )


class Role(BaseModel):
    """Named role within a tenant (e.g. Admin, Editor, Viewer)."""

    __tablename__ = "roles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="roles")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_role_tenant_name", "tenant_id", "name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(BaseModel):
    """Granular permission that can be assigned to a role."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    module: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(BaseModel):
    """Many-to-many join between Role and Permission."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")

    __table_args__ = (
        Index("ix_role_permission_unique", "role_id", "permission_id", unique=True),
    )


class UserRole(BaseModel):
    """Assignment of a role to a user, scoped to a workspace."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        Index("ix_user_role_unique", "user_id", "role_id", "workspace_id", unique=True),
    )
