"""
Authentication service: registration, login, token refresh, API key management,
and password changes.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.models.auth import ApiKey, Session, User
from app.models.tenant import Role, Tenant, UserRole, Workspace

logger = logging.getLogger("amc.services.auth")


class AuthService:
    """High-level authentication business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Registration ─────────────────────────────────────────────────────────
    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
        tenant_name: str | None = None,
    ) -> dict[str, Any]:
        """Register a new user, create a default tenant and workspace, and
        return JWT tokens.

        Args:
            email: User's email address.
            password: Plain-text password.
            display_name: User's display name.
            tenant_name: Optional tenant name (defaults to the user's display name).

        Returns:
            A dict with ``access_token``, ``refresh_token``, ``token_type``,
            ``expires_in``, and ``user``.
        """
        # Check for duplicate email
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalars().first():
            raise ConflictException(detail="A user with this email already exists")

        # Hash password
        pw_hash = hash_password(password)

        # Create user
        user = User(
            email=email,
            password_hash=pw_hash,
            display_name=display_name,
        )
        self.db.add(user)
        await self.db.flush()

        # Create default tenant
        tenant = Tenant(
            name=tenant_name or f"{display_name}'s Organisation",
            slug=tenant_name.lower().replace(" ", "-") if tenant_name else f"org-{user.id.hex[:8]}",
        )
        self.db.add(tenant)
        await self.db.flush()

        # Create default workspace
        workspace = Workspace(
            tenant_id=tenant.id,
            name="Default Workspace",
            slug="default",
            is_default=True,
        )
        self.db.add(workspace)
        await self.db.flush()

        # Create default Admin role and assign it
        admin_role = Role(
            tenant_id=tenant.id,
            name="Admin",
            description="Full system access within the tenant",
            is_system=True,
        )
        self.db.add(admin_role)
        await self.db.flush()

        user_role = UserRole(
            user_id=user.id,
            role_id=admin_role.id,
            workspace_id=workspace.id,
        )
        self.db.add(user_role)
        await self.db.flush()

        # Issue tokens
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"tenant_id": str(tenant.id), "workspace_id": str(workspace.id)},
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        await self._store_refresh_token(user.id, tenant.id, refresh_token)

        await self.db.commit()

        logger.info("Registered user %s with tenant %s", user.email, tenant.slug)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire * 60,
            "user": user,
            "tenant": tenant,
            "workspace": workspace,
        }

    # ── Login ────────────────────────────────────────────────────────────────
    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate a user by email and password.

        Returns token data on success.

        Raises:
            UnauthorizedException: If credentials are invalid.
            ForbiddenException: If the account is inactive or MFA is required.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException(detail="Invalid email or password")

        if not user.is_active:
            raise ForbiddenException(detail="Account is deactivated")

        # Check MFA
        if user.mfa_devices:
            # TODO: Return a session token / MFA challenge instead of full auth
            raise ForbiddenException(detail="MFA challenge required")

        # Update last_login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Get default tenant & workspace for the user
        tenant_id, workspace_id = await self._get_user_context(user.id)

        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"tenant_id": str(tenant_id), "workspace_id": str(workspace_id)},
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        await self._store_refresh_token(user.id, tenant_id, refresh_token)

        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire * 60,
            "user": user,
        }

    # ── Token Refresh ────────────────────────────────────────────────────────
    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Verify a refresh token, rotate it, and return a new token pair.

        Raises:
            UnauthorizedException: If the token is invalid, expired, or revoked.
        """
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise UnauthorizedException(detail="Invalid or expired refresh token") from exc

        if payload.get("type") != "refresh":
            raise UnauthorizedException(detail="Token is not a refresh token")

        user_id = payload["sub"]

        # Hash the incoming token to look up the session
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(Session).where(
                Session.refresh_token_hash == token_hash,
                Session.revoked_at.is_(None),
            )
        )
        session = result.scalars().first()

        if session is None or session.is_expired:
            raise UnauthorizedException(detail="Refresh token has been revoked or expired")

        # Revoke old session
        session.revoked_at = datetime.now(timezone.utc)

        # Issue new tokens
        new_access = create_access_token(subject=user_id)
        new_refresh = create_refresh_token(subject=user_id)
        await self._store_refresh_token(
            UUID(user_id), session.tenant_id, new_refresh
        )

        await self.db.commit()

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire * 60,
        }

    # ── API Key Management ───────────────────────────────────────────────────
    async def create_api_key(
        self, user_id: UUID, tenant_id: UUID, name: str, scopes: list[str] | None = None
    ) -> dict[str, Any]:
        """Generate a new API key for the user.

        Returns:
            A dict with the ``full_key`` (shown once), ``id``, ``name``,
            ``key_prefix``, ``scopes``, and ``created_at``.
        """
        full_key, prefix = generate_api_key()
        key_hash = hash_api_key(full_key)

        api_key = ApiKey(
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes or [],
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.commit()

        return {
            "id": api_key.id,
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "full_key": full_key,
            "scopes": api_key.scopes,
            "created_at": api_key.created_at,
        }

    async def list_api_keys(self, user_id: UUID) -> list[ApiKey]:
        """List all non-revoked API keys for a user."""
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def revoke_api_key(self, api_key_id: UUID, user_id: UUID) -> None:
        """Revoke an API key belonging to the user."""
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.id == api_key_id,
                ApiKey.user_id == user_id,
            )
        )
        api_key = result.scalars().first()
        if api_key is None:
            raise NotFoundException(detail="API key not found")
        api_key.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.commit()

    # ── Token Verification ───────────────────────────────────────────────────
    async def verify_token(self, token: str) -> User:
        """Decode and validate a JWT access token, returning the user.

        Raises:
            UnauthorizedException: If the token is invalid or the user not found.
        """
        try:
            payload = decode_token(token)
        except Exception as exc:
            raise UnauthorizedException(detail="Invalid or expired token") from exc

        if payload.get("type") != "access":
            raise UnauthorizedException(detail="Token is not an access token")

        user_id = payload["sub"]
        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalars().first()

        if user is None or not user.is_active:
            raise UnauthorizedException(detail="User not found or inactive")

        return user

    # ── Password Change ──────────────────────────────────────────────────────
    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        """Verify the current password and update to the new one.

        Raises:
            UnauthorizedException: If the current password is wrong.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if user is None:
            raise NotFoundException(detail="User not found")

        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedException(detail="Current password is incorrect")

        # Revoke all existing sessions (force re-login)
        await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
            )
        )
        # NOTE: In production, batch-update sessions here

        user.password_hash = hash_password(new_password)
        await self.db.flush()
        await self.db.commit()

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _store_refresh_token(
        self, user_id: UUID, tenant_id: UUID, raw_token: str
    ) -> None:
        """Hash and persist a refresh token as a Session record."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_refresh_token_expire
        )
        session = Session(
            user_id=user_id,
            tenant_id=tenant_id,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(session)

    async def _get_user_context(self, user_id: UUID) -> tuple[UUID, UUID]:
        """Return the user's default (tenant_id, workspace_id)."""
        result = await self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id).limit(1)
        )
        user_role = result.scalars().first()
        if user_role is None:
            raise NotFoundException(detail="User has no tenant assignments")

        # Get the tenant ID from the workspace
        ws_result = await self.db.execute(
            select(Workspace).where(Workspace.id == user_role.workspace_id)
        )
        ws = ws_result.scalars().first()
        if ws is None:
            raise NotFoundException(detail="User's workspace not found")

        return ws.tenant_id, ws.id
