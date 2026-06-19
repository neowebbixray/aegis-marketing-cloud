"""
Auth router: registration, login, token refresh, profile, API keys, SSO.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.exceptions import NotFoundException
from app.core.keys import get_jwks
from app.models.auth import User
from app.schemas.auth import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ChangePasswordRequest,
    CreateApiKeyRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)
from app.schemas.sso import (
    SAMLLoginResponse,
    SSOCallbackRequest,
    SSOInitiateResponse,
    SSOProviderListResponse,
    SSOProviderResponse,
    SSOTokenResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user with a default tenant and workspace."""
    service = AuthService(db)
    result = await service.register(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        tenant_name=body.tenant_name,
    )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password."""
    service = AuthService(db)
    result = await service.login(email=body.email, password=body.password)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh an access token using a refresh token."""
    service = AuthService(db)
    result = await service.refresh_token(refresh_token=body.refresh_token)
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
    )


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Logout the current user (client should discard tokens)."""
    # In a full implementation, this would revoke the current session.
    # For now, token invalidation is handled client-side or via refresh rotation.
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return the current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateMeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update the current user's profile."""
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/password/change", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change the current user's password."""
    service = AuthService(db)
    await service.change_password(
        user_id=current_user.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return None


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all non-revoked API keys for the current user."""
    service = AuthService(db)
    keys = await service.list_api_keys(user_id=current_user.id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> ApiKeyCreatedResponse:
    """Create a new API key. The full key is returned only once."""
    from app.api.deps import get_tenant_context

    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = AuthService(db)
    result = await service.create_api_key(
        user_id=current_user.id,
        tenant_id=tenant_id,
        name=body.name,
        scopes=body.scopes,
    )
    return ApiKeyCreatedResponse(
        id=result["id"],
        name=result["name"],
        key_prefix=result["key_prefix"],
        full_key=result["full_key"],
        scopes=result["scopes"],
        created_at=result["created_at"],
    )


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke an API key."""
    from uuid import UUID

    service = AuthService(db)
    await service.revoke_api_key(api_key_id=UUID(key_id), user_id=current_user.id)
    return None


# ── JWKS (public key distribution) ──────────────────────────────────────────


@router.get("/.well-known/jwks.json", include_in_schema=True)
async def jwks_endpoint() -> dict:
    """Return the JSON Web Key Set for offline JWT verification.

    Per the docs, the public key is exposed at
    ``GET /api/v1/auth/.well-known/jwks.json`` for offline
    token verification.
    """
    return get_jwks()


# ── SSO / SAML Endpoints ─────────────────────────────────────────────────────


@router.get(
    "/sso/providers",
    response_model=SSOProviderListResponse,
    summary="List configured SSO providers",
)
async def list_sso_providers() -> SSOProviderListResponse:
    """Return all configured SSO/OAuth/SAML providers."""
    from app.core.sso import get_configured_providers

    providers = get_configured_providers()
    return SSOProviderListResponse(
        providers=[
            SSOProviderResponse(name=name, label=label)
            for name, label in providers.items()
        ]
    )


@router.post(
    "/sso/{provider}",
    response_model=SSOInitiateResponse | SAMLLoginResponse,
    summary="Initiate SSO login flow",
)
async def initiate_sso(
    provider: str,
) -> SSOInitiateResponse | SAMLLoginResponse:
    """Initiate an SSO login flow for the given provider.

    Returns a redirect URL to the provider's OAuth authorization page
    (or SAML IdP).
    """
    from app.core.sso import get_sso_provider

    sso = get_sso_provider(provider)
    if sso is None:
        raise NotFoundException(detail=f"Unknown SSO provider: {provider}")

    state = uuid.uuid4().hex  # In production, store this in Redis/session

    if provider == "saml":
        redirect_url, request_id = sso.get_login_url()
        return SAMLLoginResponse(
            authorization_url=redirect_url,
            request_id=request_id,
        )

    authorization_url = sso.get_authorization_url(state)
    return SSOInitiateResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get(
    "/sso/{provider}/callback",
    response_model=SSOTokenResponse,
    summary="Handle OAuth callback",
)
async def sso_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    db: AsyncSession = Depends(get_db),
) -> SSOTokenResponse:
    """Handle the OAuth callback from the SSO provider.

    Exchanges the authorization code for user info, then creates or links
    a user account and returns JWT tokens.
    """
    from app.core.sso import get_sso_provider

    sso = get_sso_provider(provider)
    if sso is None:
        raise NotFoundException(detail=f"Unknown SSO provider: {provider}")

    # Exchange code for user info
    user_info = await sso.exchange_code(code, state)

    # Find or create user account
    auth_service = AuthService(db)
    result = await auth_service.sso_login_or_register(
        provider=user_info.provider,
        provider_account_id=user_info.provider_account_id,
        email=user_info.email,
        display_name=user_info.display_name or "",
    )

    return SSOTokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
        user_id=result["user_id"],
        email=result["email"],
        display_name=result.get("display_name"),
        is_new_user=result.get("is_new_user", False),
    )


@router.post(
    "/sso/saml/callback",
    response_model=SSOTokenResponse,
    summary="Handle SAML assertion POST",
)
async def saml_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SSOTokenResponse:
    """Process a SAML IdP response (HTTP-POST binding).

    Expects a ``SAMLResponse`` form field in the POST body.
    """
    from app.core.sso import SAMLProvider, get_sso_provider

    sso = get_sso_provider("saml")
    if sso is None or not isinstance(sso, SAMLProvider):
        raise NotFoundException(detail="SAML provider not configured")

    form = await request.form()
    post_data = dict(form)

    # Process the SAML assertion
    user_info = await sso.process_assertion(post_data)

    # Find or create user account
    auth_service = AuthService(db)
    result = await auth_service.sso_login_or_register(
        provider=user_info.provider,
        provider_account_id=user_info.provider_account_id,
        email=user_info.email,
        display_name=user_info.display_name or "",
    )

    return SSOTokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
        user_id=result["user_id"],
        email=result["email"],
        display_name=result.get("display_name"),
        is_new_user=result.get("is_new_user", False),
    )
