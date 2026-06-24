"""Factory classes for tenant / organisation models:
Tenant, Workspace, Role, UserRole.
"""

from __future__ import annotations

import uuid

import factory
from app.models.tenant import Role, Tenant, UserRole, Workspace
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class TenantFactory(BaseFactory):
    """Generate realistic Tenant instances."""

    class Meta:
        model = Tenant

    name = factory.Faker("company")
    slug = factory.Sequence(lambda n: f"tenant-{n}")
    domain = factory.Faker("domain_name")
    settings = factory.Dict({"timezone": "UTC", "currency": "USD"})
    features_enabled = factory.List(["crm", "marketing", "analytics"])


class WorkspaceFactory(BaseFactory):
    """Generate realistic Workspace instances.

    Requires a ``tenant_id`` (typically provided via ``SubFactory`` or fixture).
    """

    class Meta:
        model = Workspace

    tenant_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("bs")  # e.g. "revolutionize e-markets"
    slug = factory.Sequence(lambda n: f"workspace-{n}")
    settings = factory.Dict({"timezone": "UTC"})
    branding = factory.Dict({"primary_color": "#3B82F6"})
    is_default = False


class RoleFactory(BaseFactory):
    """Generate realistic Role instances."""

    class Meta:
        model = Role

    tenant_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Iterator(["Admin", "Editor", "Viewer", "Manager", "Contributor"])
    description = factory.Faker("sentence", nb_words=8)
    is_system = False


class UserRoleFactory(BaseFactory):
    """Generate realistic UserRole (role assignment) instances."""

    class Meta:
        model = UserRole

    user_id = factory.LazyFunction(uuid.uuid4)
    role_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
