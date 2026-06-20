"""
Factory classes for auth / identity models:
User, ApiKey, Session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.core.security import hash_password
from app.models.auth import ApiKey, Session, User


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base for all async-compatible factories.

    Flush is deferred to the test fixture so that async sessions work
    correctly (``SQLAlchemyModelFactory._create`` calls ``session.add()``
    which is synchronous for ``AsyncSession``, and we skip its built-in
    ``flush`` by setting ``sqlalchemy_session_persistence = None``).
    """

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class UserFactory(BaseFactory):
    """Generate realistic User instances."""

    class Meta:
        model = User

    email = factory.Faker("email")
    email_verified = False
    password_hash = factory.LazyFunction(lambda: hash_password("TestPass123!"))
    display_name = factory.Faker("name")
    avatar_url = factory.Faker("image_url")
    locale = "en"
    timezone = "UTC"
    is_active = True
    is_superadmin = False
    metadata_jsonb = factory.Dict({"source": "factory"})
    last_login_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) - timedelta(hours=2)
    )
    # TenantMixin — tenant_id is set by fixtures or SubFactory
    tenant_id = factory.LazyFunction(uuid.uuid4)


class ApiKeyFactory(BaseFactory):
    """Generate realistic ApiKey instances."""

    class Meta:
        model = ApiKey

    user_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("sentence", nb_words=3)
    key_prefix = factory.LazyFunction(lambda: "amc_" + factory.Faker("hexify", text="^^^^^^^^").generate())
    key_hash = factory.Faker("sha256")
    scopes = factory.List(["read", "write"])
    expires_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) + timedelta(days=90)
    )
    last_used_at = None
    revoked_at = None
    # TenantMixin
    tenant_id = factory.LazyFunction(uuid.uuid4)


class SessionFactory(BaseFactory):
    """Generate realistic Session instances."""

    class Meta:
        model = Session

    user_id = factory.LazyFunction(uuid.uuid4)
    refresh_token_hash = factory.Faker("sha256")
    user_agent = factory.Faker("user_agent")
    ip_address = factory.Faker("ipv4")
    expires_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
    revoked_at = None
    # TenantMixin
    tenant_id = factory.LazyFunction(uuid.uuid4)
