"""
Factory classes for email delivery models:
EmailCampaign, EmailMessage.
EmailTemplateFactory is already defined in tests/factories/marketing.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.email import EmailCampaign, EmailMessage


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class EmailCampaignFactory(BaseFactory):
    """Generate realistic EmailCampaign instances."""

    class Meta:
        model = EmailCampaign

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    campaign_id = None
    template_id = None
    name = factory.Faker("catch_phrase")
    description = factory.Faker("sentence", nb_words=8)
    from_email = "sender@example.com"
    from_name = factory.Faker("name")
    reply_to = None
    subject_override = factory.Faker("sentence", nb_words=6)
    status = factory.Iterator(["draft", "scheduled", "sending", "completed", "failed"])
    provider = factory.Iterator(["smtp", "ses"])
    scheduled_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )
    started_at = None
    completed_at = None
    total_recipients = 0
    sent_count = 0
    delivered_count = 0
    bounced_count = 0
    complained_count = 0
    opened_count = 0
    clicked_count = 0
    failed_count = 0
    max_emails_per_minute = None
    tracking_enabled = True
    metadata = factory.Dict({"source": "factory"})


class EmailMessageFactory(BaseFactory):
    """Generate realistic EmailMessage instances."""

    class Meta:
        model = EmailMessage

    tenant_id = factory.LazyFunction(uuid.uuid4)
    workspace_id = factory.LazyFunction(uuid.uuid4)
    campaign_id = None
    template_id = None
    from_email = "sender@example.com"
    from_name = factory.Faker("name")
    reply_to = None
    recipient_email = factory.Faker("email")
    recipient_name = factory.Faker("name")
    subject = factory.Faker("sentence", nb_words=6)
    body_html = factory.Faker("paragraph", nb_sentences=5)
    body_text = factory.Faker("paragraph", nb_sentences=3)
    status = factory.Iterator(["queued", "sent", "delivered", "bounced", "failed"])
    provider = factory.Iterator(["smtp", "ses"])
    provider_message_id = factory.LazyFunction(
        lambda: f"msg_{uuid.uuid4().hex}"
    )
    tracking_id = factory.LazyFunction(
        lambda: uuid.uuid4().hex
    )
    tracking_enabled = True
    opened_at = None
    open_count = 0
    clicked_at = None
    click_count = 0
    bounced_at = None
    bounce_type = None
    bounce_reason = None
    complained_at = None
    complaint_feedback_type = None
    queued_at = factory.LazyFunction(
        lambda: datetime.now(timezone.utc) - timedelta(hours=1)
    )
    sent_at = None
    delivered_at = None
    failed_at = None
    error_message = None
    metadata = factory.Dict({"source": "factory"})
