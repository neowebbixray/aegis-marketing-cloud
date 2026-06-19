"""Add email delivery tables — email_campaigns and email_messages.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-19

Tables:
- email_campaigns — outbound email campaigns with aggregate delivery stats
- email_messages — individual email delivery records with open/click/bounce tracking
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── email_campaigns ────────────────────────────────────────────────────
    op.create_table(
        "email_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("from_email", sa.String(320), nullable=False),
        sa.Column("from_name", sa.String(255), nullable=True),
        sa.Column("reply_to", sa.String(320), nullable=True),
        sa.Column("subject_override", sa.String(998), nullable=True),
        sa.Column("status", sa.String(50), default="draft", nullable=False, index=True),
        sa.Column("provider", sa.String(20), default="smtp", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_recipients", sa.Integer(), default=0, nullable=False),
        sa.Column("sent_count", sa.Integer(), default=0, nullable=False),
        sa.Column("delivered_count", sa.Integer(), default=0, nullable=False),
        sa.Column("bounced_count", sa.Integer(), default=0, nullable=False),
        sa.Column("complained_count", sa.Integer(), default=0, nullable=False),
        sa.Column("opened_count", sa.Integer(), default=0, nullable=False),
        sa.Column("clicked_count", sa.Integer(), default=0, nullable=False),
        sa.Column("failed_count", sa.Integer(), default=0, nullable=False),
        sa.Column("max_emails_per_minute", sa.Integer(), nullable=True),
        sa.Column("tracking_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_campaigns_status", "email_campaigns", ["status"])

    # ── email_messages ─────────────────────────────────────────────────────
    op.create_table(
        "email_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("email_campaigns.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_email", sa.String(320), nullable=False),
        sa.Column("from_name", sa.String(255), nullable=True),
        sa.Column("reply_to", sa.String(320), nullable=True),
        sa.Column("recipient_email", sa.String(320), nullable=False, index=True),
        sa.Column("recipient_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), default="queued", nullable=False, index=True),
        sa.Column("provider", sa.String(20), default="smtp", nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("tracking_id", sa.String(64), unique=True, nullable=True, index=True),
        sa.Column("tracking_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_count", sa.Integer(), default=0, nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("click_count", sa.Integer(), default=0, nullable=False),
        sa.Column("bounced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bounce_type", sa.String(30), nullable=True),
        sa.Column("bounce_reason", sa.Text(), nullable=True),
        sa.Column("complained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("complaint_feedback_type", sa.String(50), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_messages_status", "email_messages", ["status"])
    op.create_index("ix_email_messages_recipient_email", "email_messages", ["recipient_email"])
    op.create_index("ix_email_messages_tracking_id", "email_messages", ["tracking_id"],
                    unique=True, postgresql_where=sa.text("tracking_id IS NOT NULL"))

    # ── RLS policies (if pgcrypto extension is active) ─────────────────────
    for table_name in ("email_campaigns", "email_messages"):
        op.execute(
            f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON {table_name}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            """
        )

    # ── Audit trigger for email_campaigns (only; email_messages is high volume) ─
    op.execute(
        """
        CREATE TRIGGER audit_email_campaigns
        AFTER INSERT OR UPDATE OR DELETE ON email_campaigns
        FOR EACH ROW EXECUTE FUNCTION audit_log_trigger()
        """
    )


def downgrade() -> None:
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS audit_email_campaigns ON email_campaigns")

    # Drop RLS policies
    for table_name in ("email_campaigns", "email_messages"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name}")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    # Drop tables
    op.drop_table("email_messages")
    op.drop_table("email_campaigns")
