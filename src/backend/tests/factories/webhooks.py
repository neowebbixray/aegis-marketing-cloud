"""Factory classes for webhook models:
Webhook, WebhookDelivery.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import factory
from app.models.webhooks import Webhook, WebhookDelivery
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class WebhookFactory(BaseFactory):
    """Generate realistic Webhook instances."""

    class Meta:
        model = Webhook

    tenant_id = factory.LazyFunction(uuid.uuid4)
    url = factory.Faker("url")
    secret_hash = factory.Faker("sha256")
    events = factory.List(["contact.created", "deal.updated", "campaign.completed"])
    is_active = True
    api_version = "v1"
    retry_config = factory.Dict(
        {
            "max_retries": 3,
            "initial_delay_ms": 1000,
            "backoff_factor": 2.0,
        }
    )
    description = factory.Faker("sentence", nb_words=6)


class WebhookDeliveryFactory(BaseFactory):
    """Generate realistic WebhookDelivery instances."""

    class Meta:
        model = WebhookDelivery

    webhook_id = factory.LazyFunction(uuid.uuid4)
    event_type = factory.Iterator(
        [
            "contact.created",
            "deal.updated",
            "campaign.completed",
            "webhook.test",
            "email.sent",
        ]
    )
    status = factory.Iterator(["succeeded", "failed", "retrying", "pending"])
    request_headers = factory.Dict(
        {
            "Content-Type": "application/json",
            "X-Signature": "sha256=test_signature",
        }
    )
    request_body = factory.Faker("paragraph", nb_sentences=3)
    response_status = factory.Iterator([200, 201, 400, 500, None])
    response_body = factory.Faker("sentence", nb_words=8)
    duration_ms = factory.Faker("random_int", min=50, max=5000)
    attempt = 1
    max_attempts = 5
    next_retry_at = None
    completed_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(minutes=5),
    )
