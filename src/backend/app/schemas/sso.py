"""Pydantic schemas for SSO / SAML authentication endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SSOProviderResponse(BaseModel):
    """Response model listing a configured SSO provider."""

    name: str = Field(..., description="Provider identifier (e.g. 'google')")
    label: str = Field(..., description="Human-readable label (e.g. 'Google')")


class SSOProviderListResponse(BaseModel):
    """Response model for listing all configured SSO providers."""

    providers: list[SSOProviderResponse]


class SSOInitiateResponse(BaseModel):
    """Response returned when initiating an SSO login flow."""

    authorization_url: str = Field(
        ...,
        description="URL to redirect the user to for SSO authentication",
    )
    state: str = Field(
        ...,
        description="OAuth state parameter for CSRF protection",
    )


class SSOCallbackRequest(BaseModel):
    """Query parameters expected on the SSO callback endpoint."""

    code: str = Field(..., description="Authorization code from the provider")
    state: str = Field(..., description="State parameter for CSRF validation")


class SSOTokenResponse(BaseModel):
    """Response returned after successful SSO authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    email: str
    display_name: str | None = None
    is_new_user: bool = False


class SAMLLoginResponse(BaseModel):
    """Response returned when initiating a SAML login flow."""

    authorization_url: str = Field(
        ...,
        description="SAML IdP redirect URL",
    )
    request_id: str = Field(
        ...,
        description="SAML request ID for tracking",
    )
