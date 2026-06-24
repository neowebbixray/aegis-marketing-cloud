"""Factory classes for billing models:
Subscription, Invoice, CreditWallet, UsageRecord.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import factory
from app.models.billing import CreditWallet, Invoice, Subscription, UsageRecord
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class SubscriptionFactory(BaseFactory):
    """Generate realistic Subscription instances."""

    class Meta:
        model = Subscription

    tenant_id = factory.LazyFunction(uuid.uuid4)
    plan_id = factory.Iterator(["free", "starter", "professional", "enterprise"])
    status = factory.Iterator(["active", "trialing", "past_due", "canceled", "inactive"])
    current_period_start = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(days=15),
    )
    current_period_end = factory.LazyFunction(
        lambda: datetime.now(UTC) + timedelta(days=15),
    )
    trial_end = None
    cancelled_at = None
    payment_provider = "stripe"
    payment_provider_id = factory.LazyFunction(
        lambda: f"sub_{uuid.uuid4().hex}",
    )


class InvoiceFactory(BaseFactory):
    """Generate realistic Invoice instances."""

    class Meta:
        model = Invoice

    tenant_id = factory.LazyFunction(uuid.uuid4)
    subscription_id = factory.LazyFunction(uuid.uuid4)
    invoice_number = factory.Sequence(lambda n: f"INV-{n:06d}")
    amount = factory.Faker(
        "pydecimal",
        left_digits=3,
        right_digits=2,
        positive=True,
    )
    currency = "USD"
    status = factory.Iterator(["pending", "paid", "past_due", "void", "refunded"])
    paid_at = None
    line_items = factory.List(
        [
            {"description": "Monthly subscription", "amount": 99.00, "quantity": 1},
        ]
    )
    meta_data = factory.Dict({"source": "factory"})


class CreditWalletFactory(BaseFactory):
    """Generate realistic CreditWallet instances."""

    class Meta:
        model = CreditWallet

    tenant_id = factory.LazyFunction(uuid.uuid4)
    balance = factory.Faker(
        "pydecimal",
        left_digits=3,
        right_digits=2,
        positive=True,
    )
    lifetime_credits = factory.Faker(
        "pydecimal",
        left_digits=4,
        right_digits=2,
        positive=True,
    )
    lifetime_spend = factory.Faker(
        "pydecimal",
        left_digits=3,
        right_digits=2,
        positive=True,
    )


class UsageRecordFactory(BaseFactory):
    """Generate realistic UsageRecord instances."""

    class Meta:
        model = UsageRecord

    subscription_id = factory.LazyFunction(uuid.uuid4)
    metric = factory.Iterator(
        [
            "api_calls",
            "storage_gb",
            "emails_sent",
            "ai_tokens",
            "contacts_stored",
        ]
    )
    quantity = factory.Faker(
        "pydecimal",
        left_digits=4,
        right_digits=2,
        positive=True,
    )
    recorded_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(hours=2),
    )
    meta_data = factory.Dict({"source": "factory"})
