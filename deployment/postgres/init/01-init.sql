-- =============================================================================
-- Aegis Marketing Cloud — PostgreSQL Initialization
-- Runs once on first container start (docker-entrypoint-initdb.d)
--
-- Enables required extensions: pgcrypto, uuid-ossp, moddatetime
-- Creates the audit trigger function used by history tables.
-- =============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "moddatetime";

-- ── Audit Trigger Function ─────────────────────────────────────────────────
-- Used by all _history tables to capture row-level changes.
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
DECLARE
    _changed_by UUID;
BEGIN
    -- Get the current user from the session variable, fall back to NULL
    BEGIN
        _changed_by := current_setting('app.current_user_id')::UUID;
    EXCEPTION WHEN OTHERS THEN
        _changed_by := NULL;
    END;

    IF TG_OP = 'DELETE' THEN
        INSERT INTO TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME || '_history'
            (operation, changed_by, row_data, changed_at)
        VALUES ('DELETE', _changed_by, row_to_json(OLD), NOW());
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME || '_history'
            (operation, changed_by, row_data, changed_at)
        VALUES ('UPDATE', _changed_by, row_to_json(OLD), NOW());
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ── RLS Helper: Enable RLS on a table with a standard tenant isolation policy
CREATE OR REPLACE FUNCTION enable_tenant_rls(table_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format(
        'ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', table_name
    );
    EXECUTE format(
        'DROP POLICY IF EXISTS tenant_isolation ON %I;', table_name
    );
    EXECUTE format(
        'CREATE POLICY tenant_isolation ON %I
         FOR ALL
         USING (tenant_id = current_setting(''app.current_tenant_id'')::UUID)
         WITH CHECK (tenant_id = current_setting(''app.current_tenant_id'')::UUID);',
        table_name
    );
END;
$$ LANGUAGE plpgsql;

-- ── moddatetime Trigger Helper ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
