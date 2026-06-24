"""Factory classes for analytics models:
AnalyticsEvent, MetricSnapshot, Dashboard, ScheduledReport.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import factory
from app.models.analytics import AnalyticsEvent, Dashboard, MetricSnapshot, ScheduledReport
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class AnalyticsEventFactory(BaseFactory):
    """Generate realistic AnalyticsEvent instances."""

    class Meta:
        model = AnalyticsEvent

    tenant_id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    session_id = factory.Faker("hexify", text="sess-^^^^^^^^^^^^^^^^")
    event_name = factory.Iterator(
        [
            "page_view",
            "form_submit",
            "login",
            "signup",
            "purchase",
            "click",
            "email_open",
            "export",
        ]
    )
    properties = factory.Dict(
        {
            "url": "https://example.com/page",
            "referrer": "https://google.com",
        }
    )
    entity_type = factory.Iterator(["campaign", "contact", "deal", None])
    entity_id = factory.LazyFunction(uuid.uuid4)
    timestamp = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(hours=2),
    )
    processed = False


class MetricSnapshotFactory(BaseFactory):
    """Generate realistic MetricSnapshot instances."""

    class Meta:
        model = MetricSnapshot

    tenant_id = factory.LazyFunction(uuid.uuid4)
    metric_name = factory.Iterator(
        [
            "page_views",
            "unique_visitors",
            "conversion_rate",
            "email_open_rate",
            "click_through_rate",
            "revenue",
        ]
    )
    value = factory.Faker("pyfloat", min_value=0, max_value=100000, right_digits=2)
    dimensions = factory.Dict({"entity_type": "campaign", "channel": "email"})
    timestamp = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(days=1),
    )


class AnalyticsDashboardFactory(BaseFactory):
    """Generate realistic Dashboard instances."""

    class Meta:
        model = Dashboard

    tenant_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Faker("catch_phrase")
    description = factory.Faker("sentence", nb_words=10)
    widgets = factory.List(
        [
            {
                "widget_id": str(uuid.uuid4()),
                "type": "line_chart",
                "title": "Page Views Over Time",
                "config": {"metric": "page_views", "granularity": "day"},
                "position": {"x": 0, "y": 0, "w": 6, "h": 4},
            },
            {
                "widget_id": str(uuid.uuid4()),
                "type": "metric_card",
                "title": "Active Users",
                "config": {"metric": "unique_visitors"},
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
            },
        ]
    )
    created_by = factory.LazyFunction(uuid.uuid4)


class ScheduledReportFactory(BaseFactory):
    """Generate realistic ScheduledReport instances."""

    class Meta:
        model = ScheduledReport

    tenant_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Faker("sentence", nb_words=5)
    report_type = factory.Iterator(
        [
            "campaign_performance",
            "revenue_summary",
            "user_engagement",
            "email_analytics",
        ]
    )
    config = factory.Dict(
        {
            "metrics": ["page_views", "unique_visitors"],
            "granularity": "day",
            "date_range": "last_30_days",
        }
    )
    schedule = factory.Iterator(["0 8 * * 1", "0 0 1 * *", None])
    recipients = factory.List(["admin@example.com", "reports@example.com"])
    last_generated = None
