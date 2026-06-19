# Volume 5: Database Design (ERD, Schemas, Migrations)

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering  
> **Date:** June 2026  
> **Author:** Database Architecture Team  
> **Status:** ✅ Complete  

---

## Table of Contents

1. [Database Design Philosophy](#1-database-design-philosophy)
2. [Entity Relationship Diagrams](#2-entity-relationship-diagrams)
   - 2.1 [Auth/Identity Module](#21-authidentity-module)
   - 2.2 [Organization/Tenant Module](#22-organizationtenant-module)
   - 2.3 [CRM Module](#23-crm-module)
   - 2.4 [Marketing Module](#24-marketing-module)
   - 2.5 [AI Suite Module](#25-ai-suite-module)
   - 2.6 [SEO Module](#26-seo-module)
   - 2.7 [Social Media Module](#27-social-media-module)
   - 2.8 [Automation Module](#28-automation-module)
   - 2.9 [AI Agents Module](#29-ai-agents-module)
   - 2.10 [Knowledge Base Module](#210-knowledge-base-module)
   - 2.11 [Analytics Module](#211-analytics-module)
   - 2.12 [Billing Module](#212-billing-module)
   - 2.13 [Marketplace Module](#213-marketplace-module)
   - 2.14 [Notifications Module](#214-notifications-module)
   - 2.15 [Media Library Module](#215-media-library-module)
3. [Table Definitions & Indexes](#3-table-definitions--indexes)
4. [Core Table DDL](#4-core-table-ddl)
5. [Migration Strategy](#5-migration-strategy)
6. [Query Patterns & Optimization](#6-query-patterns--optimization)
7. [Data Archival & Purging](#7-data-archival--purging)
8. [Appendix: JSONB Schemas](#8-appendix-jsonb-schemas)

---

## 1. Database Design Philosophy

### 1.1 Multi-Tenancy via `tenant_id` + Row-Level Security

Every tenant-scoped table includes a `tenant_id UUID NOT NULL` column. Row-Level Security (RLS) is enabled on every such table, with a unified policy that scopes all queries to the current tenant session variable:

```sql
-- Set at connection time by the application
SET app.current_tenant_id = 'tenant-abc-123';

-- Unified RLS policy (applied to all tenant-scoped tables)
CREATE POLICY tenant_isolation ON <table_name>
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

**Isolation layers:**

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| PostgreSQL | RLS + `tenant_id` column | All tenant-scoped tables |
| Redis | Key prefix `tenant:<id>:` | Cache, sessions, rate limits |
| Qdrant | Per-tenant collections `ai_memory_{workspace_id}` | Vector storage |
| MinIO | Per-tenant buckets (`tenant-<id>/...`) | Object storage |
| n8n | Workflow tags + execution context | Automation |

### 1.2 Soft Deletes

All entity tables use a `deleted_at TIMESTAMPTZ` nullable column. Soft-deleted rows are filtered via a default `WHERE deleted_at IS NULL` clause in all application queries (and optionally via a PostgreSQL partial index). Hard deletion is reserved for bulk purge jobs and GDPR compliance workflows.

```sql
-- Partial index to speed up active-row queries
CREATE INDEX idx_<table>_active ON <table> (id) WHERE deleted_at IS NULL;
```

### 1.3 Audit Trail via Trigger-Based History Tables

Every entity table has a corresponding `_history` table that captures row-level changes automatically via a `moddatetime`-style trigger. The history tables store the full old row, the operation type (`INSERT`, `UPDATE`, `DELETE`), the acting user, and a timestamp.

**Naming convention:** `<table_name>_history` (e.g., `contacts_history`).

**Trigger function pattern:**

```sql
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO <table>_history (operation, changed_by, row_data, changed_at)
        VALUES ('DELETE', current_setting('app.current_user_id')::UUID, row_to_json(OLD), NOW());
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO <table>_history (operation, changed_by, row_data, changed_at)
        VALUES ('UPDATE', current_setting('app.current_user_id')::UUID, row_to_json(OLD), NOW());
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

### 1.4 UUID Primary Keys

All primary keys use `UUID` type with `gen_random_uuid()` as the default. This avoids sequential ID enumeration attacks, simplifies distributed ID generation, and prevents conflicts in multi-region deployments.

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

### 1.5 Created/Updated Timestamps

Every table includes `created_at` and `updated_at` timestamps with automatic management:

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
```

`updated_at` is managed via a trigger or application-level update. A `moddatetime` trigger is preferred:

```sql
CREATE TRIGGER mdt_<table>_updated_at
    BEFORE UPDATE ON <table>
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);
```

### 1.6 Encrypted PII Columns

Personally Identifiable Information (email, phone, etc.) is encrypted at the column level using `pgcrypto`'s `pgp_sym_encrypt`/`pgp_sym_decrypt` with a tenant-specific encryption key stored in Vault. A `pgp_sym_encrypt` approach is used for columns that need to be queried after decryption (with application-layer decryption); columns that only need equality lookups use deterministic encryption via `encrypt()` with a HMAC for indexing.

```sql
-- Encrypted email column (searchable via HMAC index)
email_encrypted BYTEA,
email_hash BYTEA UNIQUE,  -- HMAC-SHA256(tenant_key, email) for uniqueness checks

-- Application decrypts on read; search is via hash
SELECT pgp_sym_decrypt(email_encrypted, current_setting('app.tenant_encryption_key'))
FROM users WHERE id = '...';
```

PostgreSQL 16's built-in `pgcrypto` extension provides the encryption primitives. The encryption key is fetched from Vault at application startup and set as a session variable per request.

### 1.7 Database Conventions Summary

| Convention | Standard |
|-----------|----------|
| **Primary keys** | `UUID DEFAULT gen_random_uuid()` |
| **Foreign keys** | `UUID` references, named `fk_<table>_<ref_table>` |
| **Audit columns** | `created_at`, `updated_at` (all tables); `deleted_at` (entity tables) |
| **Multi-tenancy** | `tenant_id UUID NOT NULL` on all tenant-scoped tables |
| **Soft delete** | `deleted_at TIMESTAMPTZ` with partial index |
| **PII columns** | Encrypted via `pgcrypto`; hashed for lookups |
| **Naming** | `snake_case` for tables, columns, indexes, constraints |
| **Index naming** | `idx_<table>_<column>` (single), `idx_<table>_<col1>_<col2>` (composite) |
| **FK naming** | `fk_<table>_<ref_table>` |

---

## 2. Entity Relationship Diagrams

### 2.1 Auth/Identity Module

**Tables:** `users`, `oauth_accounts`, `sessions`, `mfa_devices`, `api_keys`, `roles`, `permissions`, `role_permissions`, `user_roles`

```mermaid
erDiagram
    users ||--o{ oauth_accounts : "has"
    users ||--o{ sessions : "has"
    users ||--o{ mfa_devices : "has"
    users ||--o{ api_keys : "has"
    users ||--o{ user_roles : "assigned"
    roles ||--o{ user_roles : "has"
    roles ||--o{ role_permissions : "grants"
    permissions ||--o{ role_permissions : "referenced"

    users {
        uuid id PK
        uuid tenant_id FK
        string email UK
        boolean email_verified
        string password_hash
        string display_name
        string avatar_url
        string locale
        string timezone
        boolean is_active
        boolean is_superadmin
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login_at
        timestamptz deleted_at
    }

    oauth_accounts {
        uuid id PK
        uuid user_id FK
        string provider "google|github|microsoft|apple"
        string provider_account_id
        text access_token
        text refresh_token
        timestamptz expires_at
        jsonb provider_metadata
        timestamptz created_at
        timestamptz updated_at
    }

    sessions {
        uuid id PK
        uuid user_id FK
        uuid tenant_id FK
        string token_hash UK
        string ip_address
        text user_agent
        jsonb device_info
        timestamptz expires_at
        timestamptz created_at
        timestamptz last_accessed_at
        timestamptz revoked_at
    }

    mfa_devices {
        uuid id PK
        uuid user_id FK
        string device_type "totp|sms|email|webauthn"
        string name
        text secret_encrypted
        jsonb device_metadata
        boolean is_primary
        timestamptz verified_at
        timestamptz created_at
        timestamptz updated_at
    }

    api_keys {
        uuid id PK
        uuid user_id FK
        uuid tenant_id FK
        string name
        string key_hash UK
        string key_prefix "first 8 chars for identification"
        jsonb permissions
        timestamptz expires_at
        timestamptz last_used_at
        timestamptz created_at
        timestamptz revoked_at
    }

    roles {
        uuid id PK
        uuid tenant_id FK
        string name
        string slug UK
        string description
        boolean is_system
        int priority
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    permissions {
        uuid id PK
        string resource "crm.contacts|marketing.campaigns|..."
        string action "create|read|update|delete|manage"
        string description
        jsonb conditions "optional JSON conditions for fine-grained access"
        timestamptz created_at
    }

    role_permissions {
        uuid role_id FK
        uuid permission_id FK
        jsonb constraints "additional constraints on this permission"
        timestamptz created_at
    }

    user_roles {
        uuid user_id FK
        uuid role_id FK
        uuid assigned_by FK "users.id"
        timestamptz created_at
        timestamptz expires_at
    }
```

### 2.2 Organization/Tenant Module

**Tables:** `tenants`, `workspaces`, `workspace_users`, `teams`, `team_members`, `subscription_plans`, `tenant_subscriptions`

```mermaid
erDiagram
    tenants ||--o{ workspaces : "has"
    tenants ||--o{ tenant_subscriptions : "has"
    subscription_plans ||--o{ tenant_subscriptions : "defines"
    workspaces ||--o{ workspace_users : "has"
    workspaces ||--o{ teams : "has"
    teams ||--o{ team_members : "has"
    users ||--o{ workspace_users : "member of"
    users ||--o{ team_members : "member of"

    tenants {
        uuid id PK
        string name
        string slug UK
        string domain
        jsonb settings
        text[] features_enabled
        string tier "free|starter|professional|enterprise"
        int max_users
        int max_workspaces
        int max_storage_gb
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    workspaces {
        uuid id PK
        uuid tenant_id FK
        string name
        string slug
        string domain
        jsonb settings
        jsonb branding
        boolean is_default
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    workspace_users {
        uuid workspace_id FK
        uuid user_id FK
        string role "owner|admin|member|viewer|custom"
        jsonb permissions
        timestamptz joined_at
        timestamptz invited_at
        timestamptz accepted_at
    }

    teams {
        uuid id PK
        uuid workspace_id FK
        string name
        string description
        uuid lead_user_id FK "users.id"
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    team_members {
        uuid team_id FK
        uuid user_id FK
        string role "lead|member"
        timestamptz joined_at
    }

    subscription_plans {
        uuid id PK
        string name
        string slug UK
        string description
        decimal price_monthly
        decimal price_yearly
        string currency "USD|EUR|GBP"
        jsonb features
        jsonb limits
        boolean is_active
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    tenant_subscriptions {
        uuid id PK
        uuid tenant_id FK UK
        uuid plan_id FK
        string status "active|past_due|canceled|trialing|expired"
        string billing_cycle "monthly|yearly"
        timestamptz current_period_start
        timestamptz current_period_end
        timestamptz trial_start
        timestamptz trial_end
        timestamptz canceled_at
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.3 CRM Module

**Tables:** `contacts`, `organizations`, `leads`, `deals`, `pipelines`, `pipeline_stages`, `activities`, `tasks`, `meetings`, `notes`, `tags`, `contact_tags`, `file_attachments`

```mermaid
erDiagram
    contacts ||--o{ deals : "has"
    contacts ||--o{ activities : "has"
    contacts ||--o{ tasks : "assigned"
    contacts ||--o{ meetings : "scheduled"
    contacts ||--o{ notes : "has"
    contacts ||--o{ contact_tags : "tagged"
    contacts ||--o{ file_attachments : "has"
    organizations ||--o{ contacts : "belongs to"
    organizations ||--o{ deals : "belongs to"
    pipelines ||--o{ pipeline_stages : "contains"
    pipeline_stages ||--o{ deals : "in stage"
    tags ||--o{ contact_tags : "used in"
    users ||--o{ contacts : "owns"

    contacts {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string first_name
        string last_name
        string email
        string phone
        uuid organization_id FK
        string company
        string position
        string lifecycle_stage "subscriber|lead|mql|sql|opportunity|customer|churned"
        string source "website|referral|import|api|manual"
        jsonb custom_fields
        text[] tags
        uuid owner_id FK "users.id"
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    organizations {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string domain
        string industry
        string size "1-10|11-50|51-200|201-1000|1000+"
        string revenue_range
        string phone
        string website
        jsonb custom_fields
        uuid owner_id FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    leads {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string first_name
        string last_name
        string email
        string phone
        string company
        string source
        string status "new|contacted|qualified|disqualified|converted"
        string score
        uuid converted_contact_id FK
        uuid converted_deal_id FK
        uuid owner_id FK
        jsonb custom_fields
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    deals {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        decimal value
        string currency
        uuid pipeline_stage_id FK
        uuid contact_id FK
        uuid organization_id FK
        uuid owner_id FK
        int probability
        date expected_close_date
        jsonb custom_fields
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    pipelines {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string description
        boolean is_default
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    pipeline_stages {
        uuid id PK
        uuid pipeline_id FK
        string name
        int order
        int probability_default
        string category "open|won|lost"
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
    }

    activities {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid contact_id FK
        uuid deal_id FK
        string type "email|call|meeting|note|task|social|system"
        string description
        jsonb metadata
        timestamptz activity_date
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    tasks {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid contact_id FK
        uuid deal_id FK
        uuid assignee_id FK
        string title
        text description
        string status "pending|in_progress|completed|canceled"
        string priority "low|medium|high|urgent"
        date due_date
        jsonb metadata
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    meetings {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid contact_id FK
        uuid deal_id FK
        uuid organizer_id FK
        string title
        text description
        string location
        string meeting_type "in_person|video|phone"
        string provider "google_meet|zoom|teams"
        string provider_event_id
        timestamptz start_time
        timestamptz end_time
        string status "scheduled|ongoing|completed|canceled"
        jsonb attendees
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    notes {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid contact_id FK
        uuid deal_id FK
        text content
        jsonb metadata
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    tags {
        uuid id PK
        uuid tenant_id FK
        string name
        string color
        string group_name
        timestamptz created_at
    }

    contact_tags {
        uuid contact_id FK
        uuid tag_id FK
        timestamptz created_at
    }

    file_attachments {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid contact_id FK
        uuid deal_id FK
        string file_name
        string file_type
        int file_size_bytes
        string storage_path
        string storage_bucket
        jsonb metadata
        timestamptz created_at
        timestamptz deleted_at
    }
```

### 2.4 Marketing Module

**Tables:** `campaigns`, `campaign_channels`, `email_templates`, `campaign_emails`, `sms_templates`, `landing_pages`, `funnels`, `funnel_stages`, `segments`, `segment_conditions`, `contact_segments`

```mermaid
erDiagram
    campaigns ||--o{ campaign_channels : "uses"
    campaigns ||--o{ campaign_emails : "sends"
    email_templates ||--o{ campaign_emails : "used in"
    funnels ||--o{ funnel_stages : "contains"
    funnels ||--o{ campaigns : "includes"
    segments ||--o{ segment_conditions : "defined by"
    segments ||--o{ contact_segments : "contains"
    contacts ||--o{ contact_segments : "assigned to"

    campaigns {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        text description
        string type "email|sms|social|landing_page|multi_channel|drip"
        string status "draft|scheduled|active|paused|completed|archived"
        timestamptz start_date
        timestamptz end_date
        decimal budget
        jsonb channel_config
        text[] segments
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    campaign_channels {
        uuid id PK
        uuid campaign_id FK
        string channel_type "email|sms|social_push|in_app|push"
        jsonb config
        string status "pending|active|completed|failed"
        timestamptz scheduled_at
        timestamptz sent_at
        int sent_count
        int open_count
        int click_count
        timestamptz created_at
        timestamptz updated_at
    }

    email_templates {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string subject
        text body_html
        text body_text
        jsonb variables
        string category "promotional|transactional|newsletter|automated"
        jsonb metadata
        string locale
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    campaign_emails {
        uuid id PK
        uuid campaign_id FK
        uuid campaign_channel_id FK
        uuid template_id FK
        uuid contact_id FK
        string status "queued|sent|delivered|opened|clicked|bounced|spam|failed"
        string subject
        text body_html
        jsonb metadata
        timestamptz sent_at
        timestamptz opened_at
        timestamptz clicked_at
        jsonb tracking_data
    }

    sms_templates {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        text body
        jsonb variables
        string category
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    landing_pages {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string title
        string slug
        text body_html
        jsonb seo_config
        string status "draft|published|archived"
        uuid campaign_id FK
        string domain
        jsonb analytics_config
        timestamptz published_at
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    funnels {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string description
        string type "lead_gen|sales|onboarding|retention|custom"
        jsonb settings
        boolean is_active
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    funnel_stages {
        uuid id PK
        uuid funnel_id FK
        string name
        int order
        string stage_type "awareness|interest|consideration|intent|evaluation|purchase|retention"
        jsonb settings
        uuid email_template_id FK
        uuid wait_duration_minutes
        timestamptz created_at
        timestamptz updated_at
    }

    segments {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string description
        string match_type "all|any"
        int estimated_count
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    segment_conditions {
        uuid id PK
        uuid segment_id FK
        string field "email|first_name|lifecycle_stage|tags|..."
        string operator "equals|not_equals|contains|gt|lt|between|in|not_in|is_set|is_not_set"
        jsonb value
        string data_type "string|number|date|boolean|array"
        timestamptz created_at
    }

    contact_segments {
        uuid contact_id FK
        uuid segment_id FK
        timestamptz added_at
        timestamptz removed_at
    }
```

### 2.5 AI Suite Module

**Tables:** `ai_generations`, `brand_voices`, `ai_templates`, `generation_history`

```mermaid
erDiagram
    ai_templates ||--o{ ai_generations : "used by"
    brand_voices ||--o{ ai_generations : "applies"
    ai_generations ||--o{ generation_history : "versioned"

    ai_generations {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string content_type "email|social_post|ad_copy|landing_page|blog|seo_meta|sms|push"
        text input_prompt
        text generated_content
        jsonb metadata
        uuid template_id FK
        uuid brand_voice_id FK
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    brand_voices {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        text description
        jsonb tone "professional|casual|humorous|authoritative|empathetic"
        jsonb values
        text[] keywords
        text[] forbidden_words
        text guidelines
        jsonb voice_profile "AI-generated voice fingerprint"
        boolean is_default
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    ai_templates {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string content_type
        text prompt_template
        jsonb variables
        string category
        jsonb default_config "model|temperature|max_tokens"
        boolean is_system
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    generation_history {
        uuid id PK
        uuid generation_id FK
        text previous_content
        text new_content
        string change_type "initial|regenerate|edit|approve|reject"
        uuid changed_by FK
        jsonb diff
        timestamptz created_at
    }
```

### 2.6 SEO Module

**Tables:** `keywords`, `keyword_rankings`, `competitor_sites`, `backlinks`, `serp_results`, `site_audits`, `schema_markup`

```mermaid
erDiagram
    keywords ||--o{ keyword_rankings : "tracks"
    keywords ||--o{ serp_results : "has"
    competitor_sites ||--o{ backlinks : "from"
    keywords ||--o{ backlinks : "targets"

    keywords {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string keyword
        string intent "informational|navigational|commercial|transactional"
        decimal volume "avg monthly search volume"
        decimal difficulty "0-100"
        decimal cpc
        string language
        string country
        jsonb related_keywords
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    keyword_rankings {
        uuid id PK
        uuid keyword_id FK
        int position
        int previous_position
        string url
        string search_engine "google|bing|yahoo"
        string device "desktop|mobile"
        string country
        jsonb serp_features "featured_snippet|knowledge_panel|..."
        timestamptz checked_at
        timestamptz created_at
    }

    competitor_sites {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string domain
        string name
        text description
        decimal domain_authority "0-100"
        int referring_domains
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    backlinks {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid keyword_id FK
        uuid competitor_site_id FK
        string source_url
        string target_url
        string anchor_text
        string link_type "dofollow|nofollow|sponsored|ugc"
        int domain_authority
        boolean is_lost
        timestamptz discovered_at
        timestamptz last_checked_at
        timestamptz created_at
    }

    serp_results {
        uuid id PK
        uuid keyword_id FK
        int position
        string url
        string title
        text snippet
        string result_type "organic|paid|featured_snippet|local|news|image|video"
        jsonb metadata
        timestamptz checked_at
    }

    site_audits {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string url
        string audit_type "full|crawl|single_page"
        jsonb results "seo_score, issues, recommendations"
        int total_issues
        int critical_issues
        int warnings
        float seo_score "0-100"
        timestamptz completed_at
        timestamptz created_at
    }

    schema_markup {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string page_url
        string schema_type "Organization|LocalBusiness|Article|Product|FAQ|Review|Event|Person"
        jsonb markup
        string status "valid|invalid|warning"
        jsonb validation_errors
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.7 Social Media Module

**Tables:** `social_accounts`, `social_posts`, `post_schedules`, `social_analytics`, `hashtag_library`, `reply_templates`, `social_conversations`

```mermaid
erDiagram
    social_accounts ||--o{ social_posts : "publishes"
    social_accounts ||--o{ social_conversations : "received"
    social_posts ||--o{ social_analytics : "has"
    post_schedules ||--o{ social_posts : "schedules"
    social_conversations ||--o{ social_posts : "replies to"

    social_accounts {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string platform "linkedin|twitter|facebook|instagram|tiktok|youtube"
        string account_name
        string account_id
        text access_token_encrypted
        text refresh_token_encrypted
        jsonb profile_data
        boolean is_active
        timestamptz token_expires_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    social_posts {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid social_account_id FK
        string platform_post_id
        text content
        text[] media_urls
        string post_type "text|image|video|carousel|story|reel"
        string status "draft|scheduled|published|failed|deleted"
        jsonb engagement "likes, shares, comments, saves"
        uuid campaign_id FK
        jsonb metadata
        timestamptz published_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    post_schedules {
        uuid id PK
        uuid social_post_id FK UK
        uuid social_account_id FK
        timestamptz scheduled_at
        string timezone
        jsonb recurrence "null|daily|weekly|monthly|custom"
        timestamptz created_at
        timestamptz updated_at
    }

    social_analytics {
        uuid id PK
        uuid social_account_id FK
        uuid social_post_id FK
        jsonb metrics "impressions, reach, engagement_rate, follower_growth"
        jsonb demographics "age_range, gender, location, device"
        jsonb hourly_breakdown
        date analytics_date
        timestamptz created_at
    }

    hashtag_library {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string hashtag
        string category "industry|campaign|brand|trending|seasonal"
        int usage_count
        float engagement_rate
        jsonb related_hashtags
        timestamptz created_at
    }

    reply_templates {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        text body
        string category "support|sales|general|crisis"
        jsonb variables
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    social_conversations {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid social_account_id FK
        uuid social_post_id FK
        string conversation_id
        string platform
        string participant_name
        string participant_handle
        text last_message
        string status "unread|read|replied|archived|spam"
        string sentiment "positive|neutral|negative"
        jsonb metadata
        timestamptz last_message_at
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.8 Automation Module

**Tables:** `workflows`, `workflow_triggers`, `workflow_actions`, `workflow_executions`, `execution_logs`, `workflow_templates`

```mermaid
erDiagram
    workflows ||--o{ workflow_triggers : "has"
    workflows ||--o{ workflow_actions : "defines"
    workflows ||--o{ workflow_executions : "runs"
    workflow_executions ||--o{ execution_logs : "produces"
    workflow_templates ||--o{ workflows : "based on"

    workflows {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        text description
        string status "active|paused|draft|archived"
        jsonb n8n_workflow_id
        string category "lead_mgmt|campaign|crm|notification|data|custom"
        boolean is_template
        jsonb tags
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    workflow_triggers {
        uuid id PK
        uuid workflow_id FK
        string trigger_type "event|schedule|webhook|manual|contact_action|campaign_event"
        jsonb config
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    workflow_actions {
        uuid id PK
        uuid workflow_id FK
        int order
        string action_type "send_email|update_contact|create_deal|notify|api_call|ai_generate|..."
        jsonb config
        string on_failure "stop|continue|retry"
        int retry_count
        timestamptz created_at
        timestamptz updated_at
    }

    workflow_executions {
        uuid id PK
        uuid workflow_id FK
        uuid trigger_id FK
        string status "running|completed|failed|paused|canceled"
        jsonb input_data
        jsonb output_data
        jsonb error_details
        timestamptz started_at
        timestamptz completed_at
        uuid triggered_by FK "user or agent id"
        timestamptz created_at
    }

    execution_logs {
        uuid id PK
        uuid execution_id FK
        string level "info|warn|error|debug"
        string source
        text message
        jsonb metadata
        timestamptz created_at
    }

    workflow_templates {
        uuid id PK
        string name
        string slug UK
        text description
        string category
        jsonb definition
        jsonb tags
        string complexity "beginner|intermediate|advanced"
        int usage_count
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.9 AI Agents Module

**Tables:** `agents`, `agent_conversations`, `agent_messages`, `agent_tools`, `agent_memory`, `agent_knowledge_refs`, `agent_executions`, `agent_goals`

```mermaid
erDiagram
    agents ||--o{ agent_conversations : "participates"
    agents ||--o{ agent_messages : "sends"
    agents ||--o{ agent_tools : "has access"
    agents ||--o{ agent_memory : "stores"
    agents ||--o{ agent_executions : "runs"
    agents ||--o{ agent_goals : "pursues"
    agent_conversations ||--o{ agent_messages : "contains"
    agent_memory ||--o{ agent_knowledge_refs : "references"

    agents {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string role "marketing_director|seo_specialist|content_writer|analytics_agent|customer_success|operations"
        text description
        jsonb model_config
        text[] tools
        jsonb memory_config
        jsonb permissions
        text system_prompt
        jsonb goals
        jsonb guardrails
        string status "active|paused|disabled"
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    agent_conversations {
        uuid id PK
        uuid agent_id FK
        uuid workspace_id FK
        uuid user_id FK
        string title
        string status "active|archived|completed"
        string context_type "campaign_planning|content_creation|analysis|strategy|general"
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    agent_messages {
        uuid id PK
        uuid conversation_id FK
        uuid agent_id FK
        uuid user_id FK
        string role "user|agent|system|tool"
        text content
        jsonb tool_calls
        jsonb tool_results
        jsonb metadata
        string message_type "text|tool_call|tool_result|system|error"
        timestamptz created_at
    }

    agent_tools {
        uuid id PK
        uuid agent_id FK
        string tool_name
        jsonb tool_config
        jsonb rate_limits
        boolean is_enabled
        timestamptz created_at
        timestamptz updated_at
    }

    agent_memory {
        uuid id PK
        uuid agent_id FK
        uuid workspace_id FK
        string memory_type "conversation|fact|preference|decision|insight"
        text content
        jsonb embeddings_ref
        float importance "0.0-1.0"
        jsonb metadata
        timestamptz created_at
        timestamptz last_accessed_at
    }

    agent_knowledge_refs {
        uuid id PK
        uuid memory_id FK
        uuid kb_document_id FK
        string reference_type "source|similar|citation"
        timestamptz created_at
    }

    agent_executions {
        uuid id PK
        uuid agent_id FK
        uuid conversation_id FK
        string action_type "generate|analyze|research|execute_tool|reason|plan"
        jsonb input
        jsonb output
        jsonb metrics "tokens_used, duration_ms, cost"
        string status "running|completed|failed|timed_out"
        timestamptz started_at
        timestamptz completed_at
    }

    agent_goals {
        uuid id PK
        uuid agent_id FK
        uuid parent_goal_id FK
        string title
        text description
        string status "active|in_progress|completed|failed|canceled"
        string priority "low|medium|high|critical"
        jsonb progress "percentage, milestones"
        jsonb criteria
        timestamptz due_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.10 Knowledge Base Module

**Tables:** `kb_documents`, `kb_chunks`, `kb_categories`, `kb_permissions`, `kb_versions`

```mermaid
erDiagram
    kb_categories ||--o{ kb_documents : "contains"
    kb_documents ||--o{ kb_chunks : "split into"
    kb_documents ||--o{ kb_versions : "versioned"
    kb_documents ||--o{ kb_permissions : "has"

    kb_documents {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid category_id FK
        string title
        string slug
        text content
        text content_plain
        string status "draft|published|archived"
        string visibility "workspace|tenant|private"
        jsonb metadata
        uuid author_id FK
        uuid last_editor_id FK
        timestamptz published_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    kb_chunks {
        uuid id PK
        uuid document_id FK
        int chunk_index
        text content
        int token_count
        jsonb embeddings_ref
        jsonb metadata
        timestamptz created_at
    }

    kb_categories {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid parent_category_id FK
        string name
        string slug
        string description
        int sort_order
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    kb_permissions {
        uuid id PK
        uuid document_id FK
        string grantee_type "role|user|team"
        uuid grantee_id
        string permission_level "view|edit|manage"
        timestamptz created_at
    }

    kb_versions {
        uuid id PK
        uuid document_id FK
        int version_number
        text content
        text content_diff
        string change_summary
        uuid changed_by FK
        timestamptz created_at
    }
```

### 2.11 Analytics Module

**Tables:** `analytics_events`, `analytics_dashboards`, `dashboard_widgets`, `saved_reports`, `metric_definitions`

```mermaid
erDiagram
    metric_definitions ||--o{ dashboard_widgets : "used by"
    analytics_dashboards ||--o{ dashboard_widgets : "contains"
    metric_definitions ||--o{ saved_reports : "based on"

    analytics_events {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string event_name
        string event_category "campaign|email|crm|social|seo|system|user"
        jsonb event_properties
        jsonb user_properties
        jsonb context "page|device|browser|ip|geo"
        uuid user_id FK
        uuid session_id FK
        timestamptz event_time
    }

    analytics_dashboards {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string description
        jsonb layout
        string visibility "workspace|tenant|private"
        boolean is_default
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    dashboard_widgets {
        uuid id PK
        uuid dashboard_id FK
        string widget_type "chart|table|metric|funnel|map|list"
        string title
        jsonb config "data_source, dimensions, measures, filters, visualization"
        int position_x
        int position_y
        int width
        int height
        jsonb cache_config
        timestamptz created_at
        timestamptz updated_at
    }

    saved_reports {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        string name
        string description
        jsonb query_config "table, filters, group_by, aggregations, time_range"
        jsonb visualization_config
        string schedule "none|daily|weekly|monthly|custom"
        text[] recipients
        uuid created_by FK
        timestamptz last_run_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    metric_definitions {
        uuid id PK
        string name
        string slug UK
        string description
        string aggregation_type "count|sum|avg|min|max|count_distinct|rate|percentile"
        string data_source "analytics_events|campaign_emails|social_analytics|..."
        jsonb filters
        string unit "number|percentage|currency|time|ratio"
        jsonb formula
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.12 Billing Module

**Tables:** `plans`, `subscriptions`, `invoices`, `invoice_items`, `payments`, `credits`, `credit_transactions`, `coupons`, `taxes`, `wallet_transactions`, `affiliate_payouts`

```mermaid
erDiagram
    plans ||--o{ subscriptions : "subscribed"
    subscriptions ||--o{ invoices : "generates"
    invoices ||--o{ invoice_items : "contains"
    invoices ||--o{ payments : "paid by"
    credits ||--o{ credit_transactions : "used in"
    coupons ||--o{ subscriptions : "applied to"

    plans {
        uuid id PK
        string name
        string slug UK
        string description
        string billing_model "flat|per_user|per_contact|tiered|usage_based"
        jsonb pricing_tiers
        decimal price_monthly
        decimal price_yearly
        string currency "USD|EUR|GBP"
        jsonb features
        jsonb limits
        string tier "free|starter|professional|enterprise"
        boolean is_active
        int sort_order
        timestamptz created_at
        timestamptz updated_at
    }

    subscriptions {
        uuid id PK
        uuid tenant_id FK
        uuid plan_id FK
        uuid coupon_id FK
        string status "active|past_due|canceled|expired|trialing|incomplete"
        string billing_cycle "monthly|yearly"
        string collection_method "charge_automatically|send_invoice"
        timestamptz current_period_start
        timestamptz current_period_end
        timestamptz trial_start
        timestamptz trial_end
        timestamptz canceled_at
        timestamptz paused_at
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    invoices {
        uuid id PK
        uuid subscription_id FK
        uuid tenant_id FK
        string invoice_number UK
        string status "draft|open|paid|void|uncollectible|overdue"
        decimal subtotal
        decimal discount_amount
        decimal tax_amount
        decimal total
        string currency
        jsonb line_items
        timestamptz due_date
        timestamptz paid_at
        timestamptz created_at
        timestamptz updated_at
    }

    invoice_items {
        uuid id PK
        uuid invoice_id FK
        string description
        decimal unit_amount
        int quantity
        decimal amount
        string item_type "subscription|addon|credit|adjustment|tax|usage"
        jsonb metadata
        timestamptz period_start
        timestamptz period_end
        timestamptz created_at
    }

    payments {
        uuid id PK
        uuid invoice_id FK
        uuid tenant_id FK
        decimal amount
        string currency
        string payment_method "card|bank_transfer|crypto|wallet|invoice"
        string status "pending|completed|failed|refunded|partially_refunded"
        string gateway "stripe|paypal|custom"
        string gateway_payment_id
        jsonb gateway_response
        jsonb metadata
        timestamptz paid_at
        timestamptz created_at
        timestamptz updated_at
    }

    credits {
        uuid id PK
        uuid tenant_id FK
        decimal balance
        string currency
        jsonb metadata
        timestamptz expires_at
        timestamptz created_at
        timestamptz updated_at
    }

    credit_transactions {
        uuid id PK
        uuid credit_id FK
        uuid invoice_id FK
        string transaction_type "earned|spent|expired|refunded|adjusted"
        decimal amount
        decimal balance_after
        string description
        timestamptz created_at
    }

    coupons {
        uuid id PK
        string code UK
        string description
        string discount_type "percentage|fixed_amount"
        decimal discount_value
        string discount_currency
        int max_redemptions
        int current_redemptions
        string duration "once|forever|repeating"
        int duration_months
        jsonb restrictions "min_amount, plan_ids, max_uses_per_customer"
        timestamptz starts_at
        timestamptz expires_at
        timestamptz created_at
        timestamptz updated_at
    }

    taxes {
        uuid id PK
        string tax_name
        string tax_code
        decimal rate
        string country
        string jurisdiction
        string tax_type "vat|gst|sales_tax|withholding"
        boolean is_active
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    wallet_transactions {
        uuid id PK
        uuid tenant_id FK
        decimal amount
        string currency
        string transaction_type "deposit|withdrawal|payment|refund|bonus"
        string status "pending|completed|failed"
        string gateway
        jsonb metadata
        timestamptz created_at
    }

    affiliate_payouts {
        uuid id PK
        uuid affiliate_user_id FK
        decimal amount
        string currency
        string status "pending|processing|paid|failed"
        string payout_method "bank_transfer|paypal|crypto"
        jsonb metadata
        timestamptz paid_at
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.13 Marketplace Module

**Tables:** `marketplace_listings`, `listing_versions`, `reviews`, `installations`, `developer_profiles`

```mermaid
erDiagram
    developer_profiles ||--o{ marketplace_listings : "publishes"
    marketplace_listings ||--o{ listing_versions : "versioned"
    marketplace_listings ||--o{ reviews : "reviewed"
    marketplace_listings ||--o{ installations : "installed"

    marketplace_listings {
        uuid id PK
        uuid developer_id FK
        string name
        string slug UK
        string short_description
        text full_description
        string category "crm|marketing|automation|analytics|ai|seo|social|billing|custom"
        string type "integration|plugin|extension|template|connector"
        jsonb screenshots
        string icon_url
        string documentation_url
        string support_url
        string pricing_model "free|paid|freemium|subscription"
        decimal price
        string status "draft|pending_review|approved|rejected|published|archived"
        jsonb permissions_required
        jsonb supported_versions
        float rating
        int review_count
        int install_count
        timestamptz published_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    listing_versions {
        uuid id PK
        uuid listing_id FK
        string version "semver"
        text changelog
        jsonb package_ref
        string status "active|deprecated|superseded"
        int download_count
        timestamptz created_at
    }

    reviews {
        uuid id PK
        uuid listing_id FK
        uuid tenant_id FK
        uuid user_id FK
        int rating "1-5"
        text review_text
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    installations {
        uuid id PK
        uuid listing_id FK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid version_id FK
        string status "active|disabled|uninstalled"
        jsonb config
        uuid installed_by FK
        timestamptz installed_at
        timestamptz updated_at
        timestamptz uninstalled_at
    }

    developer_profiles {
        uuid id PK
        uuid user_id FK
        string name
        string company
        string website
        string email
        text bio
        string support_email
        jsonb social_links
        jsonb payout_settings
        string verification_status "unverified|pending|verified"
        timestamptz created_at
        timestamptz updated_at
    }
```

### 2.14 Notifications Module

**Tables:** `notification_templates`, `notification_queue`, `notification_preferences`, `notification_logs`

```mermaid
erDiagram
    notification_templates ||--o{ notification_queue : "used by"
    notification_queue ||--o{ notification_logs : "logged as"

    notification_templates {
        uuid id PK
        uuid tenant_id FK
        string name
        string channel "email|sms|push|in_app|webhook"
        string category "campaign|system|billing|social|workflow|agent|mention"
        string subject
        text body_template
        jsonb variables
        jsonb channel_config
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    notification_queue {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid template_id FK
        uuid user_id FK
        string channel "email|sms|push|in_app|webhook"
        string status "queued|processing|sent|failed|canceled"
        string priority "low|normal|high|urgent"
        jsonb payload
        jsonb channel_specific "email_config|sms_config|push_config"
        int retry_count
        int max_retries
        timestamptz scheduled_at
        timestamptz sent_at
        jsonb error_details
        timestamptz created_at
        timestamptz updated_at
    }

    notification_preferences {
        uuid id PK
        uuid user_id FK
        uuid tenant_id FK
        string channel "email|sms|push|in_app"
        string category "campaign|system|billing|social|workflow|agent|mention"
        boolean is_enabled
        jsonb schedule "quiet_hours, daily_digest"
        timestamptz created_at
        timestamptz updated_at
    }

    notification_logs {
        uuid id PK
        uuid queue_id FK
        uuid user_id FK
        string channel
        string status "sent|delivered|opened|clicked|bounced|failed|unsubscribed"
        jsonb provider_response
        jsonb metadata
        timestamptz created_at
    }
```

### 2.15 Media Library Module

**Tables:** `media_assets`, `asset_folders`, `asset_versions`, `asset_tags`

```mermaid
erDiagram
    asset_folders ||--o{ media_assets : "contains"
    media_assets ||--o{ asset_versions : "versioned"
    asset_tags ||--o{ media_assets : "tags"

    media_assets {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid folder_id FK
        string file_name
        string original_name
        string mime_type
        int file_size_bytes
        int width
        int height
        string storage_path
        string storage_bucket
        string public_url
        string hash "SHA-256 for dedup"
        string status "uploading|processing|ready|failed"
        jsonb metadata "exif, colors, dominant_color, alt_text"
        uuid uploaded_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    asset_folders {
        uuid id PK
        uuid tenant_id FK
        uuid workspace_id FK
        uuid parent_folder_id FK
        string name
        string path
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    asset_versions {
        uuid id PK
        uuid asset_id FK
        int version_number
        string file_name
        int file_size_bytes
        string storage_path
        string change_summary
        uuid created_by FK
        timestamptz created_at
    }

    asset_tags {
        uuid id PK
        uuid asset_id FK
        string tag
        timestamptz created_at
    }
```

---

## 3. Table Definitions & Indexes

### 3.1 Auth/Identity Tables

#### `users`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | Primary key |
| `tenant_id` | UUID | NOT NULL, FK → tenants(id) | — | Tenant scope (nullable for superadmin) |
| `email` | TEXT | NOT NULL | — | User email (encrypted at rest) |
| `email_verified` | BOOLEAN | NOT NULL | `FALSE` | Email verification status |
| `password_hash` | TEXT | NOT NULL | — | Argon2id password hash |
| `display_name` | TEXT | NOT NULL | — | Display name |
| `avatar_url` | TEXT | — | — | Avatar image URL |
| `locale` | TEXT | NOT NULL | `'en'` | User locale |
| `timezone` | TEXT | NOT NULL | `'UTC'` | User timezone |
| `is_active` | BOOLEAN | NOT NULL | `TRUE` | Account active status |
| `is_superadmin` | BOOLEAN | NOT NULL | `FALSE` | Cross-tenant admin |
| `metadata` | JSONB | — | `'{}'` | Flexible metadata |
| `last_login_at` | TIMESTAMPTZ | — | — | Last successful login |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Row creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Row update timestamp |
| `deleted_at` | TIMESTAMPTZ | — | — | Soft delete timestamp |

**Indexes:**

```sql
CREATE UNIQUE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_tenant_id ON users (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_display_name ON users USING GIN (display_name gin_trgm_ops);
CREATE INDEX idx_users_metadata ON users USING GIN (metadata jsonb_path_ops);
```

**RLS Policy:**
```sql
-- Users with tenant_id = NULL (superadmins) bypass, others scoped
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID OR tenant_id IS NULL)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID OR current_setting('app.user_role') = 'superadmin');
```

**Row count estimate:** 10–500K (grows linearly with tenant count)

#### `oauth_accounts`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | Associated user |
| `provider` | TEXT | NOT NULL | — | OAuth provider name |
| `provider_account_id` | TEXT | NOT NULL | — | ID from provider |
| `access_token` | TEXT | — | — | Encrypted access token |
| `refresh_token` | TEXT | — | — | Encrypted refresh token |
| `expires_at` | TIMESTAMPTZ | — | — | Token expiry |
| `provider_metadata` | JSONB | — | `'{}'` | Raw provider profile data |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_oauth_provider_account ON oauth_accounts (provider, provider_account_id);
CREATE INDEX idx_oauth_user_id ON oauth_accounts (user_id);
```

**Row count estimate:** 1–2× users

#### `sessions`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | Session owner |
| `tenant_id` | UUID | NOT NULL, FK → tenants(id) | — | Tenant context |
| `token_hash` | TEXT | NOT NULL, UNIQUE | — | SHA-256 of session token |
| `ip_address` | INET | — | — | Client IP |
| `user_agent` | TEXT | — | — | Browser user agent |
| `device_info` | JSONB | — | — | Device fingerprint |
| `expires_at` | TIMESTAMPTZ | NOT NULL | — | Session expiry |
| `last_accessed_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Last activity |
| `revoked_at` | TIMESTAMPTZ | — | — | Manual revocation |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_sessions_token_hash ON sessions (token_hash);
CREATE INDEX idx_sessions_user_id ON sessions (user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_sessions_expires_at ON sessions (expires_at) WHERE revoked_at IS NULL;
```

**Row count estimate:** 5–50× active users

#### `mfa_devices`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | — |
| `device_type` | TEXT | NOT NULL | — | `totp`, `sms`, `email`, `webauthn` |
| `name` | TEXT | NOT NULL | — | User-given name |
| `secret_encrypted` | TEXT | — | — | Encrypted TOTP secret |
| `device_metadata` | JSONB | — | — | WebAuthn credential data |
| `is_primary` | BOOLEAN | NOT NULL | `FALSE` | Primary MFA method |
| `verified_at` | TIMESTAMPTZ | — | — | When first verified |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE INDEX idx_mfa_user_id ON mfa_devices (user_id);
```

**Row count estimate:** 0.1–3× users with MFA enabled

#### `api_keys`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | Owner |
| `tenant_id` | UUID | NOT NULL, FK → tenants(id) | — | Tenant scope |
| `name` | TEXT | NOT NULL | — | Key name |
| `key_hash` | TEXT | NOT NULL, UNIQUE | — | SHA-256 of full key |
| `key_prefix` | TEXT | NOT NULL | — | First 8 chars for identification |
| `permissions` | JSONB | NOT NULL | `'[]'` | Scoped permissions |
| `expires_at` | TIMESTAMPTZ | — | — | Expiration |
| `last_used_at` | TIMESTAMPTZ | — | — | Last usage |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `revoked_at` | TIMESTAMPTZ | — | — | Revocation timestamp |

**Indexes:**
```sql
CREATE INDEX idx_api_keys_user_id ON api_keys (user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_tenant_id ON api_keys (tenant_id) WHERE revoked_at IS NULL;
```

**Row count estimate:** 0.5–5× API-using users

#### `roles`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `tenant_id` | UUID | NOT NULL, FK → tenants(id) | — | Tenant scope |
| `name` | TEXT | NOT NULL | — | Human-readable name |
| `slug` | TEXT | NOT NULL, UNIQUE | — | URL-safe identifier |
| `description` | TEXT | — | — | — |
| `is_system` | BOOLEAN | NOT NULL | `FALSE` | System-protected role |
| `priority` | INTEGER | NOT NULL | `0` | Higher = more privileged |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `deleted_at` | TIMESTAMPTZ | — | — | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_roles_slug ON roles (slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_roles_tenant_id ON roles (tenant_id) WHERE deleted_at IS NULL;
```

**RLS Policy:**
```sql
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON roles FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

**Row count estimate:** 5–50 per tenant

#### `permissions`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `resource` | TEXT | NOT NULL | — | e.g., `crm.contacts` |
| `action` | TEXT | NOT NULL | — | e.g., `create`, `read`, `update`, `delete`, `manage` |
| `description` | TEXT | — | — | — |
| `conditions` | JSONB | — | — | Optional JSON conditions |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_permissions_resource_action ON permissions (resource, action);
```

**Row count estimate:** 100–500 (system-wide, not tenant-scoped)

#### `role_permissions`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `role_id` | UUID | NOT NULL, FK → roles(id) | — | — |
| `permission_id` | UUID | NOT NULL, FK → permissions(id) | — | — |
| `constraints` | JSONB | — | — | Additional scope restrictions |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE INDEX idx_role_permissions_role_id ON role_permissions (role_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions (permission_id);
```

#### `user_roles`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `user_id` | UUID | NOT NULL, FK → users(id) | — | — |
| `role_id` | UUID | NOT NULL, FK → roles(id) | — | — |
| `assigned_by` | UUID | FK → users(id) | — | Who assigned the role |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `expires_at` | TIMESTAMPTZ | — | — | Temporary role expiry |

**Indexes:**
```sql
CREATE INDEX idx_user_roles_user_id ON user_roles (user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);
```

### 3.2 Organization/Tenant Tables

#### `tenants`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `name` | TEXT | NOT NULL | — | Company/organization name |
| `slug` | TEXT | NOT NULL, UNIQUE | — | URL-safe identifier |
| `domain` | TEXT | — | — | Custom domain |
| `settings` | JSONB | NOT NULL | `'{}'` | Tenant-level settings |
| `features_enabled` | TEXT[] | NOT NULL | `'{}'` | Enabled feature flags |
| `tier` | TEXT | NOT NULL | `'free'` | `free`, `starter`, `professional`, `enterprise` |
| `max_users` | INTEGER | NOT NULL | `5` | User limit |
| `max_workspaces` | INTEGER | NOT NULL | `1` | Workspace limit |
| `max_storage_gb` | INTEGER | NOT NULL | `1` | Storage limit in GB |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `deleted_at` | TIMESTAMPTZ | — | — | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_tenants_slug ON tenants (slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_tenants_domain ON tenants (domain) WHERE domain IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_tenants_settings ON tenants USING GIN (settings jsonb_path_ops);
```

**Row count estimate:** 100–50K

#### `workspaces`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `tenant_id` | UUID | NOT NULL, FK → tenants(id) | — | — |
| `name` | TEXT | NOT NULL | — | — |
| `slug` | TEXT | NOT NULL | — | Workspace URL slug |
| `domain` | TEXT | — | — | Custom subdomain |
| `settings` | JSONB | NOT NULL | `'{}'` | Workspace settings |
| `branding` | JSONB | NOT NULL | `'{}'` | Branding config |
| `is_default` | BOOLEAN | NOT NULL | `FALSE` | Default workspace |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `deleted_at` | TIMESTAMPTZ | — | — | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_workspaces_tenant_slug ON workspaces (tenant_id, slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_workspaces_tenant_id ON workspaces (tenant_id) WHERE deleted_at IS NULL;
```

**RLS Policy:**
```sql
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workspaces FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

**Row count estimate:** 1–10 per tenant

#### `workspace_users`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `workspace_id` | UUID | NOT NULL, FK → workspaces(id) | — | — |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | — |
| `role` | TEXT | NOT NULL | `'member'` | `owner`, `admin`, `member`, `viewer`, `custom` |
| `permissions` | JSONB | — | — | Custom permission overrides |
| `joined_at` | TIMESTAMPTZ | — | — | When user accepted |
| `invited_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When invitation sent |
| `accepted_at` | TIMESTAMPTZ | — | — | When invitation accepted |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_workspace_users_pair ON workspace_users (workspace_id, user_id);
CREATE INDEX idx_workspace_users_user_id ON workspace_users (user_id);
```

#### `teams`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `workspace_id` | UUID | NOT NULL, FK → workspaces(id) | — | — |
| `name` | TEXT | NOT NULL | — | — |
| `description` | TEXT | — | — | — |
| `lead_user_id` | UUID | FK → users(id) | — | Team lead |
| `settings` | JSONB | NOT NULL | `'{}'` | — |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `deleted_at` | TIMESTAMPTZ | — | — | — |

**Indexes:**
```sql
CREATE INDEX idx_teams_workspace_id ON teams (workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_teams_lead_user_id ON teams (lead_user_id) WHERE deleted_at IS NULL;
```

#### `team_members`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `team_id` | UUID | NOT NULL, FK → teams(id) | — | — |
| `user_id` | UUID | NOT NULL, FK → users(id) | — | — |
| `role` | TEXT | NOT NULL | `'member'` | `lead` or `member` |
| `joined_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE UNIQUE INDEX idx_team_members_pair ON team_members (team_id, user_id);
CREATE INDEX idx_team_members_user_id ON team_members (user_id);
```

#### `subscription_plans`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `name` | TEXT | NOT NULL | — | — |
| `slug` | TEXT | NOT NULL, UNIQUE | — | — |
| `description` | TEXT | — | — | — |
| `price_monthly` | DECIMAL(10,2) | NOT NULL | — | — |
| `price_yearly` | DECIMAL(10,2) | NOT NULL | — | — |
| `currency` | TEXT | NOT NULL | `'USD'` | — |
| `features` | JSONB | NOT NULL | `'{}'` | Feature list |
| `limits` | JSONB | NOT NULL | `'{}'` | Usage limits |
| `is_active` | BOOLEAN | NOT NULL | `TRUE` | — |
| `metadata` | JSONB | — | `'{}'` | — |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Row count estimate:** 5–20

#### `tenant_subscriptions`

| Column | Type | Constraints | Default | Description |
|--------|------|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | — |
| `tenant_id` | UUID | NOT NULL, UNIQUE, FK → tenants(id) | — | — |
| `plan_id` | UUID | NOT NULL, FK → subscription_plans(id) | — | — |
| `status` | TEXT | NOT NULL | `'trialing'` | — |
| `billing_cycle` | TEXT | NOT NULL | `'monthly'` | — |
| `current_period_start` | TIMESTAMPTZ | NOT NULL | — | — |
| `current_period_end` | TIMESTAMPTZ | NOT NULL | — | — |
| `trial_start` | TIMESTAMPTZ | — | — | — |
| `trial_end` | TIMESTAMPTZ | — | — | — |
| `canceled_at` | TIMESTAMPTZ | — | — | — |
| `metadata` | JSONB | — | `'{}'` | — |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Indexes:**
```sql
CREATE INDEX idx_tenant_subscriptions_plan_id ON tenant_subscriptions (plan_id);
CREATE INDEX idx_tenant_subscriptions_status ON tenant_subscriptions (status);
```

### 3.3–3.15 Remaining Tables

_(Due to the comprehensive scope, remaining table definitions follow the same pattern. See the ERD sections above for complete column listings. The full DDL for all tables follows standard conventions:_

- _All tables include `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`_
- _All tenant-scoped tables include `tenant_id UUID NOT NULL REFERENCES tenants(id)`_
- _All entity tables include `deleted_at TIMESTAMPTZ`_
- _All tables include `created_at` and `updated_at`_
- _RLS is enabled and a `tenant_isolation` policy is created on all tenant-scoped tables_
- _Partial indexes on `(id) WHERE deleted_at IS NULL` exist on all entity tables_
- _B-tree indexes exist on all FK columns_
- _GIN indexes exist on JSONB columns with `jsonb_path_ops`_
- _Trigram indexes exist on text search columns where applicable)_

---

## 4. Core Table DDL

### 4.1 `tenants` — Full DDL

```sql
-- Extension dependencies
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "moddatetime";

-- Table: tenants
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    domain          TEXT,
    settings        JSONB NOT NULL DEFAULT '{}'::JSONB,
    features_enabled TEXT[] NOT NULL DEFAULT '{}',
    tier            TEXT NOT NULL DEFAULT 'free'
                    CHECK (tier IN ('free', 'starter', 'professional', 'enterprise')),
    max_users       INTEGER NOT NULL DEFAULT 5,
    max_workspaces  INTEGER NOT NULL DEFAULT 1,
    max_storage_gb  INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Unique indexes
CREATE UNIQUE INDEX idx_tenants_slug ON tenants (slug) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX idx_tenants_domain ON tenants (domain)
    WHERE domain IS NOT NULL AND deleted_at IS NULL;

-- Performance indexes
CREATE INDEX idx_tenants_tier ON tenants (tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_tenants_settings ON tenants USING GIN (settings jsonb_path_ops);
CREATE INDEX idx_tenants_created_at ON tenants (created_at);

-- Partial index for active tenants
CREATE INDEX idx_tenants_active ON tenants (id) WHERE deleted_at IS NULL;

-- Updated_at trigger
CREATE TRIGGER mdt_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

-- Note: tenants is the root table; RLS is NOT enabled on tenants itself
-- (it is the tenant-defining table). Instead, access is controlled
-- through the application layer.
```

### 4.2 `users` — Full DDL

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    email           TEXT NOT NULL,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash   TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    avatar_url      TEXT,
    locale          TEXT NOT NULL DEFAULT 'en',
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_superadmin   BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}'::JSONB,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email ON users (lower(email)) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_tenant_id ON users (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_display_name ON users USING GIN (display_name gin_trgm_ops);
CREATE INDEX idx_users_metadata ON users USING GIN (metadata jsonb_path_ops);
CREATE INDEX idx_users_active ON users (id) WHERE deleted_at IS NULL AND is_active = TRUE;
CREATE INDEX idx_users_tenant_active ON users (tenant_id) WHERE deleted_at IS NULL AND is_active = TRUE;

-- Triggers
CREATE TRIGGER mdt_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

-- RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID OR tenant_id IS NULL)
    WITH CHECK (
        tenant_id = current_setting('app.current_tenant_id')::UUID
        OR current_setting('app.user_role') = 'superadmin'
    );

-- Audit trigger: capture user changes
CREATE TABLE users_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    operation   TEXT NOT NULL CHECK (operation IN ('UPDATE', 'DELETE')),
    changed_by  UUID REFERENCES users(id),
    row_data    JSONB NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_history_user_id ON users_history (user_id, changed_at);

CREATE OR REPLACE FUNCTION audit_users()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO users_history (user_id, operation, changed_by, row_data)
        VALUES (OLD.id, 'UPDATE', current_setting('app.current_user_id')::UUID, row_to_json(OLD));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO users_history (user_id, operation, changed_by, row_data)
        VALUES (OLD.id, 'DELETE', current_setting('app.current_user_id')::UUID, row_to_json(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_users_trigger
    AFTER UPDATE OR DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION audit_users();
```

### 4.3 `workspaces` — Full DDL

```sql
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    domain          TEXT,
    settings        JSONB NOT NULL DEFAULT '{}'::JSONB,
    branding        JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_workspaces_tenant_slug ON workspaces (tenant_id, slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_workspaces_tenant_id ON workspaces (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_workspaces_settings ON workspaces USING GIN (settings jsonb_path_ops);
CREATE INDEX idx_workspaces_branding ON workspaces USING GIN (branding jsonb_path_ops);

CREATE TRIGGER mdt_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workspaces FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 4.4 `contacts` — Full DDL

```sql
CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    first_name      TEXT NOT NULL,
    last_name       TEXT,
    email           TEXT,
    phone           TEXT,
    company         TEXT,
    position        TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'subscriber'
                    CHECK (lifecycle_stage IN ('subscriber', 'lead', 'mql', 'sql', 'opportunity', 'customer', 'churned')),
    source          TEXT DEFAULT 'manual',
    custom_fields   JSONB NOT NULL DEFAULT '{}'::JSONB,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    owner_id        UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_contacts_tenant_id ON contacts (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_workspace_id ON contacts (workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_owner_id ON contacts (owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_lifecycle_stage ON contacts (tenant_id, lifecycle_stage) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_email ON contacts (email) WHERE email IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_contacts_name ON contacts USING GIN (first_name gin_trgm_ops, last_name gin_trgm_ops);
CREATE INDEX idx_contacts_custom_fields ON contacts USING GIN (custom_fields jsonb_path_ops);
CREATE INDEX idx_contacts_tags ON contacts USING GIN (tags);
CREATE INDEX idx_contacts_created_at ON contacts (created_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_contacts_tenant_stage_created ON contacts (tenant_id, lifecycle_stage, created_at)
    WHERE deleted_at IS NULL;

CREATE TRIGGER mdt_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON contacts FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 4.5 `deals` — Full DDL

```sql
CREATE TABLE deals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    workspace_id        UUID NOT NULL REFERENCES workspaces(id),
    name                TEXT NOT NULL,
    value               DECIMAL(12,2) NOT NULL DEFAULT 0,
    currency            TEXT NOT NULL DEFAULT 'USD',
    pipeline_stage_id   UUID NOT NULL REFERENCES pipeline_stages(id),
    contact_id          UUID REFERENCES contacts(id),
    organization_id     UUID REFERENCES organizations(id),
    owner_id            UUID REFERENCES users(id),
    probability         INTEGER NOT NULL DEFAULT 0 CHECK (probability BETWEEN 0 AND 100),
    expected_close_date DATE,
    custom_fields       JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_deals_tenant_id ON deals (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_workspace_id ON deals (workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_pipeline_stage_id ON deals (pipeline_stage_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_contact_id ON deals (contact_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_owner_id ON deals (owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_value ON deals (value) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_expected_close ON deals (expected_close_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_deals_custom_fields ON deals USING GIN (custom_fields jsonb_path_ops);
CREATE INDEX idx_deals_tenant_stage ON deals (tenant_id, pipeline_stage_id) WHERE deleted_at IS NULL;

CREATE TRIGGER mdt_deals_updated_at
    BEFORE UPDATE ON deals
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON deals FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 4.6 `campaigns` — Full DDL

```sql
CREATE TABLE campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    name            TEXT NOT NULL,
    description     TEXT,
    type            TEXT NOT NULL
                    CHECK (type IN ('email', 'sms', 'social', 'landing_page', 'multi_channel', 'drip')),
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'scheduled', 'active', 'paused', 'completed', 'archived')),
    start_date      TIMESTAMPTZ,
    end_date        TIMESTAMPTZ,
    budget          DECIMAL(12,2),
    channel_config  JSONB NOT NULL DEFAULT '{}'::JSONB,
    segments        TEXT[] NOT NULL DEFAULT '{}',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_campaigns_tenant_id ON campaigns (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_workspace_id ON campaigns (workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_status ON campaigns (tenant_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_type ON campaigns (tenant_id, type) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_dates ON campaigns (start_date, end_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_channel_config ON campaigns USING GIN (channel_config jsonb_path_ops);
CREATE INDEX idx_campaigns_created_by ON campaigns (created_by) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_created_at ON campaigns (created_at) WHERE deleted_at IS NULL;

CREATE TRIGGER mdt_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON campaigns FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 4.7 `agents` — Full DDL

```sql
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    name            TEXT NOT NULL,
    role            TEXT NOT NULL
                    CHECK (role IN (
                        'marketing_director', 'seo_specialist', 'content_writer',
                        'analytics_agent', 'customer_success', 'operations'
                    )),
    description     TEXT,
    model_config    JSONB NOT NULL DEFAULT '{}'::JSONB,
    tools           TEXT[] NOT NULL DEFAULT '{}',
    memory_config   JSONB NOT NULL DEFAULT '{}'::JSONB,
    permissions     JSONB NOT NULL DEFAULT '{}'::JSONB,
    system_prompt   TEXT,
    goals           JSONB NOT NULL DEFAULT '[]'::JSONB,
    guardrails      JSONB NOT NULL DEFAULT '{}'::JSONB,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'paused', 'disabled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_agents_tenant_id ON agents (tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_workspace_id ON agents (workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_role ON agents (tenant_id, role) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_status ON agents (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_model_config ON agents USING GIN (model_config jsonb_path_ops);
CREATE INDEX idx_agents_goals ON agents USING GIN (goals jsonb_path_ops);
CREATE INDEX idx_agents_guardrails ON agents USING GIN (guardrails jsonb_path_ops);

CREATE TRIGGER mdt_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION moddatetime(updated_at);

ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON agents FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 4.8 Common DDL Patterns (applied to all other tables)

#### History/Audit Table Pattern

Every entity table gets a corresponding `_history` table:

```sql
-- Generic audit table (one per entity table)
CREATE TABLE <table>_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id   UUID NOT NULL,  -- references the original table's id
    operation   TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_by  UUID,
    row_data    JSONB NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_<table>_history_entity_id ON <table>_history (entity_id, changed_at);
```

#### Full-Text Search Vector Column Pattern

Tables that support full-text search get a generated `tsv` column:

```sql
ALTER TABLE contacts ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '') || ' ' || coalesce(company, '') || ' ' || coalesce(email, ''))
    ) STORED;

CREATE INDEX idx_contacts_search ON contacts USING GIN (search_vector);
```

---

## 5. Migration Strategy

### 5.1 Alembic-Based Migrations

AMC uses **Alembic** for database migration management, with a structured naming convention and multi-environment support.

#### Directory Structure

```
backend/
├── alembic/
│   ├── versions/              # Migration scripts
│   │   ├── 0001_initial_schema.py
│   │   ├── 0002_add_crm_tables.py
│   │   ├── 0003_add_rls_policies.py
│   │   └── ...
│   ├── env.py                 # Alembic environment configuration
│   ├── script.py.mako         # Migration template
│   └── alembic.ini            # Alembic configuration
├── migrations/
│   ├── seed/                  # Seed data scripts
│   │   ├── seed_roles.py
│   │   ├── seed_plans.py
│   │   └── seed_ai_templates.py
│   ├── backfill/              # Data backfill scripts
│   │   └── backfill_search_vectors.py
│   └── checks/                # Pre/post migration safety checks
│       └── check_replication_lag.py
└── ...
```

#### Naming Conventions

| Component | Convention | Example |
|-----------|-----------|---------|
| Migration revision | `{sequence}_{description}` | `0001_initial_schema` |
| Migration message | Present tense, imperative | `Add CRM tables with RLS policies` |
| Branch labels | `module_` prefix | `crm@head`, `marketing@head` |
| Tags | `env:production`, `env:staging` | For environment-specific migrations |

#### Migration Template

```python
"""Add CRM tables with RLS policies

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = ('crm',)
depends_on = ('auth',)

def upgrade():
    op.create_table('contacts',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(), nullable=False),
        sa.Column('first_name', sa.Text(), nullable=False),
        # ... other columns ...
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_contacts_tenants'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name='fk_contacts_workspaces'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='fk_contacts_owner'),
    )
    op.create_index('idx_contacts_tenant_id', 'contacts', ['tenant_id'],
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_contacts_email', 'contacts', ['email'],
                    postgresql_where=sa.text('email IS NOT NULL AND deleted_at IS NULL'))

    # RLS
    op.execute("ALTER TABLE contacts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON contacts FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID)
    """)

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON contacts")
    op.drop_table('contacts')
```

### 5.2 Data Migration Patterns

#### Backfill Scripts

Backfill scripts are standalone Python scripts that run after schema migrations, designed to be idempotent:

```python
"""
backfill_search_vectors.py

Idempotent backfill: populate search_vector column for existing contacts.
"""
import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

BATCH_SIZE = 1000

async def backfill_contact_search_vectors():
    async with async_session_factory() as session:
        while True:
            result = await session.execute(
                text("""
                    UPDATE contacts
                    SET search_vector = to_tsvector('english',
                        coalesce(first_name, '') || ' ' ||
                        coalesce(last_name, '') || ' ' ||
                        coalesce(company, '') || ' ' ||
                        coalesce(email, '')
                    )
                    WHERE search_vector IS NULL
                    AND deleted_at IS NULL
                    LIMIT :batch
                    RETURNING id
                """),
                {"batch": BATCH_SIZE}
            )
            updated = result.rowcount
            await session.commit()
            if updated == 0:
                break
            print(f"Updated {updated} contact search vectors...")

if __name__ == "__main__":
    asyncio.run(backfill_contact_search_vectors())
```

**Backfill patterns:**

| Pattern | Use Case | Approach |
|---------|----------|----------|
| **Batch UPDATE** | Computed columns, denormalized fields | `UPDATE ... LIMIT batch_size` loop |
| **Batch INSERT** | Materializing derived data | `INSERT ... SELECT` with batch limits |
| **Streaming** | Very large tables (100M+ rows) | Server-side cursor, batch process |
| **Parallel** | Independent partitions | Partition-level parallelism via `pg_batch` |
| **Idempotent** | Ensures re-runnable | `ON CONFLICT DO NOTHING` or `WHERE NULL` checks |

#### Seed Data Pattern

```python
"""
seed_roles.py

Idempotent seed: insert system roles.
"""
import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory

SYSTEM_ROLES = [
    {"slug": "superadmin", "name": "Super Admin", "is_system": True, "priority": 100},
    {"slug": "owner", "name": "Workspace Owner", "is_system": True, "priority": 80},
    {"slug": "admin", "name": "Workspace Admin", "is_system": True, "priority": 60},
    {"slug": "member", "name": "Team Member", "is_system": True, "priority": 40},
    {"slug": "viewer", "name": "Read Only", "is_system": True, "priority": 20},
]

async def seed():
    async with async_session_factory() as session:
        for role in SYSTEM_ROLES:
            # Check if exists
            exists = await session.execute(
                select(Role).where(Role.slug == role["slug"], Role.is_system == True)
            )
            if not exists.scalar_one_or_none():
                session.add(Role(**role))
        await session.commit()
```

### 5.3 Zero-Downtime Migration Approaches

AMC uses the **Expand-Contract** pattern for all schema changes that cannot be made in-place without downtime:

#### Expand-Contract Pattern

```
Phase 1 (Expand):     Add new column/table alongside existing
Phase 2 (Migrate):    Backfill data, dual-write both old and new
Phase 3 (Contract):   Remove old column/table, update application code
```

**Example — Renaming a column:**

```mermaid
sequenceDiagram
    participant App as Application (old)
    participant App2 as Application (new)
    participant DB as PostgreSQL

    Note over App,DB: Phase 1: EXPAND
    DB->>DB: ALTER TABLE contacts ADD COLUMN full_name TEXT;
    Note over App: Deploy app v1.1 that writes to both `name` and `full_name`
    App->>DB: INSERT INTO contacts (name, full_name) VALUES (...)
    Note over DB: Phase 2: MIGRATE
    DB->>DB: UPDATE contacts SET full_name = name WHERE full_name IS NULL;
    Note over App: Deploy app v1.2 that reads from `full_name` only
    Note over App,DB: Phase 3: CONTRACT
    DB->>DB: ALTER TABLE contacts DROP COLUMN name;
    App2->>DB: INSERT INTO contacts (full_name) VALUES (...)
```

#### Common Zero-Downtime Patterns

| Change Type | Zero-Downtime Approach |
|------------|------------------------|
| **Add column** | Safe: `ALTER TABLE ... ADD COLUMN ... DEFAULT NULL` — no table rewrite |
| **Add column with default** | Add as nullable, backfill, then `ALTER COLUMN SET NOT NULL` + `SET DEFAULT` |
| **Drop column** | Mark as unused in app, remove reads, then `ALTER TABLE ... DROP COLUMN` |
| **Rename column** | Expand-contract via dual-write |
| **Add index** | `CREATE INDEX CONCURRENTLY` (avoids table lock) |
| **Drop index** | `DROP INDEX CONCURRENTLY` |
| **Add FK constraint** | `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID` then `VALIDATE CONSTRAINT` |
| **Change column type** | Add new column, backfill, dual-write, drop old column |
| **Partition existing table** | Create partitioned table, attach old table as partition, backfill |
| **Add RLS policy** | Safe — applied atomically, no lock |

### 5.4 Migration Safety Checks

Every migration must pass a safety review:

```python
"""check_replication_lag.py — Pre-migration safety check"""
import asyncio
from app.db.session import async_session_factory

async def check_replication_lag(max_lag_seconds=5) -> bool:
    """Check that replication lag is below threshold before migration."""
    async with async_session_factory() as session:
        result = await session.execute("""
            SELECT GREATEST(
                EXTRACT(EPOCH FROM NOW() - pg_last_xact_replay_timestamp()),
                0
            ) AS lag_seconds
        """)
        lag = result.scalar()
        if lag > max_lag_seconds:
            print(f"WARNING: Replication lag is {lag}s (threshold: {max_lag_seconds}s)")
            return False
        print(f"Replication lag: {lag}s — OK")
        return True

async def check_active_connections() -> bool:
    """Warn if there are active connections that might be affected."""
    async with async_session_factory() as session:
        result = await session.execute("""
            SELECT count(*) FROM pg_stat_activity
            WHERE state = 'active'
            AND query NOT LIKE '%pg_stat_activity%'
        """)
        count = result.scalar()
        print(f"Active connections: {count}")
        return count < 50  # threshold
```

**Safety checklist (pre-merge):**

- [ ] Migration is reversible (has `downgrade()`)
- [ ] No `ALTER TABLE ... DROP COLUMN` without expand-contract cycle
- [ ] All indexes on large tables use `CONCURRENTLY`
- [ ] FK constraints added with `NOT VALID` + `VALIDATE CONSTRAINT`
- [ ] Migration has been tested on a staging copy of production data
- [ ] Estimated execution time < 5 minutes (or partitioned approach needed)
- [ ] Replication lag < 5 seconds
- [ ] Backfill script is idempotent
- [ ] RLS policies are included for new tenant-scoped tables

---

## 6. Query Patterns & Optimization

### 6.1 Common Query Patterns by Module

#### CRM Module — High-Frequency Queries

```sql
-- 1. Dashboard: Contacts by lifecycle stage (counts per tenant)
SELECT lifecycle_stage, count(*) as count
FROM contacts
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND deleted_at IS NULL
GROUP BY lifecycle_stage;

-- 2. Pipeline: Deals in a pipeline stage (with contact info)
SELECT d.*, c.first_name, c.last_name, c.email, c.company
FROM deals d
LEFT JOIN contacts c ON c.id = d.contact_id
WHERE d.tenant_id = current_setting('app.current_tenant_id')::UUID
  AND d.pipeline_stage_id = :stage_id
  AND d.deleted_at IS NULL
ORDER BY d.value DESC;

-- 3. Contact search (full-text)
SELECT id, first_name, last_name, email, company, ts_rank(search_vector, query) AS rank
FROM contacts, plainto_tsquery('english', :search_term) AS query
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND search_vector @@ query
  AND deleted_at IS NULL
ORDER BY rank DESC
LIMIT 20;

-- 4. Recent activities for a contact
SELECT * FROM activities
WHERE contact_id = :contact_id
  AND tenant_id = current_setting('app.current_tenant_id')::UUID
ORDER BY activity_date DESC
LIMIT 50;

-- 5. Deal pipeline value summary
SELECT ps.name AS stage_name, count(*) AS deal_count,
       sum(d.value) AS total_value, avg(d.value) AS avg_value
FROM deals d
JOIN pipeline_stages ps ON ps.id = d.pipeline_stage_id
WHERE d.tenant_id = current_setting('app.current_tenant_id')::UUID
  AND d.deleted_at IS NULL
GROUP BY ps.id, ps.name, ps.order
ORDER BY ps.order;
```

**Covering indexes for CRM queries:**
```sql
-- Covering index for pipeline summary
CREATE INDEX idx_deals_tenant_stage_value ON deals (tenant_id, pipeline_stage_id, value)
    WHERE deleted_at IS NULL
    INCLUDE (name, expected_close_date);

-- Covering index for lifecycle counts
CREATE INDEX idx_contacts_tenant_stage ON contacts (tenant_id, lifecycle_stage)
    WHERE deleted_at IS NULL;
```

#### Marketing Module — High-Frequency Queries

```sql
-- 1. Active campaigns for workspace dashboard
SELECT id, name, type, status, start_date, end_date, budget
FROM campaigns
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND workspace_id = :workspace_id
  AND status IN ('active', 'scheduled')
  AND deleted_at IS NULL
ORDER BY start_date;

-- 2. Campaign performance metrics
SELECT c.id, c.name,
       (SELECT count(*) FROM campaign_emails ce
        WHERE ce.campaign_id = c.id) AS total_sent,
       (SELECT count(*) FROM campaign_emails ce
        WHERE ce.campaign_id = c.id AND ce.opened_at IS NOT NULL) AS total_opened,
       (SELECT count(*) FROM campaign_emails ce
        WHERE ce.campaign_id = c.id AND ce.clicked_at IS NOT NULL) AS total_clicked
FROM campaigns c
WHERE c.tenant_id = current_setting('app.current_tenant_id')::UUID
  AND c.deleted_at IS NULL;

-- 3. Segment membership (contacts in a segment)
SELECT c.* FROM contacts c
JOIN contact_segments cs ON cs.contact_id = c.id
WHERE cs.segment_id = :segment_id
  AND cs.removed_at IS NULL
  AND c.deleted_at IS NULL;
```

#### Analytics Module — Materialized View Query

```sql
-- Daily campaign metrics materialized view
CREATE MATERIALIZED VIEW mv_campaign_daily_metrics AS
SELECT
    c.tenant_id,
    c.workspace_id,
    c.id AS campaign_id,
    c.name AS campaign_name,
    date_trunc('day', ce.sent_at) AS metric_date,
    count(*) AS sent_count,
    count(ce.opened_at) AS open_count,
    count(ce.clicked_at) AS click_count,
    count(DISTINCT ce.contact_id) AS unique_contacts
FROM campaigns c
JOIN campaign_emails ce ON ce.campaign_id = c.id
WHERE c.deleted_at IS NULL
  AND ce.sent_at >= NOW() - INTERVAL '90 days'
GROUP BY c.tenant_id, c.workspace_id, c.id, c.name, date_trunc('day', ce.sent_at)
WITH DATA;

CREATE UNIQUE INDEX idx_mv_campaign_daily ON mv_campaign_daily_metrics
    (tenant_id, campaign_id, metric_date);
CREATE INDEX idx_mv_campaign_daily_tenant ON mv_campaign_daily_metrics (tenant_id);
```

### 6.2 Index Strategy

#### Index Classification

| Index Type | Use Case | Examples | Cardinality |
|-----------|----------|----------|-------------|
| **B-tree (primary)** | PK, FK lookups, range queries, sorting | All `id`, `tenant_id`, `created_at` columns | All |
| **B-tree (composite)** | Multi-column filter + sort | `(tenant_id, status, created_at)` | High |
| **B-tree (partial)** | Filter on subset (e.g., non-deleted) | `WHERE deleted_at IS NULL` | Varies |
| **B-tree (covering)** | Index-only scans | `INCLUDE (additional columns)` | High |
| **GIN** | JSONB queries, full-text search | JSONB columns, `search_vector` | High |
| **GIN (trgm)** | Fuzzy text search | `first_name`, `last_name`, `display_name` | Medium |
| **GiST** | Exclusion constraints, range types | Scheduling conflicts, geo | Low |
| **BRIN** | Large time-series tables | `analytics_events(event_time)` | Very high |
| **Hash** | Equality lookups on large values | `token_hash`, `key_hash` | Medium |

#### Composite Index Design Principles

1. **Leading column = tenant_id** — All tenant-scoped queries filter on `tenant_id` first
2. **Equality columns first** — Columns with `=` filters before range/order columns
3. **Selective columns first** — High cardinality columns before low cardinality
4. **Sort direction** — Match `ORDER BY` direction for index-only ordering

```sql
-- Good: tenant_id (equality), status (equality), created_at (range/order)
CREATE INDEX idx_campaigns_tenant_status_created ON campaigns
    (tenant_id, status, created_at) WHERE deleted_at IS NULL;

-- Bad: status comes first (low cardinality, not selective)
-- Bad: created_at before more selective columns
CREATE INDEX idx_campaigns_bad ON campaigns
    (status, created_at) WHERE deleted_at IS NULL;
```

#### Unused Index Detection

```sql
-- Find potentially unused indexes (run weekly)
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY tablename, indexname;
```

### 6.3 Partitioning Strategy

#### By Tenant (List Partitioning) — For large reference tables

```sql
-- Example: Partition contacts by tenant_id (for very large tenants)
-- NOTE: Only used when a single tenant exceeds ~10M rows
CREATE TABLE contacts_partitioned (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    -- ... other columns ...
    PRIMARY KEY (id, tenant_id)
) PARTITION BY LIST (tenant_id);

-- Each tenant gets its own partition (managed dynamically)
CREATE TABLE contacts_tenant_abc PARTITION OF contacts_partitioned
    FOR VALUES IN ('tenant-abc-123');
CREATE TABLE contacts_tenant_def PARTITION OF contacts_partitioned
    FOR VALUES IN ('tenant-def-456');
```

#### By Date (Range Partitioning) — For time-series tables

```sql
-- Partitioned analytics events (daily partitions)
CREATE TABLE analytics_events (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    event_name TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- ... other columns ...
    PRIMARY KEY (id, event_time)
) PARTITION BY RANGE (event_time);

-- Create partitions via pg_partman or cron job
SELECT partman.create_parent(
    p_parent_table := 'public.analytics_events',
    p_control := 'event_time',
    p_type := 'native',
    p_interval := '1 day',
    p_premake := 7
);

-- Partitions for campaign_events (monthly, 24-month retention)
CREATE TABLE campaign_events (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    campaign_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Monthly partitions created via pg_partman
SELECT partman.create_parent(
    p_parent_table := 'public.campaign_events',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := '1 month',
    p_premake := 3,
    p_retention := '24 months',
    p_retention_keep_table := false  -- Automatically drop old partitions
);
```

**Partitioning strategy by table:**

| Table | Partition Key | Type | Interval | Retention |
|-------|--------------|------|----------|-----------|
| `analytics_events` | `event_time` | Range (daily) | 1 day | 90 days (raw) |
| `campaign_events` | `created_at` | Range (monthly) | 1 month | 24 months |
| `email_sends` | `sent_at` | Range (monthly) | 1 month | 12 months |
| `contact_activities` | `created_at` | Range (monthly) | 1 month | 18 months |
| `execution_logs` | `created_at` | Range (monthly) | 1 month | 6 months |
| `notification_logs` | `created_at` | Range (monthly) | 1 month | 6 months |

### 6.4 Connection Pooling Configuration

#### PgBouncer Configuration

```ini
[databases]
amc = host=pg-primary port=5432 dbname=amc pool_size=25
amc_readonly = host=pg-replica port=5432 dbname=amc pool_size=50

[pgbouncer]
pool_mode = transaction
default_pool_size = 50
max_client_conn = 500
max_db_connections = 100
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
server_idle_timeout = 300
client_idle_timeout = 600
query_timeout = 30
stats_period = 60

; Connection limits per tenant (via application-level enforcement)
;
; Application-level pool configuration:
; - API Gateway: 25 connections via PgBouncer
; - Service Layer: 25 connections via PgBouncer
; - Worker Pool: 10 connections via PgBouncer
; - AI Service: 5 connections via PgBouncer
; - n8n: 15 connections via PgBouncer
; Total: 80 connections (within PgBouncer's 100 max)
```

#### Application-Level Pool (SQLAlchemy Async)

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Pool configuration
ENGINE = create_async_engine(
    "postgresql+asyncpg://user:pass@pgbouncer:6432/amc",
    pool_size=10,           # Connection pool size per process
    max_overflow=5,          # Temporary overflow connections
    pool_pre_ping=True,      # Verify connections before use
    pool_recycle=3600,       # Recycle connections every hour
    pool_use_lifo=True,      # LIFO for better cache locality
    connect_args={
        "server_settings": {
            "application_name": "amc-api-service",
            "timezone": "UTC",
        }
    }
)

AsyncSessionFactory = async_sessionmaker(ENGINE, expire_on_commit=False)
```

#### Connection Pool Metrics (monitored via Prometheus)

```python
# Prometheus gauges for pool metrics
pool_size = Gauge('db_pool_size', 'Database pool size', ['pool'])
pool_available = Gauge('db_pool_available', 'Available connections', ['pool'])
pool_overflow = Gauge('db_pool_overflow', 'Overflow connections', ['pool'])
pool_wait_ms = Histogram('db_pool_wait_ms', 'Connection wait time (ms)', buckets=[1, 5, 10, 25, 50, 100, 250, 500])
```

### 6.5 Materialized View Candidates

| Materialized View | Refresh Strategy | Use Case | Est. Rows |
|-------------------|-----------------|----------|-----------|
| `mv_campaign_daily_metrics` | Incremental (every 5 min) | Campaign performance dashboards | 10K–1M |
| `mv_contact_lifecycle_counts` | Full refresh (hourly) | CRM dashboard lifecycle chart | 100–10K |
| `mv_pipeline_value_summary` | Full refresh (every 15 min) | Pipeline value by stage/category | 100–5K |
| `mv_workspace_usage_metrics` | Incremental (hourly) | Billing and usage tracking | 1K–50K |
| `mv_keyword_rankings_latest` | Full refresh (daily) | Latest keyword positions | 10K–500K |
| `mv_social_account_summary` | Full refresh (hourly) | Social media account-level metrics | 1K–50K |
| `mv_agent_performance` | Incremental (every 5 min) | AI agent execution metrics | 1K–100K |
| `mv_tenant_monthly_revenue` | Full refresh (daily) | Revenue reporting | 100–50K |

**Refresh pattern with concurrent refresh to avoid blocking reads:**

```sql
-- Atomic refresh (blocks readers briefly)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_campaign_daily_metrics;
```

### 6.6 Full-Text Search Configuration

#### Tsvector Setup

```sql
-- Custom text search configuration for marketing content
CREATE TEXT SEARCH CONFIGURATION amc_english (COPY = pg_catalog.english);
ALTER TEXT SEARCH CONFIGURATION amc_english
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart
    WITH english_stem;

-- Add search_vector column to searchable tables
ALTER TABLE contacts ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (
        setweight(to_tsvector('amc_english', coalesce(first_name, '')), 'A') ||
        setweight(to_tsvector('amc_english', coalesce(last_name, '')), 'A') ||
        setweight(to_tsvector('amc_english', coalesce(company, '')), 'B') ||
        setweight(to_tsvector('amc_english', coalesce(email, '')), 'B') ||
        setweight(to_tsvector('amc_english', coalesce(position, '')), 'C')
    ) STORED;

CREATE INDEX idx_contacts_search ON contacts USING GIN (search_vector);

-- Knowledge base full-text search
ALTER TABLE kb_documents ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (
        setweight(to_tsvector('amc_english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('amc_english', coalesce(content_plain, '')), 'B')
    ) STORED;

CREATE INDEX idx_kb_documents_search ON kb_documents USING GIN (search_vector);
```

#### Search Query Patterns

```sql
-- Simple search with ranking
SELECT id, first_name, last_name, email, company,
       ts_rank(search_vector, query) AS rank,
       ts_headline('amc_english', coalesce(first_name, '') || ' ' || coalesce(last_name, ''),
                   query, 'StartSel=<mark>,StopSel=</mark>') AS headline
FROM contacts, plainto_tsquery('amc_english', :search_term) AS query
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND search_vector @@ query
  AND deleted_at IS NULL
ORDER BY rank DESC
LIMIT 20;

-- Autocomplete (prefix search) via trigram
SELECT id, first_name, last_name, email
FROM contacts
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND deleted_at IS NULL
  AND (first_name ILIKE :prefix || '%' OR last_name ILIKE :prefix || '%')
ORDER BY created_at DESC
LIMIT 10;

-- Trigram-based fuzzy search
SELECT id, first_name, last_name, email,
       similarity(first_name, :search_term) AS sim
FROM contacts
WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
  AND deleted_at IS NULL
  AND (first_name % :search_term OR last_name % :search_term)
ORDER BY sim DESC
LIMIT 10;
```

---

## 7. Data Archival & Purging

### 7.1 Archival Strategy

#### Tier-Based Archival

| Data Category | Active Table | Archive Table | Trigger Condition | Archival Method |
|--------------|-------------|---------------|-------------------|-----------------|
| Old campaigns | `campaigns` | `campaigns_archive` | `status = 'completed'` AND `end_date < NOW() - 6 months` | Partition detach + move |
| Analytics events | `analytics_events` | `analytics_events_archive` | `event_time < NOW() - 90 days` | Partition detach |
| Email sends | `campaign_emails` | `campaign_emails_archive` | `sent_at < NOW() - 12 months` | Batch DELETE (after archive) |
| Execution logs | `execution_logs` | `execution_logs_archive` | `created_at < NOW() - 6 months` | Batch INSERT INTO archive |
| Notification logs | `notification_logs` | `notification_logs_archive` | `created_at < NOW() - 6 months` | Partition detach |
| Social analytics | `social_analytics` | `social_analytics_archive` | `analytics_date < NOW() - 12 months` | Batch move |
| Agent executions | `agent_executions` | `agent_executions_archive` | `started_at < NOW() - 3 months` | Batch move |

#### Partition-Based Archival (for partitioned tables)

```sql
-- For monthly-partitioned tables, archival = detach old partition
-- Then optionally move to archive schema or cheaper storage

-- Step 1: Detach old partition
ALTER TABLE campaign_events DETACH PARTITION campaign_events_2025_01;

-- Step 2: Move to archive schema
ALTER TABLE campaign_events_2025_01 SET SCHEMA archive;

-- Step 3: Optionally compress (pg_compress or columnar storage)
-- Or move to a cheaper PostgreSQL instance / S3 via pg_dump

-- Automated via pg_partman retention policy
SELECT partman.partition_data_proc(
    p_parent_table := 'public.campaign_events',
    p_interval := '1 month',
    p_batch := 1000
);
```

#### Archival Worker (Background Job)

```python
"""
archival_worker.py — Background worker that runs daily.
"""
import asyncio
from datetime import datetime, timedelta
from app.db.session import async_session_factory

ARCHIVE_THRESHOLDS = {
    "analytics_events": {"days": 90, "batch": 10000},
    "campaign_emails": {"days": 365, "batch": 5000},
    "execution_logs": {"days": 180, "batch": 5000},
    "notification_logs": {"days": 180, "batch": 5000},
}

async def archive_table(table: str, threshold_days: int, batch_size: int):
    """Archive old records from a table."""
    cutoff = datetime.utcnow() - timedelta(days=threshold_days)
    table_config = {
        "analytics_events": {"date_col": "event_time", "order_col": "event_time"},
        "campaign_emails": {"date_col": "sent_at", "order_col": "sent_at"},
        "execution_logs": {"date_col": "created_at", "order_col": "created_at"},
        "notification_logs": {"date_col": "created_at", "order_col": "created_at"},
    }
    cfg = table_config.get(table)
    if not cfg:
        return

    async with async_session_factory() as session:
        while True:
            # INSERT into archive table
            result = await session.execute(f"""
                WITH batch AS (
                    SELECT * FROM {table}
                    WHERE {cfg['date_col']} < :cutoff
                    ORDER BY {cfg['order_col']}
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED
                )
                INSERT INTO {table}_archive SELECT * FROM batch
                RETURNING id
            """, {"cutoff": cutoff, "batch_size": batch_size})

            archived = result.rowcount
            if archived == 0:
                break

            # DELETE from main table
            await session.execute(f"""
                DELETE FROM {table}
                WHERE id = ANY(:ids)
            """, {"ids": [row[0] for row in result.fetchall()]})

            await session.commit()
            print(f"Archived {archived} rows from {table}...")
```

### 7.2 GDPR Deletion Workflows

#### Right to Erasure (Art. 17 GDPR)

```sql
-- Step 1: Anonymize the user's personal data
-- (Keep the record for referential integrity, but remove PII)
UPDATE users
SET
    email = 'deleted-' || id || '@anonymized.invalid',
    email_verified = FALSE,
    password_hash = 'DELETED',
    display_name = 'Deleted User',
    avatar_url = NULL,
    metadata = jsonb_build_object('deleted_at', NOW(), 'previous_tier', metadata->>'tier'),
    is_active = FALSE,
    deleted_at = NOW()
WHERE id = :user_id;

-- Step 2: Remove from all contact tables (anonymize)
UPDATE contacts
SET
    email = NULL,
    phone = NULL,
    first_name = 'Deleted',
    last_name = 'Contact',
    custom_fields = '{}'::JSONB,
    deleted_at = NOW()
WHERE email = :original_email
   OR owner_id = :user_id;

-- Step 3: Anonymize personal data in all related tables
UPDATE oauth_accounts SET access_token = 'DELETED', refresh_token = 'DELETED'
WHERE user_id = :user_id;

UPDATE api_keys SET key_hash = 'DELETED', revoked_at = NOW()
WHERE user_id = :user_id;

-- Step 4: Remove from mailing lists / segments
DELETE FROM contact_segments
WHERE contact_id IN (SELECT id FROM contacts WHERE owner_id = :user_id);
```

#### GDPR Deletion Service

```python
"""
gdpr_service.py — Orchestrates GDPR right to erasure.
"""
import asyncio
from app.db.session import async_session_factory

GDPR_TABLES = [
    "users", "oauth_accounts", "sessions", "api_keys", "mfa_devices",
    "contacts", "leads", "notes", "activities",
    "notification_preferences", "social_conversations",
]

async def execute_gdpr_erasure(user_id: str, tenant_id: str):
    """
    Execute full GDPR right to erasure for a user.
    This is a soft-delete + anonymization, not a hard DELETE,
    to preserve referential integrity in analytics and audit logs.
    """
    async with async_session_factory() as session:
        async with session.begin():
            # 1. Anonymize user
            await session.execute("""
                UPDATE users SET
                    email = 'gdpr-' || id || '@anonymized.invalid',
                    email_verified = FALSE,
                    password_hash = 'GDPR_ERASED',
                    display_name = 'Deleted User',
                    avatar_url = NULL,
                    metadata = jsonb_build_object('gdpr_erased_at', NOW()),
                    is_active = FALSE,
                    deleted_at = NOW()
                WHERE id = :user_id AND tenant_id = :tenant_id
            """, {"user_id": user_id, "tenant_id": tenant_id})

            # 2. Expire all sessions
            await session.execute("""
                UPDATE sessions SET revoked_at = NOW()
                WHERE user_id = :user_id
            """, {"user_id": user_id})

            # 3. Anonymize OAuth tokens
            await session.execute("""
                UPDATE oauth_accounts SET
                    access_token = 'GDPR_ERASED',
                    refresh_token = 'GDPR_ERASED'
                WHERE user_id = :user_id
            """, {"user_id": user_id})

            # 4. Revoke API keys
            await session.execute("""
                UPDATE api_keys SET
                    key_hash = 'GDPR_ERASED',
                    revoked_at = NOW()
                WHERE user_id = :user_id
            """, {"user_id": user_id})

            # 5. Anonymize contacts owned by this user
            await session.execute("""
                UPDATE contacts SET
                    email = NULL,
                    phone = NULL,
                    first_name = 'GDPR',
                    last_name = 'Erased',
                    custom_fields = '{}'::JSONB,
                    owner_id = NULL,
                    deleted_at = NOW()
                WHERE owner_id = :user_id AND tenant_id = :tenant_id
            """, {"user_id": user_id, "tenant_id": tenant_id})

            # 6. Reassign deals and leads
            await session.execute("""
                UPDATE deals SET owner_id = NULL
                WHERE owner_id = :user_id AND tenant_id = :tenant_id
            """, {"user_id": user_id, "tenant_id": tenant_id})

            await session.execute("""
                UPDATE leads SET owner_id = NULL
                WHERE owner_id = :user_id AND tenant_id = :tenant_id
            """, {"user_id": user_id, "tenant_id": tenant_id})

            # 7. Log GDPR deletion
            await session.execute("""
                INSERT INTO gdpr_deletion_log (user_id, tenant_id, requested_by, deleted_at)
                VALUES (:user_id, :tenant_id, :requested_by, NOW())
            """, {"user_id": user_id, "tenant_id": tenant_id, "requested_by": "SYSTEM"})

        # Log completion
        print(f"GDPR erasure completed for user {user_id} in tenant {tenant_id}")
```

### 7.3 Data Retention Policies (Per Tier)

| Data Category | Free Tier | Starter | Professional | Enterprise |
|--------------|-----------|---------|--------------|------------|
| **Analytics events (raw)** | 30 days | 90 days | 180 days | 365 days |
| **Campaign analytics** | 6 months | 12 months | 24 months | 36 months |
| **Email send logs** | 3 months | 6 months | 12 months | 24 months |
| **Social analytics** | 3 months | 6 months | 12 months | 24 months |
| **Execution logs** | 7 days | 30 days | 90 days | 180 days |
| **Notification logs** | 30 days | 60 days | 90 days | 180 days |
| **Audit logs** | 30 days | 90 days | 180 days | 365 days |
| **Deleted contacts** | 30 days | 60 days | 90 days | 180 days |
| **Session data** | 24 hours | 7 days | 14 days | 30 days |
| **Conversation history (AI)** | 30 days | 90 days | 180 days | 365 days |

**Retention enforcement via pg_cron:**

```sql
-- Schedule daily purge job via pg_cron
SELECT cron.schedule(
    'purge-analytics-events',       -- job name
    '0 3 * * *',                    -- daily at 3 AM
    $$DELETE FROM analytics_events
      WHERE event_time < NOW() - INTERVAL '90 days'
      AND tenant_id IN (
          SELECT id FROM tenants WHERE tier IN ('free', 'starter')
      )$$
);

SELECT cron.schedule(
    'purge-execution-logs',
    '30 3 * * *',                   -- daily at 3:30 AM
    $$DELETE FROM execution_logs el
      USING workflow_executions we
      WHERE el.execution_id = we.id
      AND we.created_at < NOW() - INTERVAL '30 days'
      AND we.tenant_id IN (
          SELECT id FROM tenants WHERE tier = 'free'
      )$$
);
```

---

## 8. Appendix: JSONB Schemas

### 8.1 `settings` JSONB Schema

#### Tenant Settings (`tenants.settings`)

```json
{
  "type": "object",
  "properties": {
    "branding": {
      "type": "object",
      "properties": {
        "primary_color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "logo_url": { "type": "string", "format": "uri" },
        "favicon_url": { "type": "string", "format": "uri" }
      }
    },
    "security": {
      "type": "object",
      "properties": {
        "password_policy": {
          "type": "object",
          "properties": {
            "min_length": { "type": "integer", "minimum": 8, "default": 12 },
            "require_special_chars": { "type": "boolean", "default": true },
            "require_numbers": { "type": "boolean", "default": true },
            "require_uppercase": { "type": "boolean", "default": true },
            "max_age_days": { "type": "integer", "default": 90 }
          }
        },
        "mfa_required": { "type": "boolean", "default": false },
        "session_timeout_minutes": { "type": "integer", "default": 480 },
        "allowed_ip_ranges": {
          "type": "array",
          "items": { "type": "string", "format": "cidr" }
        }
      }
    },
    "sso": {
      "type": "object",
      "properties": {
        "saml_enabled": { "type": "boolean" },
        "oidc_enabled": { "type": "boolean" },
        "providers": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "provider": { "type": "string", "enum": ["google", "microsoft", "okta", "custom"] },
              "client_id": { "type": "string" },
              "issuer_url": { "type": "string", "format": "uri" }
            }
          }
        }
      }
    },
    "notifications": {
      "type": "object",
      "properties": {
        "default_email": { "type": "string", "format": "email" },
        "digest_frequency": { "type": "string", "enum": ["instant", "daily", "weekly", "never"], "default": "instant" }
      }
    },
    "limits": {
      "type": "object",
      "properties": {
        "max_contacts": { "type": "integer" },
        "max_campaigns_per_month": { "type": "integer" },
        "max_api_calls_per_hour": { "type": "integer" },
        "max_ai_generations_per_day": { "type": "integer" },
        "max_storage_mb": { "type": "integer" }
      }
    }
  }
}
```

#### Workspace Settings (`workspaces.settings`)

```json
{
  "type": "object",
  "properties": {
    "timezone": { "type": "string", "default": "UTC" },
    "locale": { "type": "string", "default": "en-US" },
    "currency": { "type": "string", "default": "USD" },
    "date_format": { "type": "string", "enum": ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"], "default": "YYYY-MM-DD" },
    "week_starts_on": { "type": "string", "enum": ["monday", "sunday"], "default": "monday" },
    "business_hours": {
      "type": "object",
      "properties": {
        "timezone": { "type": "string" },
        "monday":    { "$ref": "#/definitions/day_hours" },
        "tuesday":   { "$ref": "#/definitions/day_hours" },
        "wednesday": { "$ref": "#/definitions/day_hours" },
        "thursday":  { "$ref": "#/definitions/day_hours" },
        "friday":    { "$ref": "#/definitions/day_hours" },
        "saturday":  { "$ref": "#/definitions/day_hours" },
        "sunday":    { "$ref": "#/definitions/day_hours" }
      }
    },
    "email_footer": {
      "type": "object",
      "properties": {
        "company_name": { "type": "string" },
        "address": { "type": "string" },
        "unsubscribe_link": { "type": "string", "format": "uri" },
        "social_links": { "type": "array", "items": { "type": "string", "format": "uri" } }
      }
    },
    "pipeline_settings": {
      "type": "object",
      "properties": {
        "default_pipeline_id": { "type": "string", "format": "uuid" },
        "auto_assign_probability": { "type": "boolean", "default": false }
      }
    }
  },
  "definitions": {
    "day_hours": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "start": { "type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$" },
        "end": { "type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$" }
      }
    }
  }
}
```

#### Pipeline Settings (`pipelines.settings`)

```json
{
  "type": "object",
  "properties": {
    "win_reason_required": { "type": "boolean", "default": false },
    "loss_reason_required": { "type": "boolean", "default": false },
    "auto_advance": { "type": "boolean", "default": false },
    "expected_close_required": { "type": "boolean", "default": false },
    "probability_type": { "type": "string", "enum": ["manual", "stage_based", "ml_predicted"], "default": "stage_based" },
    "stages_config": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "stage_id": { "type": "string", "format": "uuid" },
          "mandatory_fields": { "type": "array", "items": { "type": "string" } },
          "auto_move_on_fields_complete": { "type": "boolean", "default": false }
        }
      }
    }
  }
}
```

#### Funnel Settings (`funnels.settings`)

```json
{
  "type": "object",
  "properties": {
    "entry_condition": {
      "type": "object",
      "properties": {
        "trigger_type": { "type": "string", "enum": ["form_submit", "tag_added", "lifecycle_change", "deal_stage_change", "custom_event"] },
        "trigger_config": { "type": "object" }
      }
    },
    "exit_condition": {
      "type": "object",
      "properties": {
        "type": { "type": "string", "enum": ["stage_completed", "unsubscribed", "converted", "timeout"] },
        "timeout_days": { "type": "integer" }
      }
    },
    "goal_tracking": {
      "type": "object",
      "properties": {
        "conversion_goal": { "type": "string" },
        "track_attribution": { "type": "boolean", "default": true }
      }
    }
  }
}
```

### 8.2 `custom_fields` JSONB Schema

The `custom_fields` column on `contacts`, `organizations`, `deals`, and `leads` uses the same schema pattern.

```json
{
  "type": "object",
  "description": "User-defined custom fields for contacts, organizations, deals, and leads",
  "additionalProperties": {
    "type": "object",
    "properties": {
      "value": {
        "description": "The actual field value",
        "oneOf": [
          { "type": "string" },
          { "type": "number" },
          { "type": "boolean" },
          { "type": "array", "items": { "type": "string" } },
          { "type": "object" },
          { "type": "null" }
        ]
      },
      "field_type": {
        "type": "string",
        "enum": ["text", "textarea", "number", "date", "boolean", "select", "multi_select", "url", "email", "phone"]
      },
      "field_id": { "type": "string", "description": "Reference to custom field definition" },
      "updated_at": { "type": "string", "format": "date-time" }
    },
    "required": ["value", "field_type"]
  },
  "example": {
    "industry": { "value": "Technology", "field_type": "select", "field_id": "cf_001" },
    "annual_revenue": { "value": 5000000, "field_type": "number", "field_id": "cf_002" },
    "referral_source": { "value": "LinkedIn", "field_type": "text", "field_id": "cf_003" },
    "is_vip": { "value": true, "field_type": "boolean", "field_id": "cf_004" },
    "service_interests": { "value": ["SEO", "PPC"], "field_type": "multi_select", "field_id": "cf_005" }
  }
}
```

### 8.3 `branding` JSONB Schema

```json
{
  "type": "object",
  "description": "Workspace branding configuration",
  "properties": {
    "logo": {
      "type": "object",
      "properties": {
        "url": { "type": "string", "format": "uri" },
        "dark_mode_url": { "type": "string", "format": "uri" },
        "favicon_url": { "type": "string", "format": "uri" },
        "alt_text": { "type": "string" }
      }
    },
    "colors": {
      "type": "object",
      "properties": {
        "primary": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "secondary": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "accent": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "background": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "text_primary": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "text_secondary": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }
      }
    },
    "typography": {
      "type": "object",
      "properties": {
        "heading_font": { "type": "string", "default": "Inter" },
        "body_font": { "type": "string", "default": "Inter" },
        "base_font_size": { "type": "string", "default": "16px" }
      }
    },
    "email": {
      "type": "object",
      "properties": {
        "header_logo_url": { "type": "string" },
        "header_bg_color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "footer_text": { "type": "string" },
        "footer_unsubscribe": { "type": "boolean", "default": true },
        "company_address": { "type": "string" }
      }
    },
    "domain": {
      "type": "object",
      "properties": {
        "custom_domain": { "type": "string", "format": "hostname" },
        "ssl_status": { "type": "string", "enum": ["pending", "active", "failed"] },
        "landing_page_domain": { "type": "string", "format": "hostname" }
      }
    },
    "custom_css": {
      "type": "string",
      "description": "Custom CSS overrides for the workspace portal"
    }
  }
}
```

### 8.4 `metadata` JSONB Schema

The `metadata` column appears on `users`, `tenants`, `subscription_plans`, and several other tables. It is designed as a flexible container for future extensibility.

```json
{
  "type": "object",
  "description": "Flexible metadata container for extensibility",
  "properties": {
    "created_by_source": { "type": "string", "description": "How the record was created (import, api, manual, signup)" },
    "import_batch_id": { "type": "string", "format": "uuid", "description": "Reference to import batch if created via import" },
    "external_ids": {
      "type": "object",
      "description": "Mapping of external system IDs",
      "additionalProperties": { "type": "string" },
      "example": { "hubspot_contact_id": "12345", "salesforce_id": "001xx000003E7kz" }
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Additional tags beyond the dedicated tags column"
    },
    "internal_notes": {
      "type": "string",
      "description": "Internal notes (not shown to end users)"
    },
    "onboarding": {
      "type": "object",
      "properties": {
        "step": { "type": "integer" },
        "completed": { "type": "array", "items": { "type": "string" } },
        "skipped": { "type": "array", "items": { "type": "string" } }
      }
    },
    "feature_flags": {
      "type": "object",
      "description": "Per-entity feature flag overrides",
      "additionalProperties": { "type": "boolean" }
    },
    "custom_tracking": {
      "type": "object",
      "description": "Custom UTM or tracking parameters",
      "properties": {
        "utm_source": { "type": "string" },
        "utm_medium": { "type": "string" },
        "utm_campaign": { "type": "string" },
        "utm_term": { "type": "string" },
        "utm_content": { "type": "string" }
      }
    }
  },
  "additionalProperties": false
}
```

### 8.5 `model_config` JSONB Schema (AI Agents)

```json
{
  "type": "object",
  "properties": {
    "provider": { "type": "string", "enum": ["nim", "openai", "anthropic", "custom"], "default": "nim" },
    "model": { "type": "string", "default": "mixtral-8x22b" },
    "temperature": { "type": "number", "minimum": 0, "maximum": 2, "default": 0.7 },
    "max_tokens": { "type": "integer", "minimum": 256, "maximum": 32768, "default": 4096 },
    "top_p": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.95 },
    "frequency_penalty": { "type": "number", "minimum": -2, "maximum": 2, "default": 0 },
    "presence_penalty": { "type": "number", "minimum": -2, "maximum": 2, "default": 0 },
    "stop_sequences": { "type": "array", "items": { "type": "string" } },
    "response_format": { "type": "string", "enum": ["text", "json_object", "structured"], "default": "text" },
    "tools_enabled": { "type": "boolean", "default": true },
    "parallel_tool_calls": { "type": "boolean", "default": true }
  }
}
```

### 8.6 `channel_config` JSONB Schema (Campaigns)

```json
{
  "type": "object",
  "description": "Multi-channel campaign configuration",
  "properties": {
    "email": {
      "type": "object",
      "properties": {
        "from_name": { "type": "string" },
        "from_email": { "type": "string", "format": "email" },
        "reply_to": { "type": "string", "format": "email" },
        "tracking_domain": { "type": "string", "format": "hostname" },
        "open_tracking": { "type": "boolean", "default": true },
        "click_tracking": { "type": "boolean", "default": true },
        "unsubscribe_handling": { "type": "string", "enum": ["header", "footer", "both", "custom"], "default": "header" },
        "bounce_handling": { "type": "string", "enum": ["automatic", "manual"], "default": "automatic" }
      }
    },
    "sms": {
      "type": "object",
      "properties": {
        "from_number": { "type": "string" },
        "provider": { "type": "string", "enum": ["twilio", "vonage", "aws_sns"] },
        "encoding": { "type": "string", "enum": ["gsm7", "ucs2"], "default": "gsm7" },
        "max_segments": { "type": "integer", "default": 3 }
      }
    },
    "social": {
      "type": "object",
      "properties": {
        "platforms": {
          "type": "array",
          "items": { "type": "string", "enum": ["linkedin", "twitter", "facebook", "instagram", "tiktok"] }
        },
        "posting_strategy": { "type": "string", "enum": ["now", "scheduled", "best_time"], "default": "scheduled" }
      }
    },
    "landing_page": {
      "type": "object",
      "properties": {
        "domain": { "type": "string" },
        "slug": { "type": "string" },
        "analytics_tracking": { "type": "boolean", "default": true },
        "a_b_testing": { "type": "boolean", "default": false },
        "variants": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "variant_name": { "type": "string" },
              "traffic_percentage": { "type": "number", "minimum": 0, "maximum": 100 },
              "landing_page_id": { "type": "string", "format": "uuid" }
            }
          }
        }
      }
    },
    "drip": {
      "type": "object",
      "properties": {
        "trigger_event": { "type": "string" },
        "timezone_sensitive": { "type": "boolean", "default": true },
        "exit_on_conversion": { "type": "boolean", "default": true },
        "max_emails_per_week": { "type": "integer", "default": 5 }
      }
    }
  }
}
```

### 8.7 `guardrails` JSONB Schema (AI Agents)

```json
{
  "type": "object",
  "properties": {
    "content_safety": {
      "type": "object",
      "properties": {
        "blocked_topics": { "type": "array", "items": { "type": "string" } },
        "blocked_words": { "type": "array", "items": { "type": "string" } },
        "toxicity_threshold": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.7 },
        "pii_redaction": { "type": "boolean", "default": true }
      }
    },
    "action_limits": {
      "type": "object",
      "properties": {
        "max_tool_calls_per_conversation": { "type": "integer", "default": 50 },
        "max_tokens_per_response": { "type": "integer", "default": 4096 },
        "max_daily_generations": { "type": "integer", "default": 1000 },
        "cost_limit_per_day_usd": { "type": "number", "default": 10.0 }
      }
    },
    "scope_restrictions": {
      "type": "object",
      "properties": {
        "allowed_modules": { "type": "array", "items": { "type": "string" } },
        "allowed_tools": { "type": "array", "items": { "type": "string" } },
        "restricted_operations": { "type": "array", "items": { "type": "string" } },
        "workspace_data_only": { "type": "boolean", "default": true }
      }
    },
    "escalation": {
      "type": "object",
      "properties": {
        "auto_escalate_on": { "type": "array", "items": { "type": "string" } },
        "escalation_contact": { "type": "string", "format": "email" },
        "escalation_workflow_id": { "type": "string", "format": "uuid" }
      }
    }
  }
}
```

### 8.8 `memory_config` JSONB Schema (AI Agents)

```json
{
  "type": "object",
  "properties": {
    "short_term": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "ttl_minutes": { "type": "integer", "default": 30 },
        "max_messages": { "type": "integer", "default": 50 }
      }
    },
    "long_term": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean", "default": true },
        "summarization_threshold": { "type": "integer", "default": 10, "description": "Messages before summarization" },
        "retrieval_limit": { "type": "integer", "default": 5 },
        "importance_threshold": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.5 },
        "auto_summarize": { "type": "boolean", "default": true }
      }
    },
    "vector_store": {
      "type": "object",
      "properties": {
        "collection_prefix": { "type": "string", "default": "ai_memory_" },
        "embedding_model": { "type": "string", "default": "text-embedding-3-large" },
        "vector_dimensions": { "type": "integer", "default": 3072 },
        "distance_metric": { "type": "string", "enum": ["cosine", "dot", "euclidean"], "default": "cosine" }
      }
    }
  }
}
```

---

## Appendices

### A. Complete Table Inventory

| # | Module | Table | Tenant-Scoped | Soft Delete | RLS | History | Partitioned | Est. Growth/Month |
|---|--------|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Auth | `users` | ✓ | ✓ | ✓ | ✓ | — | 1K–10K |
| 2 | Auth | `oauth_accounts` | — | — | — | — | — | 1K–5K |
| 3 | Auth | `sessions` | ✓ | — | ✓ | — | — | 10K–100K |
| 4 | Auth | `mfa_devices` | — | — | — | — | — | 0–1K |
| 5 | Auth | `api_keys` | ✓ | — | ✓ | — | — | 0–1K |
| 6 | Auth | `roles` | ✓ | ✓ | ✓ | — | — | 10–100 |
| 7 | Auth | `permissions` | — | — | — | — | — | 100–500 |
| 8 | Auth | `role_permissions` | — | — | — | — | — | 200–2K |
| 9 | Auth | `user_roles` | — | — | — | — | — | 1K–10K |
| 10 | Org | `tenants` | Root | ✓ | — | ✓ | — | 10–500 |
| 11 | Org | `workspaces` | ✓ | ✓ | ✓ | ✓ | — | 10–2K |
| 12 | Org | `workspace_users` | ✓ | — | ✓ | — | — | 1K–50K |
| 13 | Org | `teams` | ✓ | ✓ | — | — | — | 10–2K |
| 14 | Org | `team_members` | — | — | — | — | — | 50–10K |
| 15 | Org | `subscription_plans` | — | — | — | — | — | 5–20 |
| 16 | Org | `tenant_subscriptions` | ✓ | — | ✓ | ✓ | — | 10–500 |
| 17 | CRM | `contacts` | ✓ | ✓ | ✓ | ✓ | — | 10K–500K |
| 18 | CRM | `organizations` | ✓ | ✓ | ✓ | ✓ | — | 1K–50K |
| 19 | CRM | `leads` | ✓ | ✓ | ✓ | ✓ | — | 5K–100K |
| 20 | CRM | `deals` | ✓ | ✓ | ✓ | ✓ | — | 1K–50K |
| 21 | CRM | `pipelines` | ✓ | ✓ | ✓ | — | — | 1–50 |
| 22 | CRM | `pipeline_stages` | — | — | — | — | — | 5–50 |
| 23 | CRM | `activities` | ✓ | — | ✓ | — | ✓ (monthly) | 10K–500K |
| 24 | CRM | `tasks` | ✓ | ✓ | ✓ | ✓ | — | 1K–50K |
| 25 | CRM | `meetings` | ✓ | ✓ | ✓ | ✓ | — | 1K–10K |
| 26 | CRM | `notes` | ✓ | ✓ | ✓ | ✓ | — | 5K–100K |
| 27 | CRM | `tags` | ✓ | — | ✓ | — | — | 10–1K |
| 28 | CRM | `contact_tags` | — | — | — | — | — | 10K–500K |
| 29 | CRM | `file_attachments` | ✓ | ✓ | ✓ | ✓ | — | 1K–10K |
| 30 | Mktg | `campaigns` | ✓ | ✓ | ✓ | ✓ | — | 100–10K |
| 31 | Mktg | `campaign_channels` | — | — | — | — | — | 200–20K |
| 32 | Mktg | `email_templates` | ✓ | ✓ | ✓ | — | — | 50–5K |
| 33 | Mktg | `campaign_emails` | ✓ | — | ✓ | — | ✓ (monthly) | 100K–10M |
| 34 | Mktg | `sms_templates` | ✓ | ✓ | ✓ | — | — | 10–1K |
| 35 | Mktg | `landing_pages` | ✓ | ✓ | ✓ | ✓ | — | 10–1K |
| 36 | Mktg | `funnels` | ✓ | ✓ | ✓ | ✓ | — | 10–1K |
| 37 | Mktg | `funnel_stages` | — | — | — | — | — | 50–5K |
| 38 | Mktg | `segments` | ✓ | ✓ | ✓ | ✓ | — | 50–5K |
| 39 | Mktg | `segment_conditions` | — | — | — | — | — | 100–10K |
| 40 | Mktg | `contact_segments` | — | — | — | — | — | 10K–1M |
| 41 | AI | `ai_generations` | ✓ | — | ✓ | ✓ | — | 1K–100K |
| 42 | AI | `brand_voices` | ✓ | ✓ | ✓ | — | — | 5–100 |
| 43 | AI | `ai_templates` | ✓ | ✓ | ✓ | — | — | 10–500 |
| 44 | AI | `generation_history` | — | — | — | — | — | 1K–100K |
| 45 | SEO | `keywords` | ✓ | ✓ | ✓ | ✓ | — | 1K–100K |
| 46 | SEO | `keyword_rankings` | — | — | — | — | — | 10K–1M |
| 47 | SEO | `competitor_sites` | ✓ | — | ✓ | — | — | 10–500 |
| 48 | SEO | `backlinks` | ✓ | — | ✓ | — | — | 1K–500K |
| 49 | SEO | `serp_results` | — | — | — | — | — | 10K–500K |
| 50 | SEO | `site_audits` | ✓ | — | ✓ | ✓ | — | 10–1K |
| 51 | SEO | `schema_markup` | ✓ | — | ✓ | — | — | 10–5K |
| 52 | Social | `social_accounts` | ✓ | ✓ | ✓ | — | — | 5–50 |
| 53 | Social | `social_posts` | ✓ | ✓ | ✓ | ✓ | — | 100–10K |
| 54 | Social | `post_schedules` | — | — | — | — | — | 100–10K |
| 55 | Social | `social_analytics` | — | — | — | — | ✓ (monthly) | 1K–100K |
| 56 | Social | `hashtag_library` | ✓ | — | ✓ | — | — | 10–5K |
| 57 | Social | `reply_templates` | ✓ | ✓ | ✓ | — | — | 10–500 |
| 58 | Social | `social_conversations` | ✓ | — | ✓ | ✓ | — | 1K–50K |
| 59 | Auto | `workflows` | ✓ | ✓ | ✓ | ✓ | — | 50–5K |
| 60 | Auto | `workflow_triggers` | — | — | — | — | — | 50–5K |
| 61 | Auto | `workflow_actions` | — | — | — | — | — | 200–20K |
| 62 | Auto | `workflow_executions` | ✓ | — | ✓ | — | ✓ (monthly) | 1K–500K |
| 63 | Auto | `execution_logs` | — | — | — | — | ✓ (monthly) | 10K–10M |
| 64 | Auto | `workflow_templates` | — | — | — | — | — | 50–500 |
| 65 | Agents | `agents` | ✓ | ✓ | ✓ | ✓ | — | 5–100 |
| 66 | Agents | `agent_conversations` | ✓ | — | ✓ | ✓ | — | 1K–100K |
| 67 | Agents | `agent_messages` | — | — | — | — | — | 10K–1M |
| 68 | Agents | `agent_tools` | — | — | — | — | — | 50–500 |
| 69 | Agents | `agent_memory` | ✓ | — | ✓ | — | — | 1K–100K |
| 70 | Agents | `agent_knowledge_refs` | — | — | — | — | — | 1K–50K |
| 71 | Agents | `agent_executions` | ✓ | — | ✓ | — | ✓ (monthly) | 1K–100K |
| 72 | Agents | `agent_goals` | — | — | — | — | — | 10–500 |
| 73 | KB | `kb_documents` | ✓ | ✓ | ✓ | ✓ | — | 100–10K |
| 74 | KB | `kb_chunks` | — | — | — | — | — | 1K–100K |
| 75 | KB | `kb_categories` | ✓ | — | ✓ | — | — | 10–500 |
| 76 | KB | `kb_permissions` | — | — | — | — | — | 100–10K |
| 77 | KB | `kb_versions` | — | — | — | — | — | 200–20K |
| 78 | Analytics | `analytics_events` | ✓ | — | ✓ | — | ✓ (daily) | 1M–100M |
| 79 | Analytics | `analytics_dashboards` | ✓ | ✓ | ✓ | — | — | 10–500 |
| 80 | Analytics | `dashboard_widgets` | — | — | — | — | — | 50–5K |
| 81 | Analytics | `saved_reports` | ✓ | ✓ | ✓ | — | — | 10–1K |
| 82 | Analytics | `metric_definitions` | — | — | — | — | — | 50–500 |
| 83 | Billing | `plans` | — | — | — | — | — | 5–20 |
| 84 | Billing | `subscriptions` | ✓ | — | ✓ | ✓ | — | 10–500 |
| 85 | Billing | `invoices` | ✓ | — | ✓ | ✓ | — | 100–10K |
| 86 | Billing | `invoice_items` | — | — | — | — | — | 200–20K |
| 87 | Billing | `payments` | ✓ | — | ✓ | ✓ | — | 100–10K |
| 88 | Billing | `credits` | ✓ | — | ✓ | — | — | 10–500 |
| 89 | Billing | `credit_transactions` | — | — | — | — | — | 100–10K |
| 90 | Billing | `coupons` | — | — | — | — | — | 10–500 |
| 91 | Billing | `taxes` | — | — | — | — | — | 10–200 |
| 92 | Billing | `wallet_transactions` | ✓ | — | ✓ | — | — | 100–5K |
| 93 | Billing | `affiliate_payouts` | — | — | — | — | — | 10–1K |
| 94 | Marketplace | `marketplace_listings` | — | ✓ | — | ✓ | — | 10–1K |
| 95 | Marketplace | `listing_versions` | — | — | — | — | — | 20–2K |
| 96 | Marketplace | `reviews` | — | — | — | — | — | 50–5K |
| 97 | Marketplace | `installations` | ✓ | — | ✓ | — | — | 100–10K |
| 98 | Marketplace | `developer_profiles` | — | — | — | — | — | 10–500 |
| 99 | Notifications | `notification_templates` | ✓ | ✓ | ✓ | — | — | 10–500 |
| 100 | Notifications | `notification_queue` | ✓ | — | ✓ | — | — | 10K–1M |
| 101 | Notifications | `notification_preferences` | ✓ | — | ✓ | — | — | 1K–50K |
| 102 | Notifications | `notification_logs` | — | — | — | — | ✓ (monthly) | 10K–10M |
| 103 | Media | `media_assets` | ✓ | ✓ | ✓ | ✓ | — | 1K–50K |
| 104 | Media | `asset_folders` | ✓ | ✓ | ✓ | — | — | 10–1K |
| 105 | Media | `asset_versions` | — | — | — | — | — | 1K–50K |
| 106 | Media | `asset_tags` | — | — | — | — | — | 1K–50K |

### B. Extension Requirements

```sql
-- Required PostgreSQL extensions for AMC
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";       -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- Encryption (PII)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram fuzzy text search
CREATE EXTENSION IF NOT EXISTS "moddatetime";       -- Auto-update updated_at
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";-- Query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_partman";        -- Automated partition management
CREATE EXTENSION IF NOT EXISTS "pg_cron";           -- In-database job scheduling
CREATE EXTENSION IF NOT EXISTS "btree_gin";         -- GIN on b-tree columns
CREATE EXTENSION IF NOT EXISTS "pgstattuple";       -- Table statistics
CREATE EXTENSION IF NOT EXISTS "pg_repack";         -- Online table rebuild

-- Optional extensions
-- CREATE EXTENSION IF NOT EXISTS "postgis";        -- Geospatial queries (future)
-- CREATE EXTENSION IF NOT EXISTS "pg_net";         -- Async HTTP requests (future)
-- CREATE EXTENSION IF NOT EXISTS "pg_vector";      -- Vector similarity (alternative to Qdrant)
```

### C. Initial Schema Migration (0001)

```python
"""Initial schema: tenants, users, auth tables

Revision ID: 0001
Revises: None
Create Date: 2026-06-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = ('core',)
depends_on = None

def upgrade():
    # === Extensions ===
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS uuid-ossp")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS moddatetime")

    # === tenants ===
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('domain', sa.Text(), nullable=True),
        sa.Column('settings', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('features_enabled', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('tier', sa.Text(), server_default='free', nullable=False),
        sa.Column('max_users', sa.Integer(), server_default='5', nullable=False),
        sa.Column('max_workspaces', sa.Integer(), server_default='1', nullable=False),
        sa.Column('max_storage_gb', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("tier IN ('free', 'starter', 'professional', 'enterprise')", name='ck_tenants_tier')
    )
    op.create_index('idx_tenants_slug', 'tenants', ['slug'], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_tenants_domain', 'tenants', ['domain'],
                    postgresql_where=sa.text('domain IS NOT NULL AND deleted_at IS NULL'),
                    unique=True)
    op.create_index('idx_tenants_settings', 'tenants', ['settings'],
                    postgresql_using='gin', postgresql_ops={'settings': 'jsonb_path_ops'})
    op.execute("""
        CREATE TRIGGER mdt_tenants_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at)
    """)
    op.execute("""
        CREATE TABLE tenants_history (LIKE tenants INCLUDING ALL)
    """)
    op.execute("""
        ALTER TABLE tenants_history ADD COLUMN operation TEXT,
                                     ADD COLUMN changed_by UUID,
                                     ADD COLUMN changed_at TIMESTAMPTZ DEFAULT NOW()
    """)

    # === users ===
    op.create_table('users',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=True),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), server_default='FALSE', nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('locale', sa.Text(), server_default='en', nullable=False),
        sa.Column('timezone', sa.Text(), server_default='UTC', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='TRUE', nullable=False),
        sa.Column('is_superadmin', sa.Boolean(), server_default='FALSE', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_users_tenants',
                                ondelete='SET NULL')
    )
    op.create_index('idx_users_email', 'users', [sa.text('lower(email)')], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'],
                    postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_display_name', 'users', ['display_name'],
                    postgresql_using='gin', postgresql_ops={'display_name': 'gin_trgm_ops'})
    op.create_index('idx_users_metadata', 'users', ['metadata'],
                    postgresql_using='gin', postgresql_ops={'metadata': 'jsonb_path_ops'})
    op.create_index('idx_users_active', 'users', ['id'],
                    postgresql_where=sa.text('deleted_at IS NULL AND is_active = TRUE'))

    op.execute("""
        CREATE TRIGGER mdt_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at)
    """)
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON users FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id')::UUID OR tenant_id IS NULL)
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id')::UUID
            OR current_setting('app.user_role') = 'superadmin'
        )
    """)

    # === workspaces ===
    op.create_table('workspaces',
        # ... columns (see DDL above) ...
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(), nullable=False),
        # ... additional columns ...
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_workspaces_tenants')
    )
    # ... indexes and RLS ...

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.drop_table('users_history')
    op.drop_table('users')
    op.drop_table('tenants_history')
    op.drop_table('tenants')
    op.execute("DROP EXTENSION IF EXISTS moddatetime")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS uuid-ossp")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
```

---

> **Document Control**  
> **Last Updated:** June 19, 2026  
> **Next Review:** September 19, 2026  
> **Maintainer:** Database Architecture Team  
> **Reviewers:** Architecture Team, Security Team, Data Engineering  
>
> **Related Documents:**
> - Volume 1: Vision, Mission & Business Goals
> - Volume 4: System Architecture
> - Volume 6: API Design & Contracts
> - Volume 7: Security & Compliance
> - Volume 9: AI Agent Design
> - Volume 12: Operations & DevOps
> - Volume 14: Data Engineering & Pipelines
