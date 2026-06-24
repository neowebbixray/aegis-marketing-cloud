"""Add remaining domain tables — analytics, webhooks, marketplace, notifications, seo, social, usage, invitations.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-23

Tables added:
- analytics_events         — raw analytics event tracking
- metric_snapshots         — pre-aggregated metric data points
- dashboards               — user-defined dashboard configurations
- scheduled_reports        — scheduled report definitions with cron
- marketplace_installations  — plugin/extension installation records
- notifications            — in-app user notifications
- seo_keywords             — SEO keyword tracking and ranking data
- social_posts             — published/monitored social media posts
- pending_invitations      — pending user invitations
- webhooks                 — registered webhook endpoints
- webhook_deliveries       — webhook delivery attempt records
- usage_records            — subscription usage/consumption records
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Analytics tables ─────────────────────────────────────────────────
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("session_id", sa.String(255), nullable=True, index=True),
        sa.Column("event_name", sa.String(255), nullable=False, index=True),
        sa.Column("properties", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("entity_type", sa.String(100), nullable=True, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("processed", sa.Boolean(), default=False, nullable=False, index=True),
    )
    op.create_index("ix_analytics_events_event_timestamp",
                    "analytics_events", ["event_name", "timestamp"])

    op.create_table(
        "metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("metric_name", sa.String(255), nullable=False, index=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("dimensions", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index("ix_metric_snapshots_metric_timestamp",
                    "metric_snapshots", ["metric_name", "timestamp"])

    op.create_table(
        "dashboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("widgets", postgresql.JSONB, nullable=True, default=list),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("schedule", sa.String(100), nullable=True),
        sa.Column("recipients", postgresql.JSONB, nullable=True, default=list),
        sa.Column("last_generated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 2. Marketplace table ────────────────────────────────────────────────
    op.create_table(
        "marketplace_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("version_installed", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), default="installed", nullable=False, index=True),
        sa.Column("config", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("uninstalled_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 3. Notifications table ──────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("notification_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("action_url", sa.String(2048), nullable=True),
        sa.Column("priority", sa.String(20), default="normal", nullable=False, index=True),
        sa.Column("is_read", sa.Boolean(), default=False, nullable=False, index=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 4. SEO table ────────────────────────────────────────────────────────
    op.create_table(
        "seo_keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("keyword", sa.String(500), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("search_engine", sa.String(50), default="google", nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("language", sa.String(10), default="en", nullable=False),
        sa.Column("tags", postgresql.JSONB, nullable=True, default=list),
        sa.Column("current_rank", sa.Integer(), nullable=True),
        sa.Column("previous_rank", sa.Integer(), nullable=True),
        sa.Column("search_volume", sa.Integer(), nullable=True),
        sa.Column("difficulty_score", sa.Float(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 5. Social table ─────────────────────────────────────────────────────
    op.create_table(
        "social_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("media_urls", postgresql.JSONB, nullable=True, default=list),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), default="draft", nullable=False, index=True),
        sa.Column("platform_post_id", sa.String(255), nullable=True),
        sa.Column("engagement_metrics", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("ai_generated", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 6. Pending invitations ──────────────────────────────────────────────
    op.create_table(
        "pending_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email", sa.String(320), nullable=False, index=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 7. Webhook tables ───────────────────────────────────────────────────
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=True),
        sa.Column("events", postgresql.JSONB, nullable=False, default=list),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("api_version", sa.String(10), default="v1", nullable=False),
        sa.Column("retry_config", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("request_headers", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), default=1, nullable=False),
        sa.Column("max_attempts", sa.Integer(), default=5, nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 8. Usage records ────────────────────────────────────────────────────
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("pending_invitations")
    op.drop_table("social_posts")
    op.drop_table("seo_keywords")
    op.drop_table("notifications")
    op.drop_table("marketplace_installations")
    op.drop_table("scheduled_reports")
    op.drop_table("dashboards")
    op.drop_table("metric_snapshots")
    op.drop_table("analytics_events")
