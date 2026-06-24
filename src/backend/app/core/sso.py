"""SSO / SAML enterprise authentication providers.

Provides:
- SSOProvider abstract base class
- GoogleOAuthProvider, MicrosoftOAuthProvider, GitHubOAuthProvider
- SAMLProvider (using python3-saml)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.config import settings

logger = logging.getLogger("amc.sso")


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class SSOUserInfo:
    """Normalised user information returned by any SSO provider."""

    provider: str
    provider_account_id: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    raw_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SSOProviderConfig:
    """Configuration for a single SSO provider."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "openid email profile"
    authorization_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    extra_params: dict[str, Any] = field(default_factory=dict)


# ── Abstract base ────────────────────────────────────────────────────────────


class SSOProvider(ABC):
    """Abstract base for OAuth2 / OpenID Connect SSO providers."""

    name: ClassVar[str] = ""

    def __init__(self, config: SSOProviderConfig | None = None) -> None:
        self.config = config or self._default_config()

    @abstractmethod
    def _default_config(self) -> SSOProviderConfig:
        """Return a config populated from settings for this provider."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Build the URL to redirect the user to for SSO authorisation."""

    @abstractmethod
    async def exchange_code(self, code: str, state: str) -> SSOUserInfo:
        """Exchange an authorisation code for user info."""


# ── Google OAuth ─────────────────────────────────────────────────────────────


class GoogleOAuthProvider(SSOProvider):
    """Google OAuth 2.0 / OpenID Connect provider."""

    name = "google"

    def _default_config(self) -> SSOProviderConfig:
        return SSOProviderConfig(
            client_id=settings.google_oauth_client_id or "",
            client_secret=settings.google_oauth_client_secret or "",
            redirect_uri=settings.sso_redirect_uri,
            scope="openid email profile",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            extra_params={"access_type": "offline", "prompt": "consent"},
        )

    def get_authorization_url(self, state: str) -> str:
        import urllib.parse

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
            "state": state,
            **self.config.extra_params,
        }
        return f"{self.config.authorization_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> SSOUserInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_resp = await client.post(
                self.config.token_url,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Fetch user info
            access_token = token_data["access_token"]
            user_resp = await client.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

        return SSOUserInfo(
            provider=self.name,
            provider_account_id=user_data.get("sub", ""),
            email=user_data.get("email", ""),
            display_name=user_data.get("name"),
            avatar_url=user_data.get("picture"),
            raw_attributes=user_data,
        )


# ── Microsoft OAuth (Azure AD) ───────────────────────────────────────────────


class MicrosoftOAuthProvider(SSOProvider):
    """Microsoft Azure AD OAuth 2.0 / OpenID Connect provider."""

    name = "microsoft"

    def _default_config(self) -> SSOProviderConfig:
        tenant = settings.microsoft_oauth_tenant or "common"
        return SSOProviderConfig(
            client_id=settings.microsoft_oauth_client_id or "",
            client_secret=settings.microsoft_oauth_client_secret or "",
            redirect_uri=settings.sso_redirect_uri,
            scope="openid email profile User.Read",
            authorization_url=(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"),
            token_url=(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"),
            userinfo_url="https://graph.microsoft.com/v1.0/me",
        )

    def get_authorization_url(self, state: str) -> str:
        import urllib.parse

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
            "state": state,
        }
        return f"{self.config.authorization_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> SSOUserInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                self.config.token_url,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            access_token = token_data["access_token"]
            user_resp = await client.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

        return SSOUserInfo(
            provider=self.name,
            provider_account_id=user_data.get("id", ""),
            email=user_data.get("mail") or user_data.get("userPrincipalName", ""),
            display_name=user_data.get("displayName"),
            raw_attributes=user_data,
        )


# ── GitHub OAuth ─────────────────────────────────────────────────────────────


class GitHubOAuthProvider(SSOProvider):
    """GitHub OAuth 2.0 provider (no OpenID Connect)."""

    name = "github"

    def _default_config(self) -> SSOProviderConfig:
        return SSOProviderConfig(
            client_id=settings.github_oauth_client_id or "",
            client_secret=settings.github_oauth_client_secret or "",
            redirect_uri=settings.sso_redirect_uri,
            scope="read:user user:email",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
        )

    def get_authorization_url(self, state: str) -> str:
        import urllib.parse

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scope,
            "state": state,
        }
        return f"{self.config.authorization_url}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, state: str) -> SSOUserInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                self.config.token_url,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data["access_token"]

            # Fetch user profile
            user_resp = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            # Fetch primary email (GitHub doesn't include email in /user by default)
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            email_resp.raise_for_status()
            emails = email_resp.json()
            primary_email = next(
                (e["email"] for e in emails if e.get("primary")),
                user_data.get("email", ""),
            )

        return SSOUserInfo(
            provider=self.name,
            provider_account_id=str(user_data.get("id", "")),
            email=primary_email,
            display_name=user_data.get("name") or user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
            raw_attributes=user_data,
        )


# ── SAML Provider ────────────────────────────────────────────────────────────


class SAMLProvider:
    """SAML 2.0 authentication provider using python3-saml (onelogin)."""

    name = "saml"

    def __init__(self) -> None:
        self.idp_metadata_url = settings.saml_idp_metadata_url or ""
        self.idp_entity_id = settings.saml_idp_entity_id or ""
        self.sp_entity_id = settings.saml_sp_entity_id or ""
        self.sp_acs_url = settings.saml_sp_acs_url or ""
        self.sp_x509_cert = settings.saml_sp_x509_cert or ""
        self.sp_private_key = settings.saml_sp_private_key or ""

    def _build_settings(self) -> dict[str, Any]:
        """Build the python3-saml settings dict."""
        return {
            "strict": True,
            "debug": settings.debug,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": f"{self.sp_acs_url.removesuffix('/callback')}/logout",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.sp_x509_cert,
                "privateKey": self.sp_private_key,
            },
            "idp": {
                "entityId": self.idp_entity_id,
                "singleSignOnService": {
                    "url": self.idp_metadata_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": "",
            },
        }

    def get_login_url(self) -> tuple[str, str]:
        """Return (redirect_url, request_id) for SAML login initiation."""
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
        except ImportError:
            logger.error(
                "python3-saml not installed. Install with: pip install python3-saml",
            )
            raise

        # Build a mock request dict for OneLogin_Saml2_Auth
        req = {
            "http_host": "localhost",
            "script_name": "/api/v1/auth/sso/saml/login",
            "get_data": {},
            "post_data": {},
        }
        auth = OneLogin_Saml2_Auth(req, self._build_settings())
        # Use get_data directly; auth.login() adds the SAMLRequest
        redirect_url = auth.login()
        return redirect_url, auth.get_last_request_id()

    async def process_assertion(self, post_data: dict[str, str]) -> SSOUserInfo:
        """Process a SAML response POST and return user info."""
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.errors import OneLogin_Saml2_Error
        except ImportError:
            logger.error(
                "python3-saml not installed. Install with: pip install python3-saml",
            )
            raise

        req = {
            "http_host": "localhost",
            "script_name": "/api/v1/auth/sso/saml/callback",
            "get_data": {},
            "post_data": post_data,
        }
        auth = OneLogin_Saml2_Auth(req, self._build_settings())
        auth.process_response()
        if auth.get_errors():
            error_msg = ", ".join(auth.get_errors())
            logger.error("SAML assertion error: %s", error_msg)
            raise OneLogin_Saml2_Error(error_msg)

        attributes = auth.get_attributes()
        name_id = auth.get_nameid()

        return SSOUserInfo(
            provider=self.name,
            provider_account_id=name_id or "",
            email=attributes.get("email", [""])[0]
            or attributes.get("Email", [""])[0]
            or name_id
            or "",
            display_name=attributes.get("displayName", [None])[0]
            or attributes.get("DisplayName", [None])[0],
            raw_attributes=attributes,
        )


# ── Provider registry ────────────────────────────────────────────────────────

_SSO_PROVIDERS: dict[str, type[SSOProvider]] = {
    "google": GoogleOAuthProvider,
    "microsoft": MicrosoftOAuthProvider,
    "github": GitHubOAuthProvider,
}


def get_sso_provider(provider_name: str) -> SSOProvider | SAMLProvider | None:
    """Return an instance of the named SSO provider, or None if unknown."""
    if provider_name == "saml":
        return SAMLProvider()
    provider_cls = _SSO_PROVIDERS.get(provider_name)
    if provider_cls is not None:
        return provider_cls()
    return None


def get_configured_providers() -> dict[str, str]:
    """Return a dict of provider_name -> display_label for configured providers."""
    providers: dict[str, str] = {}

    if settings.google_oauth_client_id:
        providers["google"] = "Google"
    if settings.microsoft_oauth_client_id:
        providers["microsoft"] = "Microsoft"
    if settings.github_oauth_client_id:
        providers["github"] = "GitHub"
    if settings.saml_idp_metadata_url:
        providers["saml"] = "SAML 2.0"

    return providers
