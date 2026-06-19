"""
Tests for the auth endpoints: registration, login, token refresh, and
protected endpoint access.

Uses factory-based fixtures (``test_user``, ``test_auth_headers``) for
authenticated test scenarios.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """A new user can register and receives tokens."""
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPass1",
        "display_name": "New User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Registering with an existing email returns 409 Conflict."""
    payload = {
        "email": "dupe@example.com",
        "password": "StrongPass1",
        "display_name": "User One",
    }
    # First registration
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    # Duplicate
    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409, resp2.text


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user) -> None:
    """A registered user can log in and receives tokens."""
    payload = {
        "email": test_user.email,
        "password": "TestPass123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user) -> None:
    """Login with a wrong password returns 401."""
    payload = {
        "email": test_user.email,
        "password": "WrongPassword1",
    }
    response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401, response.text
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user) -> None:
    """A valid refresh token returns a new access token pair."""
    # First, log in to get a refresh token
    login_payload = {
        "email": test_user.email,
        "password": "TestPass123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # Now refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # The new refresh token should be different (rotation)
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient) -> None:
    """Accessing a protected endpoint without a token returns 401."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401, response.text
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, test_auth_headers) -> None:
    """An authenticated user can access their profile."""
    response = await client.get("/api/v1/auth/me", headers=test_auth_headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] is not None
    assert data["display_name"] is not None
