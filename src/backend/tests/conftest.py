"""
Test configuration, fixtures, and factories.

Provides an async test client, a test database, sample data factories,
and authentication header helpers.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db
from app.main import create_app
from app.models.auth import User
from app.models.tenant import Role, Tenant, UserRole, Workspace
from app.core.security import hash_password, create_access_token

# ── Test factories ────────────────────────────────────────────────────────────
from tests.factories.auth import ApiKeyFactory, SessionFactory, UserFactory
from tests.factories.crm import (
    ActivityFactory,
    ContactFactory,
    DealFactory,
    PipelineFactory,
    PipelineStageFactory,
)
from tests.factories.marketing import CampaignFactory, EmailTemplateFactory, SegmentFactory
from tests.factories.tenant import RoleFactory, TenantFactory, UserRoleFactory, WorkspaceFactory
from tests.factories.ai import AIAgentFactory, ConversationFactory, KnowledgeDocumentFactory
from tests.factories.analytics import (
    AnalyticsDashboardFactory,
    AnalyticsEventFactory,
    MetricSnapshotFactory,
    ScheduledReportFactory,
)
from tests.factories.billing import (
    CreditWalletFactory,
    InvoiceFactory,
    SubscriptionFactory,
    UsageRecordFactory,
)
from tests.factories.email import EmailCampaignFactory, EmailMessageFactory
from tests.factories.media import MediaAssetFactory
from tests.factories.webhooks import WebhookDeliveryFactory, WebhookFactory

# ── Test database ────────────────────────────────────────────────────────────
# Use a separate database for tests (configure via env variable or fallback).
TEST_DATABASE_URL = settings.database_url + "_test"
# If the URL already has a query string, inject _test before the query
if "?" in settings.database_url:
    base, query = settings.database_url.split("?", 1)
    TEST_DATABASE_URL = f"{base}_test?{query}"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
test_async_session_factory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database() -> AsyncIterator[None]:
    """Create all tables before the test session and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh transactional session per test.

    Each test runs inside a transaction that is rolled back at the end,
    ensuring test isolation.
    """
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await trans.rollback()
        await session.close()


# ── Test app ─────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def app():
    """Create a test FastAPI app instance."""
    application = create_app()

    # Override the get_db dependency to use the test database
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as ac:
            yield ac


# ── Sample data factories ────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def sample_tenant(db_session: AsyncSession) -> Tenant:
    """Create a sample tenant for testing."""
    tenant = Tenant(
        name="Test Organisation",
        slug="test-org",
        domain="test.example.com",
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def sample_workspace(db_session: AsyncSession, sample_tenant: Tenant) -> Workspace:
    """Create a sample workspace for testing."""
    workspace = Workspace(
        tenant_id=sample_tenant.id,
        name="Test Workspace",
        slug="test-workspace",
        is_default=True,
    )
    db_session.add(workspace)
    await db_session.flush()
    return workspace


@pytest_asyncio.fixture
async def sample_role(db_session: AsyncSession, sample_tenant: Tenant) -> Role:
    """Create a sample admin role for testing."""
    role = Role(
        tenant_id=sample_tenant.id,
        name="Admin",
        description="Test admin role",
        is_system=True,
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def sample_user(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_workspace: Workspace,
    sample_role: Role,
) -> User:
    """Create a sample user with a role assignment."""
    user = User(
        email="testuser@example.com",
        password_hash=hash_password("TestPass123"),
        display_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_role = UserRole(
        user_id=user.id,
        role_id=sample_role.id,
        workspace_id=sample_workspace.id,
    )
    db_session.add(user_role)
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def sample_user2(
    db_session: AsyncSession,
    sample_tenant: Tenant,
    sample_workspace: Workspace,
    sample_role: Role,
) -> User:
    """Create a second sample user for isolation testing."""
    user = User(
        email="testuser2@example.com",
        password_hash=hash_password("TestPass456"),
        display_name="Test User 2",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_role = UserRole(
        user_id=user.id,
        role_id=sample_role.id,
        workspace_id=sample_workspace.id,
    )
    db_session.add(user_role)
    await db_session.flush()

    return user


# ── Auth headers ─────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def auth_headers(sample_user: User) -> dict[str, str]:
    """Generate valid JWT auth headers for the sample user."""
    token = create_access_token(
        subject=str(sample_user.id),
        extra_claims={"tenant_id": str(sample_user.tenant_id) if hasattr(sample_user, 'tenant_id') else ""},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def tenant_headers(auth_headers: dict[str, str], sample_tenant: Tenant) -> dict[str, str]:
    """Auth headers plus the X-Tenant-ID header."""
    headers = auth_headers.copy()
    headers["X-Tenant-ID"] = str(sample_tenant.id)
    return headers


# ── Factory session setup ─────────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def _setup_factory_sessions(db_session: AsyncSession) -> None:
    """Inject the async SQLAlchemy session into all test factories.

    This runs before every test so that ``UserFactory()``,
    ``TenantFactory()``, etc. add model instances to the current
    transactional session instead of ``None``.
    """
    for factory_cls in (
        UserFactory, ApiKeyFactory, SessionFactory,
        TenantFactory, WorkspaceFactory, RoleFactory, UserRoleFactory,
        ContactFactory, DealFactory, PipelineFactory, PipelineStageFactory,
        ActivityFactory,
        CampaignFactory, EmailTemplateFactory, SegmentFactory,
        AIAgentFactory, KnowledgeDocumentFactory, ConversationFactory,
        SubscriptionFactory, InvoiceFactory, CreditWalletFactory, UsageRecordFactory,
        MediaAssetFactory,
        WebhookFactory, WebhookDeliveryFactory,
        AnalyticsEventFactory, MetricSnapshotFactory, AnalyticsDashboardFactory,
        ScheduledReportFactory,
        EmailCampaignFactory, EmailMessageFactory,
    ):
        factory_cls._meta.sqlalchemy_session = db_session


# ── Factory-based fixtures ────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a Tenant using ``TenantFactory``."""
    tenant = TenantFactory()
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_tenant: Tenant) -> Workspace:
    """Create a Workspace using ``WorkspaceFactory``, linked to ``test_tenant``."""
    workspace = WorkspaceFactory(tenant_id=test_tenant.id, is_default=True)
    await db_session.flush()
    return workspace


@pytest_asyncio.fixture
async def test_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_workspace: Workspace,
) -> User:
    """Create a User + associated Role + UserRole using factories.

    Returns the created User with a full role assignment.
    """
    role = RoleFactory(tenant_id=test_tenant.id, name="Admin", is_system=True)
    user = UserFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
        workspace_id=test_workspace.id,
    )
    db_session.add(user_role)
    await db_session.flush()

    return user


@pytest_asyncio.fixture
async def test_auth_headers(test_user: User) -> dict[str, str]:
    """Generate valid JWT auth headers for the factory-created ``test_user``."""
    token = create_access_token(
        subject=str(test_user.id),
        extra_claims={"tenant_id": str(test_user.tenant_id)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_tenant_headers(
    test_auth_headers: dict[str, str],
    test_tenant: Tenant,
) -> dict[str, str]:
    """Auth headers plus the X-Tenant-ID header for the factory-created tenant."""
    headers = test_auth_headers.copy()
    headers["X-Tenant-ID"] = str(test_tenant.id)
    return headers
