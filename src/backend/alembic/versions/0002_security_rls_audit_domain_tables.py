"""PostgreSQL security enhancements: RLS, PII encryption, audit logging, and
remaining domain tables (marketing, AI, billing, media).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-19

Features:
- pgcrypto extension for column-level encryption
- Row-Level Security (RLS) policies on all tenant-scoped tables
- Audit log trigger function and table
- Encrypted PII columns for contacts (email, phone, company)
- Marketing tables (campaigns, email_templates, landing_pages, funnels,
  segments, tags)
- AI tables (ai_agents, ai_agent_executions, knowledge_documents,
  conversations, messages)
- Billing tables (subscriptions, invoices, credit_wallets)
- Media table (assets)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

TENANT_TABLES = [
    "contacts", "pipelines", "deals", "activities",
    "campaigns", "email_templates", "landing_pages", "funnels",
    "segments", "tags",
    "ai_agents", "ai_agent_executions", "knowledge_documents",
    "conversations",
    "assets",
]

BILLING_TABLES = [
    "subscriptions", "invoices", "credit_wallets",
]

ALL_SECURED_TABLES = TENANT_TABLES + BILLING_TABLES


def upgrade() -> None:
    # ── 1. Enable pgcrypto ──────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── 2. PGP encryption / decryption helpers ──────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION encrypt_pii(plaintext text)
        RETURNS bytea
        LANGUAGE plpgsql
        STABLE
        AS $$
        BEGIN
            IF plaintext IS NULL THEN
                RETURN NULL;
            END IF;
            RETURN pgp_sym_encrypt(
                plaintext,
                current_setting('app.pgp_encryption_key', TRUE),
                'compress-algo=2, cipher-algo=aes256'
            );
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION decrypt_pii(ciphertext bytea)
        RETURNS text
        LANGUAGE plpgsql
        STABLE
        AS $$
        BEGIN
            IF ciphertext IS NULL THEN
                RETURN NULL;
            END IF;
            RETURN pgp_sym_decrypt(
                ciphertext,
                current_setting('app.pgp_encryption_key', TRUE)
            );
        END;
        $$;
    """)

    # ── 3. Add encrypted PII columns to contacts ──────────────────────────
    op.add_column(
        "contacts",
        sa.Column("email_encrypted", postgresql.BYTEA, nullable=True),
    )
    op.add_column(
        "contacts",
        sa.Column("phone_encrypted", postgresql.BYTEA, nullable=True),
    )
    op.add_column(
        "contacts",
        sa.Column("company_encrypted", postgresql.BYTEA, nullable=True),
    )

    # Backfill encrypted columns from existing plaintext
    op.execute("""
        UPDATE contacts
        SET
            email_encrypted = CASE WHEN email IS NOT NULL
                THEN encrypt_pii(email) ELSE NULL END,
            phone_encrypted = CASE WHEN phone IS NOT NULL
                THEN encrypt_pii(phone) ELSE NULL END,
            company_encrypted = CASE WHEN company IS NOT NULL
                THEN encrypt_pii(company) ELSE NULL END
    """)

    # ── 4. Audit log infrastructure ────────────────────────────────────────

    # Audit log table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("action", sa.String(64), nullable=False),  # create, update, delete
        sa.Column("entity_type", sa.String(128), nullable=False),  # table name
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_values", postgresql.JSONB, nullable=True),
        sa.Column("new_values", postgresql.JSONB, nullable=True),
        sa.Column("changed_fields", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    # Audit trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_log_trigger()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            v_tenant_id uuid;
            v_workspace_id uuid;
            v_user_id uuid;
            v_request_id text;
            v_action text;
        BEGIN
            -- Extract context from session variables set by middleware
            v_tenant_id := current_setting('app.current_tenant_id', TRUE)::uuid;
            v_workspace_id := current_setting('app.current_workspace_id', TRUE)::uuid;
            v_user_id := NULLIF(current_setting('app.current_user_id', TRUE), '')::uuid;
            v_request_id := NULLIF(current_setting('app.request_id', TRUE), '');
            v_action := 'update';

            -- Determine the action
            IF TG_OP = 'INSERT' THEN
                v_action := 'create';
                v_tenant_id := COALESCE(v_tenant_id, NEW.tenant_id);
            ELSIF TG_OP = 'UPDATE' THEN
                v_action := 'update';
                v_tenant_id := COALESCE(v_tenant_id, NEW.tenant_id, OLD.tenant_id);
            ELSIF TG_OP = 'DELETE' THEN
                v_action := 'delete';
                v_tenant_id := COALESCE(v_tenant_id, OLD.tenant_id);
            END IF;

            -- Determine workspace_id from the row if available
            BEGIN
                IF TG_OP IN ('INSERT', 'UPDATE') THEN
                    v_workspace_id := COALESCE(v_workspace_id, NEW.workspace_id);
                ELSE
                    v_workspace_id := COALESCE(v_workspace_id, OLD.workspace_id);
                END IF;
            EXCEPTION WHEN undefined_column THEN
                v_workspace_id := NULL;
            END;

            INSERT INTO audit_logs (
                tenant_id, workspace_id, user_id, action,
                entity_type, entity_id, old_values, new_values,
                changed_fields, request_id
            ) VALUES (
                v_tenant_id,
                v_workspace_id,
                v_user_id,
                v_action,
                TG_TABLE_NAME,
                CASE
                    WHEN TG_OP = 'DELETE' THEN OLD.id
                    ELSE NEW.id
                END,
                CASE WHEN TG_OP IN ('UPDATE', 'DELETE')
                    THEN row_to_json(OLD)::jsonb ELSE NULL END,
                CASE WHEN TG_OP IN ('INSERT', 'UPDATE')
                    THEN row_to_json(NEW)::jsonb ELSE NULL END,
                CASE WHEN TG_OP = 'UPDATE'
                    THEN (
                        SELECT array_agg(key) FROM jsonb_each(
                            row_to_json(NEW)::jsonb - row_to_json(OLD)::jsonb
                        ) WHERE row_to_json(NEW)::jsonb -> key IS DISTINCT FROM
                            row_to_json(OLD)::jsonb -> key
                    )
                    ELSE NULL
                END,
                v_request_id
            );

            RETURN COALESCE(NEW, OLD);
        END;
        $$;
    """)

    # ── 5. Marketing tables ─────────────────────────────────────────────────

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), default="draft", nullable=False),
        sa.Column("channel", sa.String(50), nullable=True),
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_audience", postgresql.JSONB, nullable=True),
        sa.Column("schedule_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_optimized", sa.Boolean(), default=False, nullable=False),
        sa.Column("metrics", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "email_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("preheader", sa.String(255), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "landing_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
        sa.Column("published_url", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(50), default="draft", nullable=False),
        sa.Column("seo_meta", postgresql.JSONB, nullable=True),
        sa.Column("ai_generated", sa.Boolean(), default=False, nullable=False),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "funnels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", postgresql.JSONB, nullable=False, default=list),
        sa.Column("conversion_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_optimized", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("criteria", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("contact_count", sa.Integer(), default=0, nullable=False),
        sa.Column("is_dynamic", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 6. AI tables ────────────────────────────────────────────────────────

    op.create_table(
        "ai_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("configuration", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("tools", postgresql.JSONB, nullable=False, default=list),
        sa.Column("memory_config", postgresql.JSONB, nullable=False, default=dict),
        sa.Column("guardrails", postgresql.JSONB, nullable=True, default=list),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_public", sa.Boolean(), default=False, nullable=False),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("total_executions", sa.Integer(), default=0, nullable=False),
        sa.Column("avg_response_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ai_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("input", postgresql.JSONB, nullable=False),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True, default=list),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), default="pending", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_executions_agent_id",
                    "ai_agent_executions", ["agent_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=True, default=list),
        sa.Column("metadata", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("is_indexed", sa.Boolean(), default=False, nullable=False),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ai_agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("message_count", sa.Integer(), default=0, nullable=False),
        sa.Column("is_archived", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True, default=list),
        sa.Column("tool_call_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # ── 7. Billing tables ───────────────────────────────────────────────────

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("plan_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), default="inactive", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_provider", sa.String(50), nullable=True),
        sa.Column("payment_provider_id", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), default=False, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_number", sa.String(50), unique=True, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), default="USD", nullable=False),
        sa.Column("status", sa.String(50), default="pending", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("line_items", postgresql.JSONB, nullable=True, default=list),
        sa.Column("metadata", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "credit_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("balance", sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column("lifetime_credits", sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column("lifetime_spend", sa.Numeric(12, 2), default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 8. Media table ─────────────────────────────────────────────────────

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), default=0, nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("storage_backend", sa.String(50), default="local", nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("is_public", sa.Boolean(), default=False, nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 9. RLS — enable and create policies (AFTER all tables exist) ────────

    for table_name in ALL_SECURED_TABLES:
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')

        # Multi-tenant isolation policy (tenant_id column)
        op.execute(f"""
            CREATE POLICY tenant_isolation ON "{table_name}"
            FOR ALL
            USING (
                tenant_id = current_setting('app.current_tenant_id')::uuid
            )
            WITH CHECK (
                tenant_id = current_setting('app.current_tenant_id')::uuid
            )
        """)

        # Superuser bypass
        op.execute(f"""
            CREATE POLICY superuser_bypass ON "{table_name}"
            FOR ALL
            USING (
                current_setting('app.is_superuser', TRUE) = 'true'
            )
            WITH CHECK (
                current_setting('app.is_superuser', TRUE) = 'true'
            )
        """)

    # RLS for billing tables (subscriptions, invoices, credit_wallets)
    for table_name in BILLING_TABLES:
        op.execute(f"""
            CREATE POLICY billing_isolation ON "{table_name}"
            FOR ALL
            USING (
                tenant_id = current_setting('app.current_tenant_id')::uuid
            )
            WITH CHECK (
                tenant_id = current_setting('app.current_tenant_id')::uuid
            )
        """)

    # ── 10. Apply audit triggers (AFTER all tables exist) ────────────────────

    audit_trigger_tables = [
        "contacts", "deals", "pipelines", "activities",
        "campaigns", "email_templates", "landing_pages",
        "segments", "knowledge_documents", "ai_agents",
        "subscriptions", "invoices",
    ]

    for table_name in audit_trigger_tables:
        op.execute(f"""
            CREATE TRIGGER trg_{table_name}_audit
            AFTER INSERT OR UPDATE OR DELETE ON "{table_name}"
            FOR EACH ROW EXECUTE FUNCTION audit_log_trigger()
        """)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("assets")
    op.drop_table("credit_wallets")
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("knowledge_documents")
    op.drop_table("ai_agent_executions")
    op.drop_table("ai_agents")
    op.drop_table("tags")
    op.drop_table("segments")
    op.drop_table("funnels")
    op.drop_table("landing_pages")
    op.drop_table("email_templates")
    op.drop_table("campaigns")

    # Drop audit triggers
    for table_name in [
        "contacts", "deals", "pipelines", "activities",
        "campaigns", "email_templates", "landing_pages",
        "segments", "knowledge_documents", "ai_agents",
        "subscriptions", "invoices",
    ]:
        op.execute(f'DROP TRIGGER IF EXISTS trg_{table_name}_audit ON "{table_name}"')

    # Drop RLS policies
    for table_name in ALL_SECURED_TABLES:
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table_name}"')
        op.execute(f'DROP POLICY IF EXISTS superuser_bypass ON "{table_name}"')
        op.execute(f'DROP POLICY IF EXISTS billing_isolation ON "{table_name}"')
        op.execute(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY')

    # Drop audit infrastructure
    op.execute("DROP FUNCTION IF EXISTS audit_log_trigger()")
    op.drop_table("audit_logs")

    # Drop encrypted PII columns
    op.drop_column("contacts", "company_encrypted")
    op.drop_column("contacts", "phone_encrypted")
    op.drop_column("contacts", "email_encrypted")

    # Drop pgp helpers
    op.execute("DROP FUNCTION IF EXISTS decrypt_pii(bytea)")
    op.execute("DROP FUNCTION IF EXISTS encrypt_pii(text)")

    # pgcrypto is deliberately NOT dropped in case other extensions depend on it
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
