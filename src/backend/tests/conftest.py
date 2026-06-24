"""Aegis Marketing Cloud — Test Configuration & Fixtures
======================================================

Provides the full test infrastructure:
- Session-scoped schema init (sync SQLAlchemy via psycopg2)
- Per-test async engine with auto-rollback (no cross-loop leaks)
- Factory-based fixtures for User, Tenant, Workspace, etc.
- Auth headers for authenticated requests

Usage:
    pytest tests/ -v

Skip all tests if no database is available:
    export AMC_SKIP_DB_TESTS=1
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from app.config import settings as app_settings
from app.core.security import hash_password
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

# NOTE: Do NOT import app.database or app.main at module level — they
# create their engine at import time using the current settings.
# We patch settings FIRST in a session-scoped fixture, then import these
# modules lazily inside fixtures.

# ── Database URL (override via env) ───────────────────────────────────────────

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://amc:amc_secret@localhost:5432/aegis_marketing_cloud_test",
)


# ── Settings patch (runs first, before any DB imports) ────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _patch_settings():
    """Point settings at the test database and disable production features.

    Runs BEFORE any module-level ``app.database`` imports because those are
    done lazily inside fixtures.  By the time a test needs the database,
    ``settings.database_url`` already points at the test DB.
    """
    overrides = {
        "database_url": TEST_DATABASE_URL,
        "database_pool_size": 2,
        "database_max_overflow": 1,
        "debug": True,
        "environment": "testing",
        "rate_limit_enabled": False,
        "csp_enabled": False,
        "prometheus_enabled": False,
        "secret_key": "test-secret-key-not-for-production",
        "jwt_key_id": "test",
        "trusted_hosts": ["*"],
        # Disable optional services (not available in CI / test env)
        "minio_endpoint": "",
        "qdrant_host": "",
        "rabbitmq_url": "",
    }
    for key, value in overrides.items():
        setattr(app_settings, key, value)


# ── Schema init (once per session, sync DDL — no deadlocks) ──────────────────


@pytest.fixture(scope="session", autouse=True)
def _init_schema(_patch_settings):
    """Create all tables before the test session using sync SQLAlchemy."""
    # Import Base lazily — app.database only loaded now, AFTER settings patched
    from app.database import Base

    sync_url = TEST_DATABASE_URL.replace("+asyncpg", "+psycopg2")
    engine = create_sync_engine(sync_url, pool_pre_ping=False)
    try:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transaction-backed async database session.

    Each test gets a **fresh engine** and a transaction that is rolled back
    on teardown.  This guarantees zero cross-test leakage and avoids Windows
    event-loop issues with cached asyncpg connections.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_size=2,
        max_overflow=1,
        echo=False,
    )
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client against the FastAPI app.

    Overrides the ``get_db`` dependency to inject the test session
    and disables the tenant-membership DB check (data is transaction-local).
    """
    from app.api.deps import get_db
    from app.main import create_app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.state.skip_tenant_membership_check = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
def _bind_factories(db_session: AsyncSession):
    """Bind factory_boy's SQLAlchemyModelFactory classes to the test session.

    Each test gets its own ``db_session``, but factory_boy factories (e.g.
    ``WebhookFactory``) need ``_meta.sqlalchemy_session`` assigned to write
    to the database.  This fixture recursively visits every concrete
    (non-abstract) subclass and binds the live session.
    """
    from factory.alchemy import SQLAlchemyModelFactory

    def _bind(cls):
        meta = getattr(cls, "_meta", None)
        if meta is not None and not getattr(meta, "abstract", True):
            meta.sqlalchemy_session = db_session
        for sub in cls.__subclasses__():
            _bind(sub)

    _bind(SQLAlchemyModelFactory)


# ── Test Data Fixtures ───────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Any:
    """Create a default test tenant."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        name="Test Organisation",
        slug="test-org",
        settings={"timezone": "UTC", "currency": "USD"},
        features_enabled=["crm", "marketing", "analytics", "ai_agents"],
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_tenant) -> Any:
    """Create a default test workspace under ``test_tenant``."""
    from app.models.tenant import Workspace

    ws = Workspace(
        tenant_id=test_tenant.id,
        name="Default Workspace",
        slug="default",
        is_default=True,
        settings={"timezone": "UTC"},
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_tenant, test_workspace) -> Any:
    """Create a test user with a known password (``TestPass123!``)."""
    from app.models.auth import User
    from app.models.tenant import Role, UserRole

    user = User(
        email="testuser@example.com",
        password_hash=hash_password("TestPass123!"),
        display_name="Test User",
        tenant_id=test_tenant.id,
        is_active=True,
        locale="en",
        timezone="UTC",
    )
    db_session.add(user)
    await db_session.flush()

    # Create an Admin role for the tenant
    role = Role(
        tenant_id=test_tenant.id,
        name="Admin",
        description="Full system access",
        is_system=True,
    )
    db_session.add(role)
    await db_session.flush()

    # Assign the user to the role
    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
        workspace_id=test_workspace.id,
    )
    db_session.add(user_role)
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def test_auth_headers(test_user) -> dict[str, str]:
    """Provide Bearer authorization headers for ``test_user``."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=str(test_user.id),
        extra_claims={
            "tenant_id": str(test_user.tenant_id),
        },
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_tenant_headers(test_auth_headers, test_tenant) -> dict[str, str]:
    """Provide headers with both auth token and X-Tenant-ID."""
    return {
        **test_auth_headers,
        "X-Tenant-ID": str(test_tenant.id),
    }


@pytest_asyncio.fixture
async def test_admin_role(db_session: AsyncSession, test_tenant) -> Any:
    """Create an Admin role for permission tests."""
    from app.models.tenant import Role

    role = Role(
        tenant_id=test_tenant.id,
        name="Admin",
        description="Full system access within the tenant",
        is_system=True,
    )
    db_session.add(role)
    await db_session.flush()
    return role
