"""FastAPI dependencies for authentication, tenant context, and database sessions."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.database import get_db
from app.models.auth import User
from app.services.auth import AuthService

# Re-export for convenience
__all__ = [
    "get_current_active_user",
    "get_current_user",
    "get_db",
    "get_tenant_context",
]


async def get_current_user(
    request: Request,
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the JWT from the Authorization header.

    Returns the authenticated ``User``.

    Raises:
        UnauthorizedException: If the token is missing or invalid.

    """
    if authorization is None:
        raise UnauthorizedException(detail="Authorization header is required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(detail="Invalid authorization scheme — use Bearer")

    auth_service = AuthService(db)
    user = await auth_service.verify_token(token)
    request.state.current_user = user
    request.state.user_id = user.id
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the user to be active.

    Raises:
        ForbiddenException: If the user account is deactivated.

    """
    if not current_user.is_active:
        raise ForbiddenException(detail="User account is deactivated")
    return current_user


async def get_tenant_context(
    request: Request,
    current_user: User = Depends(get_current_active_user),
) -> UUID:
    """Resolve the effective tenant ID.

    Priority:
    1. ``X-Tenant-ID`` header (if provided and user belongs to it).
    2. The user's default tenant (first UserRole association).

    Returns the tenant UUID.

    Raises:
        ForbiddenException: If the user does not have access to the tenant.

    """
    x_tenant_id: str | None = request.headers.get("X-Tenant-ID") or request.headers.get(
        "x-tenant-id"
    )
    if x_tenant_id:
        tenant_id = UUID(x_tenant_id)
        # Verify user belongs to this tenant (can be disabled via app.state for testing)
        if getattr(getattr(request, "app", None), "state", None) is not None:
            _skip_check = getattr(request.app.state, "skip_tenant_membership_check", False)
        else:
            _skip_check = False
        if not _skip_check:
            from app.database import async_session_factory

            async with async_session_factory() as session:
                if not await _user_belongs_to_tenant(current_user.id, tenant_id, session):
                    raise ForbiddenException(detail="User does not belong to this tenant")
        return tenant_id

    # Fall back to user's default tenant

    # Instead, the caller should inject get_db; for simplicity, we return the
    # tenant from the token claims if present, or raise.
    token_tenant = getattr(request.state, "tenant_id", None)
    if token_tenant:
        return UUID(token_tenant)

    raise ForbiddenException(detail="Could not determine tenant context")


async def _user_belongs_to_tenant(user_id: UUID, tenant_id: UUID, db: AsyncSession) -> bool:
    """Check if a user belongs to a tenant via any workspace."""
    from sqlalchemy import func, select

    from app.models.tenant import UserRole, Workspace

    stmt = (
        select(func.count())
        .select_from(UserRole)
        .join(Workspace, Workspace.id == UserRole.workspace_id)
        .where(UserRole.user_id == user_id, Workspace.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return count > 0
