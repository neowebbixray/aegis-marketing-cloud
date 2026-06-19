"""
Factory classes for CRM models:
Contact, Deal, Pipeline, PipelineStage, Activity.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.crm import Activity, Contact, Deal, Pipeline, PipelineStage


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class PipelineFactory(BaseFactory):
    """Generate realistic Pipeline (sales funnel) instances."""

    class Meta:
        model = Pipeline

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Iterator([
        "Sales Pipeline", "Lead Funnel", "Qualification Pipeline",
        "Enterprise Sales", "Onboarding Pipeline",
    ])
    description = factory.Faker("sentence", nb_words=6)
    is_default = False


class PipelineStageFactory(BaseFactory):
    """Generate realistic PipelineStage instances.

    Requires a ``pipeline_id`` FK (typically from a ``PipelineFactory``).
    """

    class Meta:
        model = PipelineStage

    pipeline_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Iterator([
        "New Lead", "Qualified", "Proposal", "Negotiation",
        "Closed Won", "Closed Lost",
    ])
    order = factory.Sequence(lambda n: n)
    probability = factory.Faker(
        "pyfloat", min_value=0, max_value=100, right_digits=0
    )
    colour = factory.Iterator(["#EF4444", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6"])


class ContactFactory(BaseFactory):
    """Generate realistic Contact instances."""

    class Meta:
        model = Contact

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}.{o.last_name.lower()}@example.com"
    )
    phone = factory.Faker("phone_number")
    company = factory.Faker("company")
    position = factory.Faker("job")
    lifecycle_stage = factory.Iterator([
        "lead", "qualified", "opportunity", "customer", "churned",
    ])
    source = factory.Iterator([
        "website", "referral", "advertisement", "email", "event",
    ])
    custom_fields = factory.Dict({"industry": "Technology"})
    tags = factory.List(["prospect", "new"])
    owner_id = None


class DealFactory(BaseFactory):
    """Generate realistic Deal instances.

    Requires ``pipeline_stage_id`` FK. Optional ``contact_id`` and ``owner_id``.
    """

    class Meta:
        model = Deal

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("catch_phrase")
    value = factory.Faker(
        "pydecimal", left_digits=6, right_digits=2, positive=True
    )
    currency = "USD"
    pipeline_stage_id = factory.LazyFunction(uuid.uuid4)
    contact_id = None
    organization_label = factory.Faker("company")
    owner_id = None
    probability = factory.Faker(
        "pyfloat", min_value=0, max_value=100, right_digits=0
    )
    expected_close_date = factory.Faker("future_date")
    custom_fields = factory.Dict({})


class ActivityFactory(BaseFactory):
    """Generate realistic Activity instances."""

    class Meta:
        model = Activity

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    type = factory.Iterator(["note", "call", "email", "meeting", "task"])
    subject = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph", nb_sentences=3)
    contact_id = None
    deal_id = None
    user_id = None
