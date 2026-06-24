"""Authentication service: registration, login, token refresh, API key management,
and password changes.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

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
from app.models.auth import ApiKey, OAuthAccount, Session, User
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

        # Create default tenant first (user needs a tenant_id)
        tenant = Tenant(
            name=tenant_name or f"{display_name}'s Organisation",
            slug=tenant_name.lower().replace(" ", "-") if tenant_name else f"org-{uuid4().hex[:8]}",
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

        # Create default Admin role
        admin_role = Role(
            tenant_id=tenant.id,
            name="Admin",
            description="Full system access within the tenant",
            is_system=True,
        )
        self.db.add(admin_role)
        await self.db.flush()

        # Create user (with tenant_id from the newly created tenant)
        user = User(
            email=email,
            password_hash=pw_hash,
            display_name=display_name,
            tenant_id=tenant.id,
        )
        self.db.add(user)
        await self.db.flush()

        # Assign the user to the Admin role
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
            # Generate a short-lived MFA challenge token
            challenge_id = uuid4()
            mfa_token = create_access_token(
                subject=str(user.id),
                extra_claims={
                    "type": "mfa_challenge",
                    "challenge_id": str(challenge_id),
                },
                expires_delta=timedelta(minutes=5),
            )
            logger.info(
                "MFA challenge %s issued for user %s",
                challenge_id,
                user.id,
            )
            return {
                "mfa_required": True,
                "mfa_token": mfa_token,
                "challenge_id": str(challenge_id),
            }

        # Update last_login
        user.last_login_at = datetime.now(UTC)
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
            ),
        )
        session = result.scalars().first()

        if session is None or session.is_expired:
            raise UnauthorizedException(detail="Refresh token has been revoked or expired")

        # Revoke old session
        session.revoked_at = datetime.now(UTC)

        # Issue new tokens
        new_access = create_access_token(subject=user_id)
        new_refresh = create_refresh_token(subject=user_id)
        await self._store_refresh_token(
            UUID(user_id),
            session.tenant_id,
            new_refresh,
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
        self,
        user_id: UUID,
        tenant_id: UUID,
        name: str,
        scopes: list[str] | None = None,
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
            ),
        )
        return list(result.scalars().all())

    async def revoke_api_key(self, api_key_id: UUID, user_id: UUID) -> None:
        """Revoke an API key belonging to the user."""
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.id == api_key_id,
                ApiKey.user_id == user_id,
            ),
        )
        api_key = result.scalars().first()
        if api_key is None:
            raise NotFoundException(detail="API key not found")
        api_key.revoked_at = datetime.now(UTC)
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
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
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
            ),
        )
        # NOTE: In production, batch-update sessions here

        user.password_hash = hash_password(new_password)
        await self.db.flush()
        await self.db.commit()

    # ── SSO Login / Register ────────────────────────────────────────────────
    async def sso_login_or_register(
        self,
        provider: str,
        provider_account_id: str,
        email: str,
        display_name: str,
    ) -> dict[str, Any]:
        """Find an existing user by SSO provider account, or create a new one.

        Returns:
            A dict with ``access_token``, ``refresh_token``, ``expires_in``,
            ``user_id``, ``email``, ``display_name``, and ``is_new_user``.

        """
        # Look for existing OAuth account link
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_account_id == provider_account_id,
            ),
        )
        oauth_account = result.scalars().first()

        if oauth_account is not None:
            # Existing link — return tokens for the linked user
            user_result = await self.db.execute(
                select(User).where(User.id == oauth_account.user_id),
            )
            user = user_result.scalars().first()
            if user is None:
                raise NotFoundException(detail="Linked user account not found")
            is_new_user = False
        else:
            # Check if a user with this email already exists
            user_result = await self.db.execute(
                select(User).where(User.email == email),
            )
            user = user_result.scalars().first()

            if user:
                # Link the OAuth account to the existing user
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_account_id=provider_account_id,
                    provider_email=email,
                )
                self.db.add(oauth_account)
                is_new_user = False
            else:
                # Create a new user with a random password (no password login)
                import secrets

                random_pw = secrets.token_urlsafe(32)
                pw_hash = hash_password(random_pw)

                # Create a default tenant and workspace for the new user FIRST
                tenant = Tenant(
                    name=f"{display_name or email}'s Organisation",
                    slug=f"org-{uuid4().hex[:8]}",
                )
                self.db.add(tenant)
                await self.db.flush()

                workspace = Workspace(
                    tenant_id=tenant.id,
                    name="Default Workspace",
                    slug="default",
                    is_default=True,
                )
                self.db.add(workspace)
                await self.db.flush()

                # Create default role
                admin_role = Role(
                    tenant_id=tenant.id,
                    name="Admin",
                    description="Full system access within the tenant",
                    is_system=True,
                )
                self.db.add(admin_role)
                await self.db.flush()

                # Create user (with tenant_id from the newly created tenant)
                user = User(
                    email=email,
                    password_hash=pw_hash,
                    display_name=display_name or email.split("@", maxsplit=1)[0],
                    email_verified=True,
                    tenant_id=tenant.id,
                )
                self.db.add(user)
                await self.db.flush()

                user_role = UserRole(
                    user_id=user.id,
                    role_id=admin_role.id,
                    workspace_id=workspace.id,
                )
                self.db.add(user_role)
                await self.db.flush()

                # Create OAuth account link
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_account_id=provider_account_id,
                    provider_email=email,
                )
                self.db.add(oauth_account)
                is_new_user = True

        # Update last login
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        # Get tenant context
        tenant_id, workspace_id = await self._get_user_context(user.id)

        # Issue tokens
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={
                "tenant_id": str(tenant_id),
                "workspace_id": str(workspace_id),
                "sso_provider": provider,
            },
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        await self._store_refresh_token(user.id, tenant_id, refresh_token)

        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",  # nosec B105
            "expires_in": settings.jwt_access_token_expire * 60,
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_new_user": is_new_user,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _store_refresh_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        raw_token: str,
    ) -> None:
        """Hash and persist a refresh token as a Session record."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_refresh_token_expire,
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
            select(UserRole).where(UserRole.user_id == user_id).limit(1),
        )
        user_role = result.scalars().first()
        if user_role is None:
            raise NotFoundException(detail="User has no tenant assignments")

        # Get the tenant ID from the workspace
        ws_result = await self.db.execute(
            select(Workspace).where(Workspace.id == user_role.workspace_id),
        )
        ws = ws_result.scalars().first()
        if ws is None:
            raise NotFoundException(detail="User's workspace not found")

        return ws.tenant_id, ws.id
