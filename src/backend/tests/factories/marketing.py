"""Factory classes for marketing models:
Campaign, EmailTemplate, Segment.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import factory
from app.models.marketing import Campaign, EmailTemplate, Segment
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class CampaignFactory(BaseFactory):
    """Generate realistic Campaign instances."""

    class Meta:
        model = Campaign

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("catch_phrase")
    description = factory.Faker("paragraph", nb_sentences=2)
    campaign_type = factory.Iterator(
        [
            "email",
            "social",
            "ads",
            "events",
            "content",
        ]
    )
    status = factory.Iterator(["draft", "scheduled", "running", "completed", "paused"])
    channel = factory.Iterator(["email", "linkedin", "google_ads", "twitter", "webinar"])
    budget = factory.Faker(
        "pydecimal",
        left_digits=5,
        right_digits=2,
        positive=True,
    )
    target_audience = factory.Dict(
        {
            "industries": ["Technology"],
            "regions": ["North America"],
        }
    )
    schedule_start = factory.LazyFunction(
        lambda: datetime.now(UTC) + timedelta(days=1),
    )
    schedule_end = factory.LazyFunction(
        lambda: datetime.now(UTC) + timedelta(days=30),
    )
    ai_optimized = False
    metrics = factory.Dict(
        {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
        }
    )


class EmailTemplateFactory(BaseFactory):
    """Generate realistic EmailTemplate instances."""

    class Meta:
        model = EmailTemplate

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("sentence", nb_words=4)
    subject = factory.Faker("sentence", nb_words=6)
    preheader = factory.Faker("sentence", nb_words=4)
    body_html = factory.Faker("paragraph", nb_sentences=5)
    body_text = factory.Faker("paragraph", nb_sentences=3)
    category = factory.Iterator(
        [
            "transactional",
            "marketing",
            "onboarding",
            "newsletter",
        ]
    )
    variables = factory.List(["{{first_name}}", "{{company}}", "{{unsubscribe_url}}"])


class SegmentFactory(BaseFactory):
    """Generate realistic Segment instances."""

    class Meta:
        model = Segment

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("sentence", nb_words=8)
    criteria = factory.Dict(
        {
            "lifecycle_stage": ["lead", "qualified"],
            "source": ["website"],
        }
    )
    contact_count = 0
    is_dynamic = True
