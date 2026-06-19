# Volume 6: Backend API Specification (REST + GraphQL)

## Aegis Marketing Cloud (AMC)

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering  
> **Date:** June 2026  
> **Author:** API Platform Team  
> **Status:** Draft  
> **Volume:** 6 of 15  

---

## Table of Contents

1. [API Design Philosophy](#1-api-design-philosophy)
   - 1.1 [REST + GraphQL Coexistence Strategy](#11-rest--graphql-coexistence-strategy)
   - 1.2 [URL Structure](#12-url-structure)
   - 1.3 [Pagination](#13-pagination)
   - 1.4 [Error Response Format (RFC 7807)](#14-error-response-format-rfc-7807)
   - 1.5 [Rate Limiting Headers](#15-rate-limiting-headers)
   - 1.6 [Versioning Strategy](#16-versioning-strategy)
2. [Authentication & Authorization](#2-authentication--authorization)
   - 2.1 [JWT Access/Refresh Token Endpoints](#21-jwt-accessrefresh-token-endpoints)
   - 2.2 [Bearer Token Usage](#22-bearer-token-usage)
   - 2.3 [API Key Auth for Programmatic Access](#23-api-key-auth-for-programmatic-access)
   - 2.4 [RBAC Scope Enforcement](#24-rbac-scope-enforcement)
   - 2.5 [Tenant Resolution](#25-tenant-resolution)
3. [Common API Patterns](#3-common-api-patterns)
   - 3.1 [List Endpoint](#31-list-endpoint)
   - 3.2 [Create/Update](#32-createupdate)
   - 3.3 [Delete & Restore](#33-delete--restore)
   - 3.4 [Bulk Operations](#34-bulk-operations)
   - 3.5 [Export](#35-export)
   - 3.6 [Search](#36-search)
4. [Response Envelope](#4-response-envelope)
   - 4.1 [Success Response](#41-success-response)
   - 4.2 [Error Response](#42-error-response)
   - 4.3 [Batch Response](#43-batch-response)
5. [REST API Endpoints](#5-rest-api-endpoints)
   - 5.1 [Auth Module](#51-auth-module)
   - 5.2 [Tenant & Workspace Module](#52-tenant--workspace-module)
   - 5.3 [CRM Module](#53-crm-module)
   - 5.4 [Marketing Module](#54-marketing-module)
   - 5.5 [AI Suite Module](#55-ai-suite-module)
   - 5.6 [SEO Module](#56-seo-module)
   - 5.7 [Social Module](#57-social-module)
   - 5.8 [Automation Module](#58-automation-module)
   - 5.9 [AI Agents Module](#59-ai-agents-module)
   - 5.10 [Knowledge Base Module](#510-knowledge-base-module)
   - 5.11 [Analytics Module](#511-analytics-module)
   - 5.12 [Billing Module](#512-billing-module)
   - 5.13 [Marketplace Module](#513-marketplace-module)
   - 5.14 [Notifications Module](#514-notifications-module)
   - 5.15 [Media Library Module](#515-media-library-module)
   - 5.16 [Admin Module](#516-admin-module)
6. [GraphQL Schema](#6-graphql-schema)
   - 6.1 [Key GraphQL Types](#61-key-graphql-types)
   - 6.2 [Query & Mutation Signatures](#62-query--mutation-signatures)
   - 6.3 [REST vs GraphQL Decision Matrix](#63-rest-vs-graphql-decision-matrix)
7. [Webhook Specifications](#7-webhook-specifications)
   - 7.1 [Webhook Event Catalog](#71-webhook-event-catalog)
   - 7.2 [Delivery Format](#72-delivery-format)
   - 7.3 [Retry & Deduplication Strategy](#73-retry--deduplication-strategy)
   - 7.4 [Signature Verification](#74-signature-verification)
   - 7.5 [Webhook Secret Management](#75-webhook-secret-management)
8. [SDK / Client Libraries](#8-sdk--client-libraries)
   - 8.1 [Python SDK](#81-python-sdk)
   - 8.2 [TypeScript SDK](#82-typescript-sdk)
   - 8.3 [CLI Tool](#83-cli-tool)

---

## 1. API Design Philosophy

### 1.1 REST + GraphQL Coexistence Strategy

AMC exposes both a **RESTful API** and a **GraphQL API** — not as alternatives, but as complementary interfaces designed for different use cases.

#### Design Rationale

| Dimension | REST | GraphQL |
|-----------|------|---------|
| **Primary Use Case** | CRUD operations, file uploads, webhook callbacks, integrations | Dashboard data fetching, nested entity queries, mobile clients |
| **HTTP Methods** | GET, POST, PUT, PATCH, DELETE | POST (single endpoint at `/api/v1/graphql`) |
| **Data Shape** | Fixed response schemas per endpoint | Client-specified fields and relationships |
| **Caching** | Native HTTP caching (ETag, Last-Modified) | Requires CDN-level or persisted queries |
| **File Upload** | Multipart POST | Multipart with GraphQL Upload spec |
| **Tooling** | OpenAPI 3.1 (auto-generated docs) | GraphQL Schema SDL + GraphiQL IDE |
| **Versioning** | URL-prefixed (`/api/v1/`) | No explicit versioning (schema evolution via deprecation) |
| **Error Handling** | Per-status-code responses | Unified `errors[]` array with extensions |

#### Coexistence Rules

1. **REST is the system of record** — All mutations go through REST endpoints first. GraphQL mutations are thin wrappers that delegate to the same service layer.
2. **GraphQL is read-optimized** — Complex nested reads (e.g., "get contact with deals, activities, and notes") use GraphQL. Simple CRUD uses REST.
3. **File uploads are REST-only** — The GraphQL Upload spec adds complexity without benefit for AMC's use cases.
4. **Webhooks deliver REST payloads** — All webhook events are POSTed as JSON conforming to REST resource schemas.
5. **Rate limits share a pool** — Both interfaces draw from the same tenant-level rate limit bucket.
6. **Authentication is identical** — Both accept the same JWT Bearer token or API key header.

```
Client Application
  ├── CRUD, Uploads ──> FastAPI /api/v1/{resource}
  └── Complex Queries ──> Strawberry /api/v1/graphql
                             │
                             └──> Service Layer
                                    ├── PostgreSQL
                                    ├── AI Agents
                                    └── Workflow Engine
```

### 1.2 URL Structure

All API endpoints are prefixed with `/api/v1/` to enable clean versioning and gateway routing.

```
/api/v1/{module}/{resource}[/{id}][/{action}]
```

| Component | Example | Description |
|-----------|---------|-------------|
| **Base** | `/api/v1` | Fixed prefix. Version `v1` is the current stable version. |
| **Module** | `/crm` | Logical module grouping. Maps to service boundaries. |
| **Resource** | `/contacts` | Plural noun representing the resource collection. |
| **ID** | `/crm/contacts/cont_abc123` | UUID or prefixed ULID identifying a single resource. |
| **Action** | `/restore` | Verb-based sub-resource for non-CRUD operations. |

**Examples:**
- `GET /api/v1/crm/contacts` — List all contacts
- `POST /api/v1/crm/contacts` — Create a contact  
- `GET /api/v1/crm/contacts/cont_abc123` — Get a specific contact
- `PATCH /api/v1/crm/contacts/cont_abc123` — Partial update a contact
- `DELETE /api/v1/crm/contacts/cont_abc123` — Soft-delete a contact
- `POST /api/v1/crm/contacts/cont_abc123/restore` — Restore a soft-deleted contact
- `POST /api/v1/crm/contacts/batch` — Bulk operation on contacts
- `POST /api/v1/crm/contacts/search` — Full-text search across contacts

#### Resource ID Format

All primary keys use **prefixed ULIDs** (Universally Unique Lexicographically Sortable Identifier):

| Prefix | Resource |
|--------|----------|
| `cont_` | Contact |
| `deal_` | Deal |
| `pipe_` | Pipeline |
| `stag_` | Pipeline Stage |
| `acti_` | Activity |
| `task_` | Task |
| `camp_` | Campaign |
| `tpl_` | Email Template |
| `seg_` | Segment |
| `lp_` | Landing Page |
| `gen_` | AI Generation |
| `kv_` | Keyword |
| `aud_` | SEO Audit |
| `soc_` | Social Account |
| `sp_` | Social Post |
| `wf_` | Workflow |
| `wft_` | Workflow Template |
| `exec_` | Workflow Execution |
| `ag_` | AI Agent |
| `agt_` | Agent Task |
| `doc_` | Knowledge Base Document |
| `cat_` | Knowledge Base Category |
| `dash_` | Dashboard |
| `rpt_` | Report |
| `plan_` | Billing Plan |
| `sub_` | Subscription |
| `inv_` | Invoice |
| `pm_` | Payment Method |
| `cred_` | Credit Transaction |
| `wal_` | Wallet |
| `list_` | Marketplace Listing |
| `rev_` | Marketplace Review |
| `notif_` | Notification |
| `asset_` | Media Asset |
| `fldr_` | Media Folder |
| `api_` | API Key |
| `sess_` | Session |
| `ten_` | Tenant |
| `ws_` | Workspace |
| `usr_` | User |

#### Header Conventions

| Header | Required | Description |
|--------|----------|-------------|
| `X-Tenant-ID` | Yes | Tenant identifier for multi-tenancy routing |
| `X-Workspace-ID` | Conditional | Workspace scope (required for workspace-scoped resources) |
| `X-Request-ID` | Recommended | Client-generated idempotency key / correlation ID |
| `X-Idempotency-Key` | Conditional | Idempotency key for POST/PATCH requests |
| `Authorization` | Yes (for protected) | `Bearer <jwt>` or `Bearer <api_key>` |
| `Content-Type` | Yes | `application/json` (default), `multipart/form-data` for uploads |
| `Accept` | No | `application/json` (default), `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `Accept-Language` | No | Locale for error messages (e.g., `en-US`, `fr-FR`) |
| `Sunset` | Response | Signals API deprecation date |

#### Idempotency

POST and PATCH endpoints that create or update resources support idempotent retries via the `X-Idempotency-Key` header. The server caches the response for a key for 24 hours. Duplicate requests with the same key return the cached response.

### 1.3 Pagination

AMC uses two pagination strategies depending on the endpoint:

#### Cursor-Based Pagination (Default for List Endpoints)

Used for stable lists where items are frequently added/removed. Cursors are opaque base64-encoded strings.

**Request Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cursor` | string | — | Opaque cursor from previous response's `meta.next` |
| `limit` | integer | 50 | Maximum items per page (1–100) |
| `sort` | string | `-created_at` | Sort field with optional `-` prefix for descending |
| `fields` | string | — | Comma-separated field list for sparse fieldsets |
| `filter` | string | — | JSON-encoded filter expression |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `data` | array | Array of resource objects |
| `meta.page` | integer | Current page number (sequential) |
| `meta.per_page` | integer | Items per page |
| `meta.total` | integer | Total matching items (approximate for large collections) |
| `meta.has_more` | boolean | Whether additional pages exist |
| `links.self` | string | URL of current request |
| `links.next` | string | URL for next page (absent if no more) |
| `links.prev` | string | URL for previous page (absent on first page) |

**Example Request:**
```
GET /api/v1/crm/contacts?cursor=eyJpZC...oifQ==&limit=25&sort=-created_at&fields=id,first_name,last_name,email
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "cont_xyz789",
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "created_at": "2026-06-19T10:00:00Z"
    }
  ],
  "meta": {
    "page": 2,
    "per_page": 25,
    "total": 1342,
    "has_more": true
  },
  "links": {
    "self": "/api/v1/crm/contacts?cursor=...&limit=25&sort=-created_at",
    "next": "/api/v1/crm/contacts?cursor=...&limit=25&sort=-created_at",
    "prev": "/api/v1/crm/contacts?cursor=...&limit=25&sort=-created_at"
  }
}
```

#### Offset-Limit Pagination (Default for Search Endpoints)

Used for search results where total count accuracy is important and random access to pages is needed.

**Request Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | integer | 0 | Number of items to skip |
| `limit` | integer | 20 | Maximum items per page (1–100) |
| `sort` | string | `-created_at` | Sort field with optional `-` prefix |
| `q` | string | — | Search query string |

**Response:**
Same envelope as cursor-based, but `meta` includes `offset` instead of cursor info.

#### Filtering Syntax

Filters are expressed as a JSON-encoded string in the `filter` query parameter:

```json
{
  "and": [
    {"field": "status", "op": "eq", "value": "active"},
    {"field": "created_at", "op": "gte", "value": "2026-01-01"},
    {
      "or": [
        {"field": "source", "op": "eq", "value": "website"},
        {"field": "source", "op": "eq", "value": "referral"}
      ]
    }
  ]
}
```

Supported operators: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `contains`, `icontains`, `startswith`, `endswith`, `is_null`, `is_not_null`.

#### Field Selection

Use `?fields=id,first_name,email` to request only specific fields in the response. This reduces payload size and improves performance for bandwidth-constrained clients.

### 1.4 Error Response Format (RFC 7807)

All API errors conform to RFC 7807 (Problem Details for HTTP APIs).

```json
{
  "error": {
    "type": "https://api.amc.io/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "The request body contains invalid fields.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "abc123def456",
    "errors": [
      {
        "field": "email",
        "message": "Must be a valid email address",
        "code": "invalid_email"
      },
      {
        "field": "phone",
        "message": "Must be a valid phone number in E.164 format",
        "code": "invalid_phone"
      }
    ]
  }
}
```

| Field | Type | Always Present | Description |
|-------|------|:---:|-------------|
| `error.type` | URI | Yes | URI identifying the problem type |
| `error.title` | string | Yes | Short, human-readable summary |
| `error.status` | integer | Yes | HTTP status code |
| `error.detail` | string | Yes | Human-readable explanation |
| `error.instance` | string | Yes | URI identifying the specific occurrence |
| `error.trace_id` | string | No | Distributed tracing correlation ID |
| `error.errors` | array | No | Array of field-level errors |
| `error.errors[].field` | string | Conditional | JSON pointer to the field in error |
| `error.errors[].message` | string | Yes | Human-readable error description |
| `error.errors[].code` | string | Yes | Machine-readable error code |

#### Standard Error Types

| Type URI | HTTP Status | Title | When |
|----------|:-----------:|-------|------|
| `https://api.amc.io/errors/validation-error` | 422 | Validation Error | Request body fails validation |
| `https://api.amc.io/errors/authentication-error` | 401 | Authentication Error | Missing or invalid credentials |
| `https://api.amc.io/errors/authorization-error` | 403 | Authorization Error | Valid credentials but insufficient permissions |
| `https://api.amc.io/errors/not-found` | 404 | Resource Not Found | Requested resource does not exist |
| `https://api.amc.io/errors/conflict` | 409 | Conflict | Resource state conflict (e.g., duplicate) |
| `https://api.amc.io/errors/rate-limit-error` | 429 | Rate Limit Exceeded | Too many requests |
| `https://api.amc.io/errors/internal-error` | 500 | Internal Server Error | Unexpected server error |
| `https://api.amc.io/errors/service-unavailable` | 503 | Service Unavailable | Temporary maintenance or overload |

### 1.5 Rate Limiting Headers

Rate limiting is applied per **tenant + endpoint group**. Limits are configurable per plan tier.

#### Request Headers (Server Response)

| Header | Example | Description |
|--------|---------|-------------|
| `X-RateLimit-Limit` | `1000` | Maximum requests allowed in the current window |
| `X-RateLimit-Remaining` | `842` | Remaining requests in the current window |
| `X-RateLimit-Reset` | `1687200000` | Unix timestamp when the window resets |
| `Retry-After` | `35` | Seconds to wait before retrying (only on 429 responses) |

#### Default Limits by Tier

| Tier | Rate Limit (req/min) | Burst Limit | Concurrent Connections |
|------|:-------------------:|:-----------:|:---------------------:|
| Free | 60 | 100 | 5 |
| Pro | 600 | 1,000 | 25 |
| Business | 3,000 | 5,000 | 100 |
| Enterprise | 10,000 | 20,000 | 500 |

When a client exceeds the limit, the API responds with `429 Too Many Requests` and includes a `Retry-After` header indicating the wait time in seconds.

#### Burst Handling

The burst limit allows short spikes above the baseline rate. Burst capacity replenishes at the baseline rate. Once the burst is exhausted, requests are queued or rejected until capacity is restored.

### 1.6 Versioning Strategy

AMC uses **URL-prefixed versioning** (`/api/v1/`, `/api/v2/`) as the primary versioning mechanism.

#### Version Lifecycle

| Phase | Duration | URL Prefix | Behavior |
|-------|----------|:----------:|----------|
| **Alpha** | 0–3 months | `/api/v1alpha/` | Breaking changes allowed, no deprecation notice |
| **Beta** | 1–6 months | `/api/v1beta/` | Feature-complete, API may change with notice |
| **Stable** | 18+ months | `/api/v1/` | No breaking changes, additive evolution only |
| **Deprecated** | 6 months | `/api/v1/` | `Sunset` header added; Sunsets 6 months from deprecation date |
| **Sunset** | — | `/api/v1/` | Returns 410 Gone with link to migration guide |

#### Breaking vs. Non-Breaking Changes

| Change | Classification | Version Policy |
|--------|:--------------:|----------------|
| Adding a new endpoint | Non-breaking | Add to current `v1` |
| Adding an optional field to response | Non-breaking | Add to current `v1` |
| Adding an optional request parameter | Non-breaking | Add to current `v1` |
| Adding enum values | Non-breaking | Add to current `v1` |
| Removing an endpoint | Breaking | New major version (`v2`) |
| Removing a field from response | Breaking | New major version (`v2`) |
| Changing a required field to optional | Breaking | New major version (`v2`) |
| Renaming a field | Breaking | New major version (`v2`) |
| Changing error codes | Breaking | New major version (`v2`) |
| Changing pagination defaults (incompatible change) | Breaking | New major version (`v2`) |

#### Deprecation Headers

When an endpoint or field is deprecated, the API returns:

```
Sunset: Sat, 19 Dec 2026 00:00:00 GMT
Deprecation: true
Link: </docs/migration/v1-to-v2>; rel="deprecation"; type="text/html"
```

---

## 2. Authentication & Authorization

### 2.1 JWT Access/Refresh Token Endpoints

AMC uses a **dual-token JWT** strategy:
- **Access Token** (short-lived, 15 minutes) — Carries user identity, roles, and scopes
- **Refresh Token** (long-lived, 7 days rotating) — Used to obtain new access tokens

#### Token Structure

**Access Token Claims:**
```json
{
  "sub": "usr_a1b2c3d4",
  "ten": "ten_zk1ym2n3",
  "ws": "ws_x9y8z7w6",
  "roles": ["admin", "marketing_manager"],
  "scopes": ["crm:read", "crm:write", "campaigns:read", "campaigns:write"],
  "iat": 1687100000,
  "exp": 1687100900,
  "jti": "unique-token-id"
}
```

**Refresh Token Claims:**
```json
{
  "sub": "usr_a1b2c3d4",
  "ten": "ten_zk1ym2n3",
  "type": "refresh",
  "iat": 1687100000,
  "exp": 1687704800,
  "jti": "unique-refresh-id",
  "rot": 1
}
```

#### Token Endpoints

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/auth/register` | None | Create a new user account |
| `POST` | `/api/v1/auth/login` | None | Authenticate and receive tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh | Obtain new access token using refresh token |
| `POST` | `/api/v1/auth/logout` | Bearer | Invalidate current refresh token |
| `POST` | `/api/v1/auth/password/reset` | None | Request password reset email |
| `POST` | `/api/v1/auth/password/change` | Bearer | Change password (authenticated) |

### 2.2 Bearer Token Usage

All authenticated requests must include an `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6InB1YmxpYzpjM2Jh...
```

Tokens are **RS256** signed JWTs. The public key is exposed at `GET /api/v1/auth/.well-known/jwks.json` for offline verification.

**Validation flow:**
1. Extract token from `Authorization: Bearer <token>`
2. Verify JWT signature using JWKS
3. Check `exp` (expiration) and `nbf` (not before) claims
4. Extract `ten` (tenant), `ws` (workspace), `roles`, and `scopes`
5. Verify tenant matches `X-Tenant-ID` header (if both present)
6. Verify required scopes for the requested operation
7. Attach identity context to request for downstream services

### 2.3 API Key Auth for Programmatic Access

For machine-to-machine communication (CI/CD, batch scripts, integrations), AMC supports **API key authentication**.

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/auth/api-keys` | Bearer | Generate a new API key |
| `GET` | `/api/v1/auth/api-keys` | Bearer | List all API keys for the authenticated user |
| `DELETE` | `/api/v1/auth/api-keys/{id}` | Bearer | Revoke an API key |

**API Key Usage:**
```
Authorization: Bearer amc_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p
```

API keys are prefixed with `amc_live_` (production) or `amc_test_` (sandbox). The full key is only shown once at creation. Keys can be scoped to specific permissions and optionally expire.

**API Key Request Body:**
```json
{
  "name": "CI/CD Pipeline Key",
  "scopes": ["crm:read", "campaigns:read"],
  "expires_at": "2027-06-19T00:00:00Z",
  "workspace_id": "ws_x9y8z7w6"
}
```

### 2.4 RBAC Scope Enforcement

AMC uses a **role-scope-permission** model:

Role → Scopes → Actions

| Concept | Description | Example |
|---------|-------------|---------|
| **Role** | Named collection of scopes | `marketing_manager` |
| **Scope** | `<resource>:<action>` pattern | `campaigns:write` |
| **Action** | Specific operation | Create, Read, Update, Delete, Export, Import |

#### Built-in Roles

| Role | Scopes | Description |
|------|--------|-------------|
| `superadmin` | `*:*` | Platform-wide access (admin only) |
| `admin` | `*:*` (within tenant) | Full access to all resources in tenant |
| `workspace_admin` | `*:*` (within workspace) | Full access within a workspace |
| `marketing_manager` | `campaigns:*`, `segments:*`, `templates:*`, `crm:read`, `analytics:read` | Campaign management |
| `content_creator` | `campaigns:read`, `templates:*`, `ai:*`, `seo:read` | Content creation |
| `crm_manager` | `crm:*`, `deals:*`, `pipelines:*` | CRM management |
| `analyst` | `analytics:*`, `reports:*`, `crm:read`, `campaigns:read` | Data analysis |
| `developer` | `api-keys:*`, `webhooks:*`, `workflows:*` | API integration |
| `member` | Varies by workspace configuration | Base access |
| `viewer` | `*:read` | Read-only access |

### 2.5 Tenant Resolution

Tenant and workspace identity are resolved through a combination of **JWT claims** and **HTTP headers**, with the header taking precedence for flexibility in multi-workspace scenarios.

#### Resolution Order

1. **`X-Tenant-ID` and `X-Workspace-ID` headers** — Used for workspace switching and cross-tenant admin operations
2. **JWT `ten` and `ws` claims** — Default tenant/workspace from authentication
3. **Subdomain** (future) — `tenant.amc.io` — planned for dedicated tenant URLs

#### Header Validation

When a request includes `X-Tenant-ID` and/or `X-Workspace-ID` headers, the API validates that:
1. The tenant exists and is active
2. The authenticated user has access to the specified tenant
3. The workspace (if specified) belongs to the tenant
4. The user has appropriate role in that workspace

#### Tenant Context Propagation

Once resolved, the tenant context is propagated through the system via:
- **Request-scoped context** (Python `contextvars`) — Available in all service layer code
- **Database queries** — `SET session.tenant_id = '...'` for RLS policies
- **Logging** — `tenant_id` field in all structured log entries
- **Metrics** — Tags on all metric data points
- **AI Agents** — Tenant context injected into agent system prompts

---

## 3. Common API Patterns

### 3.1 List Endpoint

**Pattern:** `GET /api/v1/{module}/{resource}`

Standardized list endpoint with filtering, sorting, pagination, and field selection.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cursor` | string | — | Cursor for cursor-based pagination |
| `offset` | integer | 0 | Offset for offset-based pagination |
| `limit` | integer | 50 | Items per page (max 100) |
| `sort` | string | `-created_at` | Sort field, prefix `-` for descending |
| `fields` | string | — | Comma-separated field selection |
| `filter` | string | — | JSON-encoded filter expression |
| `include` | string | — | Comma-separated related resources to include |
| `q` | string | — | Quick search string (for search-enabled lists) |

**Response Envelope:**
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 1342,
    "has_more": true
  },
  "links": {
    "self": "...",
    "next": "...",
    "prev": null
  }
}
```

### 3.2 Create/Update

**Create Pattern:** `POST /api/v1/{module}/{resource}`
**Update Pattern:** `PATCH /api/v1/{module}/{resource}/{id}`

#### Create Request
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "phone": "+14155551234",
  "source": "website",
  "tags": ["lead", "webinar-2026"]
}
```

**Create Response (201 Created):**
```json
{
  "data": {
    "id": "cont_xyz789",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "phone": "+14155551234",
    "source": "website",
    "tags": ["lead", "webinar-2026"],
    "created_at": "2026-06-19T10:00:00Z",
    "updated_at": "2026-06-19T10:00:00Z"
  }
}
```

#### Partial Update (PATCH)

PATCH accepts a **partial resource representation**. Only the provided fields are updated. Null values clear the field if nullable.

```json
{
  "email": "jane.doe@newdomain.com",
  "tags": ["lead", "webinar-2026", "converted"]
}
```

**Response:** Returns the full updated resource.

#### Validation

Validation errors return 422 with field-level details:

```json
{
  "error": {
    "type": "https://api.amc.io/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "3 validation errors in request body.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "abc123",
    "errors": [
      {
        "field": "/email",
        "message": "Must be a valid email address",
        "code": "invalid_email"
      },
      {
        "field": "/phone",
        "message": "Must be a valid phone number in E.164 format",
        "code": "invalid_format"
      },
      {
        "field": "/tags/0",
        "message": "Tag must be lowercase alphanumeric with hyphens",
        "code": "invalid_format"
      }
    ]
  }
}
```

### 3.3 Delete & Restore

AMC implements **soft delete** — records are marked as `deleted_at` timestamp and excluded from default queries, but remain in the database for recovery and audit purposes.

#### Delete

```
DELETE /api/v1/{module}/{resource}/{id}
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "cont_xyz789",
    "deleted_at": "2026-06-19T11:00:00Z",
    "status": "deleted"
  }
}
```

**Notes:**
- Returns 200 (not 204) to confirm the soft delete with metadata
- The resource is still accessible via `?filter={"deleted": true}` or a direct GET with `?include_deleted=true`
- Cascading soft delete: if configured, related child resources are also soft-deleted

#### Restore

```
POST /api/v1/{module}/{resource}/{id}/restore
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "cont_xyz789",
    "deleted_at": null,
    "status": "active",
    "restored_at": "2026-06-19T11:30:00Z"
  }
}
```

#### Hard Delete (Admin Only)

For GDPR data erasure requests and admin cleanup:
```
DELETE /api/v1/admin/tenants/{tenantId}/purge/{resource}/{id}
```
Requires `superadmin` role. Returns 204 No Content on success.

### 3.4 Bulk Operations

**Pattern:** `POST /api/v1/{module}/{resource}/batch`

Bulk operations allow performing the same action on multiple resources in a single request.

**Request Body:**
```json
{
  "operations": [
    {
      "method": "PATCH",
      "path": "/contacts/cont_abc123",
      "body": {"tags": ["vip"]}
    },
    {
      "method": "PATCH",
      "path": "/contacts/cont_def456",
      "body": {"tags": ["vip"]}
    },
    {
      "method": "DELETE",
      "path": "/contacts/cont_ghi789"
    }
  ],
  "return_details": true
}
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "method": "PATCH",
      "path": "/contacts/cont_abc123",
      "status": 200,
      "data": {"id": "cont_abc123", "tags": ["vip"], "updated_at": "..."}
    },
    {
      "method": "PATCH",
      "path": "/contacts/cont_def456",
      "status": 200,
      "data": {"id": "cont_def456", "tags": ["vip"], "updated_at": "..."}
    }
  ],
  "errors": [
    {
      "method": "DELETE",
      "path": "/contacts/cont_ghi789",
      "status": 404,
      "error": {
        "type": "https://api.amc.io/errors/not-found",
        "title": "Resource Not Found",
        "detail": "Contact cont_ghi789 not found"
      }
    }
  ],
  "meta": {
    "succeeded": 2,
    "failed": 1,
    "total": 3
  }
}
```

**Limits:**
- Maximum 100 operations per batch request
- Maximum payload size: 10 MB
- Batch operations are not atomic — partial success is expected
- Idempotency key applies to the entire batch request

### 3.5 Export

**Pattern:** `POST /api/v1/{module}/{resource}/export`

Exports data in the requested format. For large datasets, exports are processed asynchronously and the response includes a download URL.

**Request Body:**
```json
{
  "format": "csv",
  "fields": ["id", "first_name", "last_name", "email", "phone", "created_at"],
  "filter": {"field": "created_at", "op": "gte", "value": "2026-01-01"},
  "sort": "-created_at",
  "file_name": "contacts-export-2026-06-19"
}
```

**Supported Formats:**
| Format | `Content-Type` | File Extension |
|--------|----------------|----------------|
| CSV | `text/csv` | `.csv` |
| JSON | `application/json` | `.json` |
| XLSX | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` |

**Synchronous Response (≤ 100K rows):**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="contacts-export-2026-06-19.csv"
```

**Async Response (> 100K rows, 202 Accepted):**
```json
{
  "data": {
    "export_id": "exp_a1b2c3d4",
    "status": "processing",
    "download_url": null,
    "expires_at": null,
    "estimated_rows": 150000
  }
}
```

The client polls `GET /api/v1/exports/{export_id}` to check status. Once complete, the response includes a signed download URL valid for 1 hour.

### 3.6 Search

**Pattern:** `POST /api/v1/{module}/{resource}/search`

Full-text search across the resource using PostgreSQL full-text search or Elasticsearch (for AI-enhanced search).

**Request Body:**
```json
{
  "q": "Jane Doe",
  "fields": ["first_name", "last_name", "email", "notes"],
  "filter": {"field": "status", "op": "eq", "value": "active"},
  "limit": 20,
  "offset": 0,
  "sort": "-relevance",
  "highlight": true
}
```

**Response:**
```json
{
  "data": [
    {
      "id": "cont_xyz789",
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "score": 0.95,
      "highlights": {
        "first_name": "<mark>Jane</mark>",
        "last_name": "<mark>Doe</mark>",
        "email": "<mark>jane</mark>@example.com"
      }
    }
  ],
  "meta": {
    "total": 3,
    "offset": 0,
    "limit": 20,
    "has_more": false,
    "query_time_ms": 12
  }
}
```

---

## 4. Response Envelope

### 4.1 Success Response

All successful API responses follow a consistent envelope structure.

| Field | Type | Always Present | Description |
|-------|------|:---:|-------------|
| `data` | object/array | Yes | The primary response payload |
| `meta` | object | Lists | Pagination and metadata |
| `meta.page` | integer | Lists | Current page number |
| `meta.per_page` | integer | Lists | Items per page |
| `meta.total` | integer | Lists | Total matching results |
| `meta.has_more` | boolean | Lists | Whether more pages exist |
| `links` | object | Lists | Pagination links |
| `links.self` | string | Lists | Current page URL |
| `links.next` | string | Conditional | Next page URL |
| `links.prev` | string | Conditional | Previous page URL |

**Single Resource:**
```json
{
  "data": {
    "id": "cont_xyz789",
    "first_name": "Jane",
    "last_name": "Doe"
  }
}
```

**Resource List:**
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 1342,
    "has_more": true
  },
  "links": {
    "self": "/api/v1/crm/contacts?limit=50&sort=-created_at",
    "next": "/api/v1/crm/contacts?cursor=...&limit=50&sort=-created_at",
    "prev": null
  }
}
```

**Empty Result:**
```json
{
  "data": [],
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 0,
    "has_more": false
  },
  "links": {
    "self": "/api/v1/crm/contacts?limit=50",
    "next": null,
    "prev": null
  }
}
```

**Created Resource (201):**
```json
{
  "data": { ... }
}
```

### 4.2 Error Response

All error responses follow RFC 7807 Problem Details format.

| Field | Type | Always Present | Description |
|-------|------|:---:|-------------|
| `error.type` | URI | Yes | Problem type identifier |
| `error.title` | string | Yes | Short description |
| `error.status` | integer | Yes | HTTP status code |
| `error.detail` | string | Yes | Detailed explanation |
| `error.instance` | string | Yes | The specific endpoint |
| `error.trace_id` | string | Yes | Correlation ID for debugging |
| `error.errors` | array | Conditional | Field-level validation errors |

**400 Bad Request:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/bad-request",
    "title": "Bad Request",
    "status": 400,
    "detail": "The request could not be understood. Check syntax.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_abc123"
  }
}
```

**401 Unauthorized:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/authentication-error",
    "title": "Authentication Error",
    "status": 401,
    "detail": "Missing or invalid authentication token.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_def456"
  }
}
```

**403 Forbidden:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/authorization-error",
    "title": "Insufficient Permissions",
    "status": 403,
    "detail": "Your account does not have the required scope: crm:write",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_ghi789"
  }
}
```

**404 Not Found:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/not-found",
    "title": "Resource Not Found",
    "status": 404,
    "detail": "Contact with id 'cont_invalid' not found in this workspace.",
    "instance": "/api/v1/crm/contacts/cont_invalid",
    "trace_id": "tr_jkl012"
  }
}
```

**409 Conflict:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/conflict",
    "title": "Resource Conflict",
    "status": 409,
    "detail": "A contact with email 'jane@example.com' already exists.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_mno345"
  }
}
```

**422 Validation Error:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "2 validation errors in request body.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_pqr678",
    "errors": [
      {
        "field": "/email",
        "message": "Must be a valid email address",
        "code": "invalid_email"
      },
      {
        "field": "/phone",
        "message": "Must be in E.164 format (e.g., +14155551234)",
        "code": "invalid_format"
      }
    ]
  }
}
```

**429 Rate Limit:**
```json
{
  "error": {
    "type": "https://api.amc.io/errors/rate-limit-error",
    "title": "Rate Limit Exceeded",
    "status": 429,
    "detail": "API rate limit exceeded. Resets at 14:32:15 UTC.",
    "instance": "/api/v1/crm/contacts",
    "trace_id": "tr_stu901"
  }
}
```

### 4.3 Batch Response

```json
{
  "data": [
    {
      "method": "PATCH",
      "path": "/contacts/cont_abc123",
      "status": 200,
      "data": {"id": "cont_abc123", "tags": ["vip"]}
    }
  ],
  "errors": [
    {
      "method": "DELETE",
      "path": "/contacts/cont_ghi789",
      "status": 404,
      "error": {
        "type": "https://api.amc.io/errors/not-found",
        "title": "Resource Not Found",
        "detail": "Contact cont_ghi789 not found"
      }
    }
  ],
  "meta": {
    "succeeded": 2,
    "failed": 1,
    "total": 3
  }
}
```

---

## 5. REST API Endpoints

### 5.1 Auth Module

The Auth module handles identity management, authentication, session management, MFA, API keys, and password management.

#### 5.1.1 Register

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/register` | None | 5/min per IP | Create a new user account |

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss1",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Acme Inc",
  "workspace_name": "Acme Marketing",
  "accept_terms": true,
  "referral_code": null
}
```

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `email` | string (email) | Yes | Valid email address (max 255 chars) |
| `password` | string | Yes | Min 12 chars, 1 upper, 1 lower, 1 digit, 1 special |
| `first_name` | string | Yes | Max 100 chars |
| `last_name` | string | Yes | Max 100 chars |
| `company_name` | string | No | Company or organization name |
| `workspace_name` | string | Yes | Initial workspace name |
| `accept_terms` | boolean | Yes | Must be `true` |
| `referral_code` | string | No | Optional referral code |

**Response 201:**
```json
{
  "data": {
    "user": {
      "id": "usr_a1b2c3d4",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "company_name": "Acme Inc",
      "email_verified": false,
      "created_at": "2026-06-19T10:00:00Z"
    },
    "tenant": {
      "id": "ten_zk1ym2n3",
      "name": "Acme Inc",
      "slug": "acme-inc"
    },
    "workspace": {
      "id": "ws_x9y8z7w6",
      "name": "Acme Marketing",
      "slug": "acme-marketing"
    },
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "expires_in": 900
  }
}
```

**Response 409:** Email already registered.

**Response 422:** Validation errors for password complexity, invalid email format, missing required fields.

#### 5.1.2 Login

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/login` | None | 10/min per IP, 5/min per email | Authenticate and receive JWT tokens |

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss1",
  "mfa_code": null,
  "workspace_id": null,
  "remember_me": false
}
```

**Response 200:**
```json
{
  "data": {
    "user": {
      "id": "usr_a1b2c3d4",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "avatar_url": "https://cdn.amc.io/avatars/usr_a1b2c3d4.jpg",
      "mfa_enabled": false
    },
    "workspace": {
      "id": "ws_x9y8z7w6",
      "name": "Acme Marketing",
      "slug": "acme-marketing",
      "role": "admin"
    },
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "expires_in": 900
  }
}
```

**Response 401:** Invalid credentials.

**Response 429:** Rate limit exceeded.

#### 5.1.3 Refresh Token

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/refresh` | None (uses refresh token in body) | 20/min per user | Obtain a new access token using a refresh token |

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi...",
  "workspace_id": null
}
```

**Response 200:**
```json
{
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "expires_in": 900,
    "token_type": "Bearer"
  }
}
```

#### 5.1.4 Logout

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/logout` | Bearer | 30/min per user | Invalidate the current refresh token |

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOi...",
  "all_sessions": false
}
```

**Response 200:**
```json
{
  "data": {
    "message": "Successfully logged out.",
    "sessions_invalidated": 1
  }
}
```

#### 5.1.5 MFA Setup

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/mfa/setup` | Bearer | 3/min per user | Initialize MFA enrollment (generates TOTP secret) |

**Response 200:**
```json
{
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code_url": "otpauth://totp/AMC:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=AMC",
    "backup_codes": [
      "ABCD-EFGH-IJKL-MNOP",
      "QRST-UVWX-YZAB-CDEF",
      "GHIJ-KLMN-OPQR-STUV",
      "WXYZ-ABCD-EFGH-IJKL",
      "MNOP-QRST-UVWX-YZAB",
      "CDEF-GHIJ-KLMN-OPQR",
      "STUV-WXYZ-ABCD-EFGH",
      "IJKL-MNOP-QRST-UVWX"
    ]
  }
}
```

#### 5.1.6 MFA Verify

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/mfa/verify` | Bearer | 5/min per user | Verify MFA setup by providing a valid TOTP code |

**Request Body:**
```json
{
  "code": "123456"
}
```

**Response 200:**
```json
{
  "data": {
    "mfa_enabled": true,
    "message": "MFA has been successfully enabled."
  }
}
```

#### 5.1.7 MFA Disable

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/mfa/disable` | Bearer | 3/min per user | Disable MFA (requires current password) |

**Request Body:**
```json
{
  "password": "SecureP@ss1",
  "code": "123456"
}
```

**Response 200:**
```json
{
  "data": {
    "mfa_enabled": false,
    "message": "MFA has been disabled."
  }
}
```

#### 5.1.8 OTP Generate

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/otp/generate` | None | 2/min per email | Generate and send a one-time password for passwordless login |

**Request Body:**
```json
{
  "email": "user@example.com",
  "purpose": "login"
}
```

**Response 200:**
```json
{
  "data": {
    "message": "If an account exists with this email, a one-time code has been sent.",
    "expires_in": 300
  }
}
```

#### 5.1.9 List Sessions

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/auth/sessions` | Bearer | 30/min per user | List all active sessions for the authenticated user |

**Response 200:**
```json
{
  "data": [
    {
      "id": "sess_a1b2c3d4",
      "ip_address": "203.0.113.42",
      "user_agent": "Mozilla/5.0 ...",
      "device_name": "Chrome on Windows",
      "location": "San Francisco, US",
      "last_active_at": "2026-06-19T09:55:00Z",
      "created_at": "2026-06-19T08:00:00Z",
      "is_current": true
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 3, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.1.10 Delete Session

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/auth/sessions/{id}` | Bearer | 30/min per user | Terminate a specific session |

**Response 200:**
```json
{
  "data": {
    "id": "sess_a1b2c3d4",
    "status": "terminated"
  }
}
```

#### 5.1.11 Password Reset Request

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/password/reset` | None | 2/min per email | Request a password reset email |

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response 200:**
```json
{
  "data": {
    "message": "If an account exists with this email, password reset instructions have been sent.",
    "expires_in": 3600
  }
}
```

#### 5.1.12 Password Change

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/password/change` | Bearer | 5/min per user | Change password (requires current password) |

**Request Body:**
```json
{
  "current_password": "OldP@ss1",
  "new_password": "NewSecureP@ss1"
}
```

**Response 200:**
```json
{
  "data": {
    "message": "Password changed successfully. All other sessions have been terminated."
  }
}
```

#### 5.1.13 Get Current User

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/auth/me` | Bearer | 60/min per user | Get the currently authenticated user's profile |

**Response 200:**
```json
{
  "data": {
    "id": "usr_a1b2c3d4",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "avatar_url": "https://cdn.amc.io/avatars/usr_a1b2c3d4.jpg",
    "company_name": "Acme Inc",
    "email_verified": true,
    "mfa_enabled": false,
    "roles": ["admin"],
    "workspaces": [
      {
        "id": "ws_x9y8z7w6",
        "name": "Acme Marketing",
        "slug": "acme-marketing",
        "role": "admin",
        "is_default": true
      }
    ],
    "created_at": "2026-01-15T08:00:00Z",
    "updated_at": "2026-06-19T09:00:00Z"
  }
}
```

#### 5.1.14 Update Current User

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/auth/me` | Bearer | 10/min per user | Update the current user's profile |

**Request Body:**
```json
{
  "first_name": "Jonathan",
  "last_name": "Doe",
  "avatar_url": "https://cdn.amc.io/uploads/new-avatar.jpg"
}
```

**Response 200:** Full updated user object.

#### 5.1.15 Create API Key

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/auth/api-keys` | Bearer | 5/min per user | Generate a new API key |

**Request Body:**
```json
{
  "name": "CI/CD Pipeline Key",
  "scopes": ["crm:read", "campaigns:read"],
  "expires_at": "2027-06-19T00:00:00Z",
  "workspace_id": "ws_x9y8z7w6"
}
```

**Response 201:**
```json
{
  "data": {
    "id": "api_a1b2c3d4",
    "name": "CI/CD Pipeline Key",
    "key": "amc_live_abc123def456...",
    "prefix": "amc_live_",
    "scopes": ["crm:read", "campaigns:read"],
    "workspace_id": "ws_x9y8z7w6",
    "created_at": "2026-06-19T10:00:00Z",
    "expires_at": "2027-06-19T00:00:00Z",
    "last_used_at": null
  }
}
```

#### 5.1.16 List API Keys

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/auth/api-keys` | Bearer | 30/min per user | List all API keys for the authenticated user |

**Response 200:**
```json
{
  "data": [
    {
      "id": "api_a1b2c3d4",
      "name": "CI/CD Pipeline Key",
      "prefix": "amc_live_",
      "scopes": ["crm:read", "campaigns:read"],
      "workspace_id": "ws_x9y8z7w6",
      "created_at": "2026-06-19T10:00:00Z",
      "expires_at": "2027-06-19T00:00:00Z",
      "last_used_at": "2026-06-19T11:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 2, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.1.17 Delete API Key

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/auth/api-keys/{id}` | Bearer | 30/min per user | Revoke an API key |

**Response 200:**
```json
{
  "data": {
    "id": "api_a1b2c3d4",
    "status": "revoked"
  }
}
```

---

### 5.2 Tenant & Workspace Module

The Tenant & Workspace module manages organizational boundaries and user membership.

#### 5.2.1 Get Tenant

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/tenants` | Bearer | 30/min per user | Get the current tenant's details |

**Response 200:**
```json
{
  "data": {
    "id": "ten_zk1ym2n3",
    "name": "Acme Inc",
    "slug": "acme-inc",
    "plan": "business",
    "status": "active",
    "logo_url": "https://cdn.amc.io/tenants/ten_zk1ym2n3/logo.png",
    "settings": {
      "max_workspaces": 50,
      "max_users_per_workspace": 100,
      "ai_credits_per_month": 10000,
      "storage_gb": 500
    },
    "created_at": "2026-01-15T08:00:00Z",
    "updated_at": "2026-06-19T09:00:00Z"
  }
}
```

#### 5.2.2 Update Tenant

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/tenants/{id}` | Bearer (admin) | 10/min per user | Update tenant details |

**Request Body:**
```json
{
  "name": "Acme Corporation",
  "logo_url": "https://cdn.amc.io/tenants/ten_zk1ym2n3/new-logo.png",
  "settings": {
    "default_timezone": "America/New_York",
    "default_currency": "USD"
  }
}
```

**Response 200:** Updated tenant object.

#### 5.2.3 List Workspaces

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/workspaces` | Bearer | 30/min per user | List all workspaces accessible to the current user |

**Response 200:**
```json
{
  "data": [
    {
      "id": "ws_x9y8z7w6",
      "name": "Acme Marketing",
      "slug": "acme-marketing",
      "description": "Main marketing workspace",
      "role": "admin",
      "member_count": 12,
      "created_at": "2026-01-15T08:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 3, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.2.4 Create Workspace

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/workspaces` | Bearer | 10/min per user | Create a new workspace within the current tenant |

**Request Body:**
```json
{
  "name": "Product Launch 2026",
  "slug": "product-launch-2026",
  "description": "Workspace for the Q3 product launch campaign",
  "timezone": "America/New_York",
  "currency": "USD"
}
```

**Response 201:**
```json
{
  "data": {
    "id": "ws_abc123",
    "name": "Product Launch 2026",
    "slug": "product-launch-2026",
    "description": "Workspace for the Q3 product launch campaign",
    "role": "admin",
    "member_count": 1,
    "created_at": "2026-06-19T10:00:00Z"
  }
}
```

#### 5.2.5 Get Workspace

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/workspaces/{id}` | Bearer | 30/min per user | Get workspace details |

**Response 200:**
```json
{
  "data": {
    "id": "ws_x9y8z7w6",
    "name": "Acme Marketing",
    "slug": "acme-marketing",
    "description": "Main marketing workspace",
    "timezone": "America/New_York",
    "currency": "USD",
    "role": "admin",
    "member_count": 12,
    "settings": {
      "default_campaign_settings": {
        "sender_name": "Acme Marketing",
        "sender_email": "marketing@acme.com"
      },
      "ai_config": {
        "brand_voice_id": null,
        "default_tone": "professional"
      }
    },
    "created_at": "2026-01-15T08:00:00Z",
    "updated_at": "2026-06-19T09:00:00Z"
  }
}
```

#### 5.2.6 Update Workspace

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/workspaces/{id}` | Bearer (workspace_admin) | 10/min per user | Update workspace settings |

**Request Body:** Partial workspace object.

**Response 200:** Updated workspace object.

#### 5.2.7 Delete Workspace

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/workspaces/{id}` | Bearer (workspace_admin) | 3/min per user | Soft-delete a workspace |

**Response 200:**
```json
{
  "data": {
    "id": "ws_x9y8z7w6",
    "status": "deleted",
    "deleted_at": "2026-06-19T11:00:00Z"
  }
}
```

#### 5.2.8 Invite Member

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/workspaces/{id}/invite` | Bearer (workspace_admin) | 20/min per workspace | Invite a user to the workspace |

**Request Body:**
```json
{
  "email": "colleague@example.com",
  "role": "member",
  "message": "Join our marketing team!"
}
```

**Response 200:**
```json
{
  "data": {
    "invitation_id": "inv_a1b2c3d4",
    "email": "colleague@example.com",
    "role": "member",
    "status": "pending",
    "expires_at": "2026-07-19T11:00:00Z",
    "created_at": "2026-06-19T11:00:00Z"
  }
}
```

#### 5.2.9 Remove Member

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/workspaces/{id}/members/{userId}` | Bearer (workspace_admin) | 10/min per workspace | Remove a user from the workspace |

**Response 200:**
```json
{
  "data": {
    "user_id": "usr_def456",
    "workspace_id": "ws_x9y8z7w6",
    "status": "removed"
  }
}
```

---

### 5.3 CRM Module

The CRM module manages contacts, deals, pipelines, activities, and tasks.

#### 5.3.1 List Contacts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/contacts` | Bearer | 100/min | List contacts with filtering, sorting, and pagination |

**Filterable Fields:** `status`, `source`, `tags`, `owner_id`, `created_at`, `updated_at`, `email`, `phone`, `company`, `city`, `country`

**Include Options:** `deals`, `activities`, `tasks`, `owner`

**Response 200:**
```json
{
  "data": [
    {
      "id": "cont_xyz789",
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "phone": "+14155551234",
      "company": "Acme Corp",
      "title": "Marketing Director",
      "status": "active",
      "source": "website",
      "tags": ["lead", "webinar-2026"],
      "owner_id": "usr_a1b2c3d4",
      "city": "San Francisco",
      "country": "US",
      "created_at": "2026-06-19T10:00:00Z",
      "updated_at": "2026-06-19T10:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 1342, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.3.2 Create Contact

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts` | Bearer | 50/min | Create a new contact |

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "phone": "+14155551234",
  "company": "Acme Corp",
  "title": "Marketing Director",
  "source": "website",
  "tags": ["lead", "webinar-2026"],
  "address_line1": "123 Market St",
  "address_line2": "Suite 400",
  "city": "San Francisco",
  "state": "CA",
  "postal_code": "94105",
  "country": "US",
  "notes": "Met at Webinar 2026",
  "custom_fields": {
    "industry": "Technology",
    "employee_count": "500-1000"
  }
}
```

**Response 201:** Full contact object.

#### 5.3.3 Get Contact

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/contacts/{id}` | Bearer | 100/min | Get a specific contact by ID |

**Response 200:** Full contact object with included relations.

**Response 404:** Contact not found.

#### 5.3.4 Update Contact

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/crm/contacts/{id}` | Bearer | 50/min | Partially update a contact |

**Response 200:** Full updated contact object.

#### 5.3.5 Delete Contact

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/crm/contacts/{id}` | Bearer | 20/min | Soft-delete a contact |

**Response 200:** Contact with `deleted_at` timestamp.

#### 5.3.6 Restore Contact

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts/{id}/restore` | Bearer | 10/min | Restore a soft-deleted contact |

**Response 200:** Restored contact with `restored_at` timestamp.

#### 5.3.7 Import Contacts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts/import` | Bearer | 5/min per workspace | Import contacts from CSV/JSON/XLSX file |

**Request Body:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `file` | file | Yes | CSV, JSON, or XLSX file (max 50 MB) |
| `dedup_field` | string | No | Field to use for deduplication (`email`, `phone`, or null) |
| `create_tags` | string | No | Comma-separated tags to apply to all imported contacts |
| `update_existing` | boolean | No | Update existing contacts found by dedup field (default: false) |

**Response 202 (Async for large imports):**
```json
{
  "data": {
    "import_id": "imp_a1b2c3d4",
    "status": "processing",
    "total_rows": 15000,
    "created_rows": 0,
    "updated_rows": 0,
    "failed_rows": 0,
    "errors_url": null
  }
}
```

#### 5.3.8 Export Contacts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts/export` | Bearer | 5/min per workspace | Export contacts to CSV/JSON/XLSX |

**Response 200 (sync) or 202 (async):** See Section 3.5.

#### 5.3.9 Search Contacts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts/search` | Bearer | 30/min | Full-text search across contacts |

**Response 200:** Search results with scores and highlights.

#### 5.3.10 Batch Contacts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/contacts/batch` | Bearer | 10/min | Batch operations on contacts |

#### 5.3.11 List Deals

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/deals` | Bearer | 100/min | List deals with filtering, sorting, and pagination |

**Filterable Fields:** `status`, `stage_id`, `pipeline_id`, `owner_id`, `contact_id`, `value`, `created_at`, `expected_close_date`

**Response 200:**
```json
{
  "data": [
    {
      "id": "deal_a1b2c3d4",
      "title": "Enterprise License - Acme Corp",
      "value": 50000,
      "currency": "USD",
      "status": "open",
      "stage_id": "stag_abc123",
      "pipeline_id": "pipe_def456",
      "contact_id": "cont_xyz789",
      "owner_id": "usr_a1b2c3d4",
      "probability": 60,
      "expected_close_date": "2026-09-30",
      "notes": "Follow up after technical demo",
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 45, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.3.12 Create Deal

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/deals` | Bearer | 50/min | Create a new deal |

**Request Body:** Deal object with title, value, pipeline_id, stage_id, contact_id.

**Response 201:** Full deal object.

#### 5.3.13 Update Deal

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/crm/deals/{id}` | Bearer | 50/min | Partially update a deal |

#### 5.3.14 Update Deal Stage

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/crm/deals/{id}/stage` | Bearer | 50/min | Move a deal to a different pipeline stage |

**Request Body:**
```json
{
  "stage_id": "stag_xyz789",
  "probability": 80
}
```

**Response 200:**
```json
{
  "data": {
    "id": "deal_a1b2c3d4",
    "stage_id": "stag_xyz789",
    "probability": 80,
    "stage_changed_at": "2026-06-19T11:00:00Z",
    "previous_stage_id": "stag_abc123",
    "time_in_previous_stage_hours": 72
  }
}
```

#### 5.3.15 List Pipelines

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/pipelines` | Bearer | 100/min | List all pipelines with their stages |

**Response 200:**
```json
{
  "data": [
    {
      "id": "pipe_def456",
      "name": "Sales Pipeline",
      "description": "Standard B2B sales process",
      "is_default": true,
      "stages": [
        {"id": "stag_abc123", "name": "Lead Qualification", "order": 0, "probability_default": 10, "color": "#FF6B6B"},
        {"id": "stag_def456", "name": "Discovery", "order": 1, "probability_default": 25, "color": "#FFA94D"},
        {"id": "stag_ghi789", "name": "Proposal", "order": 2, "probability_default": 50, "color": "#FFD43B"},
        {"id": "stag_jkl012", "name": "Negotiation", "order": 3, "probability_default": 75, "color": "#69DB7C"},
        {"id": "stag_mno345", "name": "Closed Won", "order": 4, "probability_default": 100, "color": "#20C997", "is_closing_stage": true},
        {"id": "stag_pqr678", "name": "Closed Lost", "order": 5, "probability_default": 0, "color": "#CED4DA", "is_closing_stage": true}
      ],
      "created_at": "2026-01-15T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 2, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.3.16 Create Pipeline

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/pipelines` | Bearer | 10/min | Create a new pipeline with stages |

**Response 201:** Full pipeline object with stages.

#### 5.3.17 Update Pipeline

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/crm/pipelines/{id}` | Bearer | 10/min | Update pipeline name, description, or stages |

#### 5.3.18 List Activities

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/activities` | Bearer | 100/min | List activities (calls, emails, meetings, notes) |

**Filterable Fields:** `type`, `contact_id`, `deal_id`, `owner_id`, `created_at`, `scheduled_at`

**Response 200:**
```json
{
  "data": [
    {
      "id": "acti_a1b2c3d4",
      "type": "call",
      "subject": "Discovery call with Jane Doe",
      "description": "Discussed enterprise requirements and timeline.",
      "contact_id": "cont_xyz789",
      "deal_id": "deal_a1b2c3d4",
      "owner_id": "usr_a1b2c3d4",
      "scheduled_at": "2026-06-18T14:00:00Z",
      "completed_at": "2026-06-18T14:45:00Z",
      "duration_minutes": 45,
      "created_at": "2026-06-18T10:00:00Z",
      "updated_at": "2026-06-18T15:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 230, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.3.19 Create Activity

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/activities` | Bearer | 50/min | Log a new activity |

**Response 201:** Full activity object.

#### 5.3.20 List Tasks

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/crm/tasks` | Bearer | 100/min | List CRM tasks |

**Filterable Fields:** `status`, `priority`, `assignee_id`, `contact_id`, `deal_id`, `due_at`, `completed_at`

**Response 200:**
```json
{
  "data": [
    {
      "id": "task_a1b2c3d4",
      "subject": "Send proposal to Acme Corp",
      "description": "Prepare and send the enterprise proposal document.",
      "status": "pending",
      "priority": "high",
      "assignee_id": "usr_def456",
      "contact_id": "cont_xyz789",
      "deal_id": "deal_a1b2c3d4",
      "due_at": "2026-06-22T17:00:00Z",
      "completed_at": null,
      "created_at": "2026-06-19T08:00:00Z",
      "updated_at": "2026-06-19T08:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 15, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.3.21 Create Task

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/crm/tasks` | Bearer | 50/min | Create a new task |

**Response 201:** Full task object.

#### 5.3.22 Update Task

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/crm/tasks/{id}` | Bearer | 50/min | Update a task (e.g., mark complete) |

**Request Body:**
```json
{
  "status": "completed",
  "completed_at": "2026-06-19T12:00:00Z"
}
```

**Response 200:** Updated task object.

---

### 5.4 Marketing Module

The Marketing module manages campaigns, email templates, landing pages, and segments.

#### 5.4.1 List Campaigns

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/campaigns` | Bearer | 100/min | List marketing campaigns |

**Filterable Fields:** `status`, `type`, `created_at`, `scheduled_at`

**Response 200:**
```json
{
  "data": [
    {
      "id": "camp_a1b2c3d4",
      "name": "Q3 Welcome Series",
      "description": "Automated welcome email sequence for new subscribers",
      "type": "email",
      "status": "active",
      "scheduled_at": "2026-07-01T08:00:00Z",
      "stats": {
        "recipients": 15000,
        "sent": 0,
        "opened": 0,
        "clicked": 0,
        "bounced": 0,
        "converted": 0
      },
      "created_at": "2026-06-10T10:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 12, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.4.2 Create Campaign

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/campaigns` | Bearer | 20/min | Create a new campaign |

**Request Body:**
```json
{
  "name": "Q3 Welcome Series",
  "description": "Automated welcome email sequence",
  "type": "email",
  "segment_id": "seg_abc123",
  "template_id": "tpl_def456",
  "sender_name": "Acme Marketing",
  "sender_email": "marketing@acme.com",
  "subject": "Welcome to Acme!",
  "scheduled_at": "2026-07-01T08:00:00Z",
  "tags": ["welcome", "onboarding"],
  "utm_params": {
    "source": "email",
    "medium": "email",
    "campaign": "q3-welcome-series"
  }
}
```

**Response 201:** Full campaign object.

#### 5.4.3 Get Campaign

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/campaigns/{id}` | Bearer | 100/min | Get campaign details with statistics |

#### 5.4.4 Update Campaign

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/marketing/campaigns/{id}` | Bearer | 20/min | Update campaign (only when status is `draft` or `scheduled`) |

#### 5.4.5 Send Campaign

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/campaigns/{id}/send` | Bearer | 10/min | Send or schedule a campaign |

**Request Body:**
```json
{
  "send_at": null,
  "test_mode": false,
  "test_emails": ["test@acme.com"]
}
```

**Response 200:**
```json
{
  "data": {
    "id": "camp_a1b2c3d4",
    "status": "sending",
    "sent_at": "2026-07-01T08:00:00Z",
    "estimated_recipients": 15000
  }
}
```

#### 5.4.6 Duplicate Campaign

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/campaigns/{id}/duplicate` | Bearer | 20/min | Create a copy of an existing campaign |

**Request Body:**
```json
{
  "name": "Q3 Welcome Series (Copy)",
  "include_stats": false
}
```

**Response 201:** New campaign object with `draft` status.

#### 5.4.7 List Email Templates

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/templates/email` | Bearer | 100/min | List email templates |

**Response 200:**
```json
{
  "data": [
    {
      "id": "tpl_def456",
      "name": "Welcome Email",
      "description": "Standard welcome template",
      "category": "onboarding",
      "subject": "Welcome to {{company_name}}!",
      "variables": ["company_name", "user_name", "activation_link"],
      "status": "published",
      "created_at": "2026-01-15T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 8, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.4.8 Create Email Template

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/templates/email` | Bearer | 20/min | Create a new email template |

**Response 201:** Full template object.

#### 5.4.9 Get Email Template

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/templates/email/{id}` | Bearer | 100/min | Get a specific email template |

#### 5.4.10 Update Email Template

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/marketing/templates/email/{id}` | Bearer | 20/min | Update an email template |

#### 5.4.11 List Landing Pages

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/landing-pages` | Bearer | 100/min | List landing pages |

**Response 200:**
```json
{
  "data": [
    {
      "id": "lp_a1b2c3d4",
      "title": "Q3 Product Launch",
      "slug": "q3-product-launch",
      "status": "published",
      "url": "https://lp.amc.io/acme-marketing/q3-product-launch",
      "stats": {"views": 1234, "conversions": 89, "conversion_rate": 7.2},
      "created_at": "2026-06-10T10:00:00Z",
      "updated_at": "2026-06-15T08:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 5, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.4.12 Create Landing Page

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/landing-pages` | Bearer | 20/min | Create a new landing page |

#### 5.4.13 List Segments

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketing/segments` | Bearer | 100/min | List audience segments |

**Response 200:**
```json
{
  "data": [
    {
      "id": "seg_abc123",
      "name": "Active Subscribers",
      "description": "Users who have engaged in the last 90 days",
      "type": "dynamic",
      "criteria": {
        "and": [
          {"field": "status", "op": "eq", "value": "active"},
          {"field": "last_engagement_at", "op": "gte", "value": "{{now-90d}}"}
        ]
      },
      "estimated_count": 12500,
      "created_at": "2026-01-15T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 10, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.4.14 Create Segment

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketing/segments` | Bearer | 20/min | Create a new audience segment |

---

### 5.5 AI Suite Module

The AI Suite provides content generation capabilities across multiple channels.

#### 5.5.1 Generate Content (Generic)

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate` | Bearer | 20/min | Generate content with AI |

**Request Body:**
```json
{
  "prompt": "Write a professional email introducing our new product",
  "type": "auto",
  "tone": "professional",
  "brand_voice_id": "bv_a1b2c3d4",
  "temperature": 0.7,
  "max_tokens": 500,
  "language": "en"
}
```

**Response 200:**
```json
{
  "data": {
    "id": "gen_a1b2c3d4",
    "content": "Dear [Name],\n\nI am excited to introduce...",
    "type": "email",
    "model": "gpt-4o",
    "tokens_used": 145,
    "created_at": "2026-06-19T10:00:00Z"
  }
}
```

#### 5.5.2 Generate Blog Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate/blog` | Bearer | 10/min | Generate a blog post with structured output |

**Response 200:** Blog post with title, outline, SEO meta, and content.

#### 5.5.3 Generate Email

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate/email` | Bearer | 20/min | Generate email content (subject + body) |

**Response 200:** Email with subject, preheader, HTML body, plaintext, and variants.

#### 5.5.4 Generate Social Media Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate/social` | Bearer | 30/min | Generate social media content |

**Response 200:** Social post with content, hashtags, and platform-specific formatting.

#### 5.5.5 Generate Ad Copy

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate/ad` | Bearer | 20/min | Generate advertising copy for multiple platforms |

**Response 200:** Ad copy with headlines, descriptions, CTAs, and platform-specific constraints.

#### 5.5.6 Generate Image Prompt

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/generate/image-prompt` | Bearer | 30/min | Generate optimized prompts for image generation models |

**Response 200:** Image prompt with negative prompt and model-specific params.

#### 5.5.7 List Generations

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/ai/generations` | Bearer | 60/min | List AI generation history |

#### 5.5.8 Get Generation

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/ai/generations/{id}` | Bearer | 60/min | Get details of a specific generation |

#### 5.5.9 Get AI Usage

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/ai/usage` | Bearer | 30/min | Get AI token usage statistics |

**Response 200:**
```json
{
  "data": {
    "current_period": {
      "start": "2026-06-01T00:00:00Z",
      "end": "2026-07-01T00:00:00Z"
    },
    "tokens_used": 145000,
    "tokens_limit": 500000,
    "tokens_remaining": 355000,
    "usage_percentage": 29,
    "by_type": {
      "email": {"tokens": 45000, "count": 320},
      "blog": {"tokens": 60000, "count": 40},
      "social": {"tokens": 25000, "count": 500},
      "ad": {"tokens": 15000, "count": 120}
    }
  }
}
```

#### 5.5.10 Create Brand Voice

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/ai/brand-voice` | Bearer | 5/min | Create a brand voice profile for AI generation |

**Response 201:** Full brand voice object.

#### 5.5.11 List Brand Voices

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/ai/brand-voices` | Bearer | 60/min | List all brand voice profiles |

---

### 5.6 SEO Module

The SEO module provides keyword research, SERP analysis, site audits, backlink analysis, and schema generation.

#### 5.6.1 List Keywords

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/keywords` | Bearer | 60/min | List tracked keywords with SEO metrics |

**Response 200:**
```json
{
  "data": [
    {
      "id": "kw_a1b2c3d4",
      "keyword": "AI marketing platform",
      "search_volume": 12000,
      "difficulty": 65,
      "cpc": 4.50,
      "current_position": 8,
      "best_position": 5,
      "last_checked_at": "2026-06-19T06:00:00Z",
      "serp_features": ["featured_snippet", "people_also_ask"],
      "intent": "commercial",
      "tags": ["target", "high-priority"],
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-06-19T06:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 145, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.6.2 Add Keywords

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/seo/keywords` | Bearer | 20/min | Add keywords to track |

**Response 201:**
```json
{
  "data": [
    {"id": "kw_def456", "keyword": "AI marketing automation", "status": "tracking"},
    {"id": "kw_ghi789", "keyword": "predictive analytics", "status": "tracking"}
  ],
  "meta": {"added": 2, "skipped": 0}
}
```

#### 5.6.3 Get SERP Data

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/keywords/{id}/serp` | Bearer | 30/min | Get SERP data for a keyword |

**Response 200:** SERP results with featured snippets, people also ask, and related searches.

#### 5.6.4 Get Competitors

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/keywords/{id}/competitors` | Bearer | 30/min | Get competitor analysis for a keyword |

**Response 200:** Competitor list with domain authority, backlinks, positions, and opportunity analysis.

#### 5.6.5 Run SEO Audit

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/seo/audit` | Bearer | 5/min per domain | Run a new SEO audit on a domain |

**Request Body:**
```json
{
  "url": "https://acme.com",
  "pages_limit": 100,
  "check_mobile": true,
  "check_speed": true,
  "check_accessibility": true,
  "check_schema": true
}
```

**Response 202:** Audit ID and estimated completion time.

#### 5.6.6 Get Audit Results

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/audits/{id}` | Bearer | 30/min | Get SEO audit results |

**Response 200:**
```json
{
  "data": {
    "id": "aud_a1b2c3d4",
    "url": "https://acme.com",
    "status": "completed",
    "score": 82,
    "crawled_pages": 85,
    "summary": {
      "total_issues": 24,
      "critical": 2,
      "warnings": 8,
      "info": 14
    },
    "categories": {
      "meta_tags": {"score": 90},
      "content": {"score": 85},
      "mobile": {"score": 95},
      "speed": {"score": 70},
      "schema": {"score": 60}
    },
    "issues": [
      {
        "severity": "critical",
        "category": "meta_tags",
        "title": "Missing meta description",
        "description": "15 pages are missing meta descriptions",
        "recommendation": "Add unique meta descriptions to each page"
      }
    ],
    "created_at": "2026-06-19T10:00:00Z",
    "completed_at": "2026-06-19T10:12:00Z"
  }
}
```

#### 5.6.7 Get Backlinks

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/backlinks` | Bearer | 30/min | Get backlink data |

#### 5.6.8 Get SEO Suggestions

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/seo/suggestions` | Bearer | 20/min | Get AI-powered SEO improvement suggestions |

#### 5.6.9 Generate Schema Markup

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/seo/schema/generate` | Bearer | 10/min | Generate structured data (JSON-LD) markup |

**Request Body:**
```json
{
  "type": "Article",
  "data": {
    "headline": "The Future of AI in Marketing",
    "author": "Acme Marketing",
    "datePublished": "2026-06-19"
  }
}
```

**Response 200:**
```json
{
  "data": {
    "schema_type": "Article",
    "jsonld": {
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "The Future of AI in Marketing",
      "author": {"@type": "Organization", "name": "Acme Marketing"},
      "datePublished": "2026-06-19"
    },
    "validation": {"valid": true, "warnings": [], "errors": []}
  }
}
```

#### 5.6.10 Generate Meta Tags

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/seo/meta/generate` | Bearer | 20/min | Generate SEO-optimized meta titles and descriptions |

**Response 200:** Title, description, and variants with character counts.

---

### 5.7 Social Module

The Social module manages social media accounts, content calendar, posting, and analytics.

#### 5.7.1 List Social Accounts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/social/accounts` | Bearer | 60/min | List connected social media accounts |

**Response 200:**
```json
{
  "data": [
    {
      "id": "soc_a1b2c3d4",
      "platform": "linkedin",
      "account_name": "Acme Marketing",
      "avatar_url": "https://cdn.amc.io/social/linkedin_avatar.png",
      "status": "connected",
      "connected_at": "2026-01-15T08:00:00Z",
      "last_sync_at": "2026-06-19T06:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 4, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.7.2 Connect Social Account

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/social/accounts` | Bearer | 5/min | Connect a social media account via OAuth |

**Response 201:** Full social account object.

#### 5.7.3 Disconnect Account

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/social/accounts/{id}` | Bearer | 10/min | Disconnect a social media account |

#### 5.7.4 Get Social Calendar

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/social/calendar` | Bearer | 30/min | Get the social media content calendar |

**Query Parameters:** `start_date`, `end_date`, `platform`, `status`

**Response 200:** Posts grouped by date with aggregate counts.

#### 5.7.5 Create Social Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/social/posts` | Bearer | 30/min | Create a new social media post |

**Request Body:**
```json
{
  "platform": "linkedin",
  "account_id": "soc_a1b2c3d4",
  "content": "Excited to announce our new AI-powered analytics suite!",
  "media_urls": ["https://cdn.amc.io/social/post-image-1.jpg"],
  "scheduled_at": "2026-06-20T09:00:00Z",
  "tags": ["product-launch", "ai"]
}
```

**Response 201:** Full social post object.

#### 5.7.6 Get Social Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/social/posts/{id}` | Bearer | 60/min | Get a specific social post |

#### 5.7.7 Update Social Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/social/posts/{id}` | Bearer | 30/min | Update a social post (draft/scheduled only) |

#### 5.7.8 Delete Social Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/social/posts/{id}` | Bearer | 20/min | Delete a social post |

#### 5.7.9 Publish Social Post

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/social/posts/{id}/publish` | Bearer | 20/min | Publish a social post immediately or schedule it |

**Response 200:**
```json
{
  "data": {
    "id": "sp_a1b2c3d4",
    "status": "publishing",
    "published_at": "2026-06-19T11:00:00Z"
  }
}
```

#### 5.7.10 Get Social Analytics

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/social/analytics` | Bearer | 20/min | Get social media analytics |

**Response 200:**
```json
{
  "data": {
    "summary": {
      "total_posts": 45,
      "total_impressions": 125000,
      "total_engagement": 8500,
      "engagement_rate": 6.8,
      "total_clicks": 3200,
      "net_followers": 330
    },
    "by_platform": {
      "linkedin": {"posts": 15, "impressions": 45000, "engagement": 3200},
      "twitter": {"posts": 20, "impressions": 55000, "engagement": 3800}
    },
    "top_posts": [
      {
        "id": "sp_a1b2c3d4",
        "content": "Excited to announce...",
        "impressions": 8500,
        "engagement": 1200,
        "engagement_rate": 14.1
      }
    ]
  }
}
```

#### 5.7.11 Generate Hashtags

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/social/hashtags/generate` | Bearer | 20/min | Generate trending/relevant hashtags |

**Response 200:** Hashtag recommendations with volume and trend data.

---

### 5.8 Automation Module

The Automation module provides workflow automation powered by n8n.

#### 5.8.1 List Workflows

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/automation/workflows` | Bearer | 60/min | List automation workflows |

**Response 200:**
```json
{
  "data": [
    {
      "id": "wf_a1b2c3d4",
      "name": "Welcome Email Sequence",
      "description": "Send welcome emails when new contacts are added",
      "status": "active",
      "trigger_type": "event",
      "last_executed_at": "2026-06-19T09:55:00Z",
      "last_execution_status": "success",
      "execution_count": 1250,
      "error_count": 3,
      "created_at": "2026-02-01T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 8, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.8.2 Create Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/automation/workflows` | Bearer | 10/min | Create a new workflow |

**Response 201:** Full workflow object with steps and configuration.

#### 5.8.3 Get Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/automation/workflows/{id}` | Bearer | 60/min | Get workflow details |

#### 5.8.4 Update Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/automation/workflows/{id}` | Bearer | 10/min | Update workflow configuration |

#### 5.8.5 Delete Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/automation/workflows/{id}` | Bearer | 10/min | Delete a workflow |

#### 5.8.6 Activate Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/automation/workflows/{id}/activate` | Bearer | 10/min | Activate a workflow |

#### 5.8.7 Deactivate Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/automation/workflows/{id}/deactivate` | Bearer | 10/min | Deactivate a workflow |

#### 5.8.8 List Workflow Executions

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/automation/workflows/{id}/executions` | Bearer | 30/min | Get execution history for a workflow |

**Response 200:**
```json
{
  "data": [
    {
      "id": "exec_a1b2c3d4",
      "workflow_id": "wf_a1b2c3d4",
      "status": "success",
      "started_at": "2026-06-19T09:55:00Z",
      "completed_at": "2026-06-19T09:55:02Z",
      "duration_ms": 2345,
      "steps_completed": 3,
      "retry_count": 0
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 1250, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.8.9 Test Workflow

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/automation/workflows/{id}/test` | Bearer | 5/min | Test a workflow with sample data |

**Response 200:** Step-by-step execution results.

#### 5.8.10 List Workflow Templates

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/automation/workflow-templates` | Bearer | 30/min | List available workflow templates |

#### 5.8.11 Install Workflow Template

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/automation/workflow-templates/install` | Bearer | 10/min | Install a workflow template |

**Response 201:** Newly created workflow from template.

---

### 5.9 AI Agents Module

The AI Agents module manages intelligent agents that can perform tasks, answer questions, and automate workflows.

#### 5.9.1 List Agents

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/agents` | Bearer | 60/min | List AI agents in the workspace |

**Response 200:**
```json
{
  "data": [
    {
      "id": "ag_a1b2c3d4",
      "name": "Marketing Assistant",
      "description": "Helps with campaign creation and content generation",
      "type": "specialist",
      "model": "gpt-4o",
      "status": "active",
      "capabilities": ["content_generation", "campaign_planning", "analytics_query"],
      "last_invoked_at": "2026-06-19T09:00:00Z",
      "total_tasks": 450,
      "success_rate": 0.95,
      "created_at": "2026-03-01T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 4, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.9.2 Create Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/agents` | Bearer | 5/min | Create a new AI agent |

**Request Body:**
```json
{
  "name": "Content Strategist",
  "description": "Specialist agent for content strategy",
  "type": "specialist",
  "model": "gpt-4o",
  "system_prompt": "You are a senior content strategist...",
  "capabilities": ["content_strategy", "keyword_research"],
  "tools": ["web_search", "kb_search", "crm_query"],
  "temperature": 0.3,
  "guardrails": {
    "restricted_actions": ["delete_contacts", "send_campaigns"],
    "require_human_approval": ["send_campaign"]
  }
}
```

**Response 201:** Full agent object.

#### 5.9.3 Get Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/agents/{id}` | Bearer | 60/min | Get agent details including configuration |

#### 5.9.4 Update Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/agents/{id}` | Bearer | 10/min | Update agent configuration |

#### 5.9.5 Delete Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/agents/{id}` | Bearer | 5/min | Delete an AI agent |

#### 5.9.6 Invoke Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/agents/{id}/invoke` | Bearer | 20/min | Invoke an agent with a task (one-shot) |

**Request Body:**
```json
{
  "task": "Create a content calendar for the next quarter",
  "context": {"campaign_id": "camp_a1b2c3d4"},
  "stream": false
}
```

**Response 200:** Task result with output, reasoning, and actions taken.

#### 5.9.7 Chat with Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/agents/{id}/chat` | Bearer | 30/min per conversation | Multi-turn conversation with an agent |

**Response 200:** Reply with conversation ID and suggestions.

#### 5.9.8 List Agent Tasks

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/agents/{id}/tasks` | Bearer | 30/min | List task history for an agent |

#### 5.9.9 Configure Agent

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/agents/{id}/configure` | Bearer | 10/min | Update agent configuration (system prompt, tools, etc.) |

#### 5.9.10 Get Agent Memory

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/agents/{id}/memory` | Bearer | 20/min | Retrieve agent memory |

**Response 200:** Short-term and long-term memory with learned preferences and key facts.

---

### 5.10 Knowledge Base Module

The Knowledge Base module manages documents, knowledge categories, and semantic search.

#### 5.10.1 List Documents

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/kb/documents` | Bearer | 60/min | List knowledge base documents |

**Response 200:**
```json
{
  "data": [
    {
      "id": "doc_a1b2c3d4",
      "title": "Brand Guidelines 2026",
      "slug": "brand-guidelines-2026",
      "category_id": "cat_abc123",
      "content_type": "markdown",
      "status": "published",
      "version": 3,
      "tags": ["brand", "guidelines"],
      "word_count": 2450,
      "read_time_min": 10,
      "created_at": "2026-01-15T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 45, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.10.2 Create Document

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/kb/documents` | Bearer | 20/min | Create a new knowledge base document |

**Response 201:** Full document object.

#### 5.10.3 Get Document

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/kb/documents/{id}` | Bearer | 60/min | Get document with full content |

#### 5.10.4 Update Document

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/kb/documents/{id}` | Bearer | 20/min | Update a document |

#### 5.10.5 Delete Document

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/kb/documents/{id}` | Bearer | 10/min | Soft-delete a document |

#### 5.10.6 Search Knowledge Base

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/kb/search` | Bearer | 30/min | Semantic search across knowledge base |

**Response 200:**
```json
{
  "data": [
    {
      "id": "doc_a1b2c3d4",
      "title": "Brand Guidelines 2026",
      "score": 0.95,
      "excerpt": "...primary brand color is **#2563EB** (Blue)...",
      "category": "Brand"
    }
  ],
  "meta": {"total": 3, "query_time_ms": 45, "search_type": "semantic"}
}
```

#### 5.10.7 List Categories

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/kb/categories` | Bearer | 60/min | List knowledge base categories |

#### 5.10.8 Create Category

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/kb/categories` | Bearer | 10/min | Create a new knowledge base category |

---

### 5.11 Analytics Module

The Analytics module provides dashboards, reports, metrics, and data export.

#### 5.11.1 List Dashboards

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/analytics/dashboards` | Bearer | 60/min | List analytics dashboards |

**Response 200:**
```json
{
  "data": [
    {
      "id": "dash_a1b2c3d4",
      "name": "Marketing Overview",
      "description": "High-level marketing KPIs",
      "type": "template",
      "is_default": true,
      "widget_count": 8,
      "created_at": "2026-01-15T08:00:00Z",
      "updated_at": "2026-06-19T09:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 5, "has_more": false},
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.11.2 Create Dashboard

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/analytics/dashboards` | Bearer | 10/min | Create a new dashboard with widgets |

#### 5.11.3 Get Dashboard

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/analytics/dashboards/{id}` | Bearer | 60/min | Get dashboard layout and widget configuration |

#### 5.11.4 Update Dashboard

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/analytics/dashboards/{id}` | Bearer | 10/min | Update dashboard layout or widgets |

#### 5.11.5 Get Dashboard Data

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/analytics/dashboards/{id}/data` | Bearer | 30/min | Get rendered data for all dashboard widgets |

**Response 200:**
```json
{
  "data": {
    "dashboard_id": "dash_a1b2c3d4",
    "refreshed_at": "2026-06-19T10:00:00Z",
    "widgets": [
      {
        "widget_id": "w_1",
        "type": "timeseries",
        "title": "Email Campaign Performance",
        "data": {
          "labels": ["2026-06-01", "2026-06-02", "..."],
          "datasets": [{"label": "Open Rate", "values": [22.5, 24.1, 23.8]}]
        }
      },
      {
        "widget_id": "w_2",
        "type": "stat",
        "title": "Total Campaigns",
        "data": {"value": 12, "change": "+3"}
      }
    ]
  }
}
```

#### 5.11.6 Create Report

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/analytics/reports` | Bearer | 10/min | Generate a custom report |

**Response 201:** Report data with rows and column metadata.

#### 5.11.7 Get Metrics

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/analytics/metrics` | Bearer | 30/min | Query individual metrics with time ranges |

**Response 200:**
```json
{
  "data": {
    "metric": "email.open_rate",
    "period": "last_30d",
    "granularity": "day",
    "overall": {"avg": 24.5, "min": 18.2, "max": 31.8},
    "timeseries": [
      {"date": "2026-05-20", "value": 22.5},
      {"date": "2026-05-21", "value": 24.1}
    ],
    "change_vs_previous_period": "+2.3%"
  }
}
```

#### 5.11.8 Export Analytics

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/analytics/export` | Bearer | 5/min | Export analytics data as CSV or XLSX |

---

### 5.12 Billing Module

The Billing module manages subscriptions, plans, invoices, payment methods, credits, and wallets.

#### 5.12.1 List Plans

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/plans` | Bearer | 30/min | List available billing plans |

**Response 200:** Array of plans with pricing and features.

#### 5.12.2 Get Subscription

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/subscription` | Bearer | 30/min | Get current subscription details |

**Response 200:**
```json
{
  "data": {
    "id": "sub_a1b2c3d4",
    "plan_id": "plan_business",
    "plan_name": "Business",
    "status": "active",
    "billing_cycle": "monthly",
    "current_period_start": "2026-06-01T00:00:00Z",
    "current_period_end": "2026-07-01T00:00:00Z",
    "cancel_at_period_end": false,
    "next_invoice_amount": 299,
    "currency": "USD",
    "payment_method": {
      "id": "pm_a1b2c3d4",
      "type": "card",
      "last4": "4242",
      "brand": "Visa"
    },
    "created_at": "2026-01-15T08:00:00Z"
  }
}
```

#### 5.12.3 Create/Change Subscription

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/subscription` | Bearer | 5/min | Subscribe to a new plan |

**Request Body:**
```json
{
  "plan_id": "plan_business",
  "billing_cycle": "monthly",
  "payment_method_id": "pm_a1b2c3d4",
  "promo_code": "LAUNCH2026"
}
```

**Response 200:** Subscription with proration details.

#### 5.12.4 Update Subscription

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/billing/subscription` | Bearer | 5/min | Update subscription |

#### 5.12.5 Cancel Subscription

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/subscription/cancel` | Bearer | 5/min | Cancel subscription at period end |

#### 5.12.6 Reactivate Subscription

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/subscription/reactivate` | Bearer | 3/min | Reactivate a cancelled subscription |

#### 5.12.7 List Invoices

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/invoices` | Bearer | 30/min | List invoices |

#### 5.12.8 Get Invoice

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/invoices/{id}` | Bearer | 30/min | Get invoice details with PDF URL |

#### 5.12.9 Add Payment Method

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/payment-methods` | Bearer | 5/min | Add a new payment method |

**Response 201:** Payment method object with masked details.

#### 5.12.10 Delete Payment Method

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/billing/payment-methods/{id}` | Bearer | 10/min | Remove a payment method |

#### 5.12.11 Get Credits

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/credits` | Bearer | 30/min | Get AI credits balance and usage history |

#### 5.12.12 Purchase Credits

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/credits/purchase` | Bearer | 5/min | Purchase additional AI credits |

#### 5.12.13 Get Wallet

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/billing/wallet` | Bearer | 30/min | Get wallet balance and transaction history |

#### 5.12.14 Create Checkout Session

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/billing/checkout` | Bearer | 5/min | Create a checkout session for payment |

**Response 200:** Checkout URL for redirect.

---

### 5.13 Marketplace Module

The Marketplace module manages integrations, plugins, and extensions.

#### 5.13.1 List Listings

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketplace/listings` | Bearer | 60/min | List marketplace listings |

**Response 200:**
```json
{
  "data": [
    {
      "id": "list_a1b2c3d4",
      "name": "Slack Integration",
      "description": "Send notifications and campaign reports to Slack",
      "category": "integration",
      "publisher": "Acme",
      "price": 0,
      "is_free": true,
      "rating": 4.5,
      "review_count": 128,
      "install_count": 1500,
      "status": "published",
      "created_at": "2026-02-01T08:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 42, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.13.2 Get Listing

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/marketplace/listings/{id}` | Bearer | 60/min | Get listing details with screenshots and docs |

#### 5.13.3 Install Listing

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketplace/listings/{id}/install` | Bearer | 10/min | Install a marketplace integration |

**Response 200:**
```json
{
  "data": {
    "listing_id": "list_a1b2c3d4",
    "name": "Slack Integration",
    "status": "installed",
    "installed_at": "2026-06-19T10:00:00Z",
    "workspace_id": "ws_x9y8z7w6"
  }
}
```

#### 5.13.4 Uninstall Listing

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/marketplace/listings/{id}/uninstall` | Bearer | 10/min | Uninstall a marketplace integration |

#### 5.13.5 Create Listing

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketplace/listings` | Bearer (publisher) | 5/min | Submit a new marketplace listing |

**Response 201:** Listing with `pending_review` status.

#### 5.13.6 Update Listing

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/marketplace/listings/{id}` | Bearer (publisher) | 5/min | Update a marketplace listing |

#### 5.13.7 Submit Review

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/marketplace/reviews` | Bearer | 5/min per listing | Submit a review for a listing |

**Response 201:** Review object.

---

### 5.14 Notifications Module

#### 5.14.1 List Notifications

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/notifications` | Bearer | 60/min | List notifications for the current user |

**Response 200:**
```json
{
  "data": [
    {
      "id": "notif_a1b2c3d4",
      "type": "campaign_sent",
      "title": "Campaign Sent Successfully",
      "body": "Your campaign 'Q3 Welcome Series' has been sent to 15,000 recipients.",
      "category": "marketing",
      "read": false,
      "action_url": "/marketing/campaigns/camp_a1b2c3d4",
      "created_at": "2026-06-19T10:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 50,
    "total": 25,
    "unread_count": 3
  },
  "links": {"self": "...", "next": null, "prev": null}
}
```

#### 5.14.2 Mark Notification Read

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/notifications/{id}/read` | Bearer | 60/min | Mark a single notification as read |

#### 5.14.3 Mark All Read

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/notifications/read-all` | Bearer | 10/min | Mark all notifications as read |

#### 5.14.4 Get Notification Preferences

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/notifications/preferences` | Bearer | 30/min | Get notification preferences |

#### 5.14.5 Update Notification Preferences

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `PATCH` | `/api/v1/notifications/preferences` | Bearer | 10/min | Update notification preferences |

#### 5.14.6 List Notification Templates

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/notifications/templates` | Bearer | 30/min | List notification templates |

---

### 5.15 Media Library Module

#### 5.15.1 List Assets

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/media/assets` | Bearer | 60/min | List media assets |

**Response 200:**
```json
{
  "data": [
    {
      "id": "asset_a1b2c3d4",
      "name": "hero-banner.jpg",
      "type": "image",
      "mime_type": "image/jpeg",
      "size_bytes": 245000,
      "width": 1920,
      "height": 1080,
      "url": "https://cdn.amc.io/media/ws_x9y8z7w6/hero-banner.jpg",
      "thumbnail_url": "https://cdn.amc.io/media/ws_x9y8z7w6/thumbs/hero-banner.jpg",
      "folder_id": "fldr_abc123",
      "tags": ["hero", "banner"],
      "created_by": "usr_a1b2c3d4",
      "created_at": "2026-06-19T10:00:00Z"
    }
  ],
  "meta": {"page": 1, "per_page": 50, "total": 230, "has_more": true},
  "links": {"self": "...", "next": "...", "prev": null}
}
```

#### 5.15.2 Upload Asset

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/media/upload` | Bearer | 30/min per workspace | Upload a media asset (multipart) |

**Response 201:** Asset metadata with CDN URLs.

#### 5.15.3 Get Asset

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/media/assets/{id}` | Bearer | 60/min | Get asset metadata |

#### 5.15.4 Delete Asset

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `DELETE` | `/api/v1/media/assets/{id}` | Bearer | 20/min | Delete a media asset |

#### 5.15.5 List Folders

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/media/folders` | Bearer | 60/min | List media folders |

#### 5.15.6 Create Folder

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `POST` | `/api/v1/media/folders` | Bearer | 10/min | Create a new media folder |

---

### 5.16 Admin Module

All Admin endpoints require `superadmin` role.

#### 5.16.1 List Tenants

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/tenants` | Bearer (superadmin) | 30/min | List all tenants in the system |

#### 5.16.2 Get Tenant

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/tenants/{id}` | Bearer (superadmin) | 30/min | Get detailed tenant information with usage stats |

#### 5.16.3 System Health

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/system/health` | Bearer (superadmin) | 10/min | Get system health status for all services |

**Response 200:**
```json
{
  "data": {
    "status": "healthy",
    "uptime_seconds": 864000,
    "version": "1.2.3",
    "services": {
      "api_gateway": {"status": "healthy", "latency_ms": 5},
      "postgresql": {"status": "healthy", "connections": 45},
      "redis": {"status": "healthy", "memory_used_mb": 450},
      "rabbitmq": {"status": "healthy", "messages_pending": 23},
      "qdrant": {"status": "healthy", "vectors_count": 1250000},
      "minio": {"status": "healthy", "total_size_gb": 2500},
      "ai_service": {"status": "healthy", "avg_inference_ms": 850}
    },
    "last_checked_at": "2026-06-19T10:00:00Z"
  }
}
```

#### 5.16.4 System Logs

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/system/logs` | Bearer (superadmin) | 10/min | Query system logs |

#### 5.16.5 Platform Usage

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/usage` | Bearer (superadmin) | 10/min | Get platform-wide usage statistics |

**Response 200:**
```json
{
  "data": {
    "summary": {
      "total_tenants": 145,
      "total_workspaces": 380,
      "total_users": 2500,
      "total_contacts": 450000,
      "total_campaigns": 3200,
      "total_ai_tokens": 12500000,
      "total_storage_gb": 2500
    },
    "growth": {
      "tenants_30d": 12,
      "users_30d": 180
    },
    "plan_distribution": {
      "free": 80,
      "pro": 40,
      "business": 20,
      "enterprise": 5
    }
  }
}
```

#### 5.16.6 System Alerts

| Method | Path | Auth | Rate Limit | Description |
|--------|------|:----:|:----------:|-------------|
| `GET` | `/api/v1/admin/alerts` | Bearer (superadmin) | 10/min | Get system alerts and incident history |

---

## 6. GraphQL Schema

### 6.1 Key GraphQL Types

AMC's GraphQL API mirrors the REST API but with nested query capabilities. Below are the primary types.

```graphql
"""Root Query type"""
type Query {
  # Auth & User
  me: User!
  users(filter: UserFilter, limit: Int = 50, offset: Int = 0): UserConnection!
  user(id: ID!): User

  # CRM
  contact(id: ID!): Contact
  contacts(filter: ContactFilter, cursor: String, limit: Int = 50): ContactConnection!
  deal(id: ID!): Deal
  deals(filter: DealFilter, cursor: String, limit: Int = 50): DealConnection!
  pipeline(id: ID!): Pipeline
  pipelines: [Pipeline!]!
  activity(id: ID!): Activity
  activities(filter: ActivityFilter, cursor: String, limit: Int = 50): ActivityConnection!
  task(id: ID!): Task
  tasks(filter: TaskFilter, cursor: String, limit: Int = 50): TaskConnection!

  # Marketing
  campaign(id: ID!): Campaign
  campaigns(filter: CampaignFilter, cursor: String, limit: Int = 50): CampaignConnection!
  emailTemplate(id: ID!): EmailTemplate
  emailTemplates(filter: TemplateFilter, cursor: String, limit: Int = 50): EmailTemplateConnection!
  landingPage(id: ID!): LandingPage
  landingPages(cursor: String, limit: Int = 50): LandingPageConnection!
  segment(id: ID!): Segment
  segments(cursor: String, limit: Int = 50): SegmentConnection!

  # AI Suite
  generation(id: ID!): AIGeneration
  generations(filter: GenerationFilter, cursor: String, limit: Int = 50): AIGenerationConnection!
  aiUsage(period: String): AIUsage!
  brandVoice(id: ID!): BrandVoice
  brandVoices: [BrandVoice!]!

  # SEO
  keyword(id: ID!): Keyword
  keywords(filter: KeywordFilter, cursor: String, limit: Int = 50): KeywordConnection!
  seoAudit(id: ID!): SEOAudit
  backlinks(filter: BacklinkFilter, cursor: String, limit: Int = 50): BacklinkConnection!
  seoSuggestions(filter: SuggestionFilter): [SEOSuggestion!]!

  # Social
  socialAccount(id: ID!): SocialAccount
  socialAccounts: [SocialAccount!]!
  socialPost(id: ID!): SocialPost
  socialPosts(filter: SocialPostFilter, cursor: String, limit: Int = 50): SocialPostConnection!
  socialAnalytics(platform: String, startDate: Date!, endDate: Date!, granularity: Granularity = day): SocialAnalytics!

  # Automation
  workflow(id: ID!): Workflow
  workflows(filter: WorkflowFilter, cursor: String, limit: Int = 50): WorkflowConnection!
  workflowExecution(id: ID!): WorkflowExecution
  workflowExecutions(workflowId: ID!, cursor: String, limit: Int = 50): WorkflowExecutionConnection!
  workflowTemplates(category: String): [WorkflowTemplate!]!

  # AI Agents
  agent(id: ID!): Agent
  agents(filter: AgentFilter): [Agent!]!
  agentTask(id: ID!): AgentTask
  agentTasks(agentId: ID!, cursor: String, limit: Int = 50): AgentTaskConnection!
  agentMemory(agentId: ID!, type: MemoryType = all, search: String): AgentMemory!

  # Knowledge Base
  document(id: ID!): KBDocument
  documents(filter: KBDocumentFilter, cursor: String, limit: Int = 50): KBDocumentConnection!
  kbSearch(q: String!, categoryId: ID, tags: [String!], limit: Int = 10): [KBSearchResult!]!
  kbCategory(id: ID!): KBCategory
  kbCategories: [KBCategory!]!

  # Analytics
  dashboard(id: ID!): Dashboard
  dashboards: [Dashboard!]!
  dashboardData(id: ID!): DashboardData!
  metrics(metric: String!, period: String!, granularity: Granularity, filter: JSON): MetricData!

  # Billing
  plans: [Plan!]!
  subscription: Subscription!
  invoices(cursor: String, limit: Int = 50): InvoiceConnection!
  invoice(id: ID!): Invoice
  credits: CreditBalance!
  wallet: Wallet!

  # Marketplace
  marketplaceListing(id: ID!): MarketplaceListing
  marketplaceListings(category: String, cursor: String, limit: Int = 50): MarketplaceListingConnection!

  # Notifications
  notifications(filter: NotificationFilter, cursor: String, limit: Int = 50): NotificationConnection!
  notificationPreferences: NotificationPreferences!

  # Media
  asset(id: ID!): MediaAsset
  assets(filter: MediaFilter, cursor: String, limit: Int = 50): MediaAssetConnection!
  folders: [MediaFolder!]!
}

"""Root Mutation type"""
type Mutation {
  # Auth
  register(input: RegisterInput!): AuthPayload!
  login(input: LoginInput!): AuthPayload!
  refresh(refreshToken: String!, workspaceId: ID): AuthPayload!
  logout(refreshToken: String!, allSessions: Boolean): LogoutPayload!
  setupMfa: MfaSetupPayload!
  verifyMfa(code: String!): MfaVerifyPayload!
  disableMfa(password: String!, code: String!): MfaDisablePayload!
  changePassword(currentPassword: String!, newPassword: String!): SuccessPayload!
  updateProfile(input: UpdateProfileInput!): User!
  createApiKey(input: CreateApiKeyInput!): ApiKeyPayload!
  deleteApiKey(id: ID!): SuccessPayload!

  # CRM
  createContact(input: CreateContactInput!): Contact!
  updateContact(id: ID!, input: UpdateContactInput!): Contact!
  deleteContact(id: ID!): DeletedObject!
  restoreContact(id: ID!): Contact!
  createDeal(input: CreateDealInput!): Deal!
  updateDeal(id: ID!, input: UpdateDealInput!): Deal!
  moveDealStage(id: ID!, stageId: ID!, probability: Int): Deal!
  createPipeline(input: CreatePipelineInput!): Pipeline!
  updatePipeline(id: ID!, input: UpdatePipelineInput!): Pipeline!
  createActivity(input: CreateActivityInput!): Activity!
  createTask(input: CreateTaskInput!): Task!
  updateTask(id: ID!, input: UpdateTaskInput!): Task!

  # Marketing
  createCampaign(input: CreateCampaignInput!): Campaign!
  updateCampaign(id: ID!, input: UpdateCampaignInput!): Campaign!
  sendCampaign(id: ID!, input: SendCampaignInput!): Campaign!
  duplicateCampaign(id: ID!, name: String): Campaign!
  createEmailTemplate(input: CreateEmailTemplateInput!): EmailTemplate!
  updateEmailTemplate(id: ID!, input: UpdateEmailTemplateInput!): EmailTemplate!
  createLandingPage(input: CreateLandingPageInput!): LandingPage!
  createSegment(input: CreateSegmentInput!): Segment!

  # AI Suite
  generateContent(input: GenerateContentInput!): AIGeneration!
  generateBlogPost(input: GenerateBlogInput!): BlogGeneration!
  generateEmail(input: GenerateEmailInput!): EmailGeneration!
  generateSocial(input: GenerateSocialInput!): SocialGeneration!
  generateAdCopy(input: GenerateAdInput!): AdGeneration!
  generateImagePrompt(input: GenerateImagePromptInput!): ImagePromptGeneration!
  createBrandVoice(input: CreateBrandVoiceInput!): BrandVoice!

  # SEO
  addKeywords(input: [String!]!, tags: [String!]): [Keyword!]!
  runSeoAudit(url: String!, pagesLimit: Int = 100): SEOAudit!
  generateSchemaMarkup(input: SchemaInput!): SchemaOutput!
  generateMetaTags(input: MetaTagInput!): MetaTagOutput!

  # Social
  connectSocialAccount(platform: String!, oauthCode: String!, redirectUri: String!): SocialAccount!
  disconnectSocialAccount(id: ID!): SuccessPayload!
  createSocialPost(input: CreateSocialPostInput!): SocialPost!
  updateSocialPost(id: ID!, input: UpdateSocialPostInput!): SocialPost!
  deleteSocialPost(id: ID!): SuccessPayload!
  publishSocialPost(id: ID!, publishAt: DateTime): SocialPost!
  generateHashtags(topic: String!, platform: String!, count: Int = 10): HashtagPayload!

  # Automation
  createWorkflow(input: CreateWorkflowInput!): Workflow!
  updateWorkflow(id: ID!, input: UpdateWorkflowInput!): Workflow!
  deleteWorkflow(id: ID!): SuccessPayload!
  activateWorkflow(id: ID!): Workflow!
  deactivateWorkflow(id: ID!): Workflow!
  testWorkflow(id: ID!, testData: JSON!): WorkflowTestResult!
  installWorkflowTemplate(templateId: ID!, name: String!, config: JSON): Workflow!

  # AI Agents
  createAgent(input: CreateAgentInput!): Agent!
  updateAgent(id: ID!, input: UpdateAgentInput!): Agent!
  deleteAgent(id: ID!): SuccessPayload!
  invokeAgent(id: ID!, input: InvokeAgentInput!): AgentTask!
  chatWithAgent(id: ID!, input: ChatInput!): ChatMessage!
  configureAgent(id: ID!, input: ConfigureAgentInput!): Agent!

  # Knowledge Base
  createDocument(input: CreateKBDocumentInput!): KBDocument!
  updateDocument(id: ID!, input: UpdateKBDocumentInput!): KBDocument!
  deleteDocument(id: ID!): DeletedObject!
  createKbCategory(input: CreateKBCategoryInput!): KBCategory!

  # Analytics
  createDashboard(input: CreateDashboardInput!): Dashboard!
  updateDashboard(id: ID!, input: UpdateDashboardInput!): Dashboard!
  createReport(input: CreateReportInput!): Report!

  # Billing
  createSubscription(input: CreateSubscriptionInput!): Subscription!
  updateSubscription(input: UpdateSubscriptionInput!): Subscription!
  cancelSubscription(reason: String): Subscription!
  reactivateSubscription: Subscription!
  addPaymentMethod(input: AddPaymentMethodInput!): PaymentMethod!
  deletePaymentMethod(id: ID!): SuccessPayload!
  purchaseCredits(amount: Int!, paymentMethodId: ID!): CreditTransaction!
  createCheckoutSession(input: CheckoutInput!): CheckoutSession!

  # Marketplace
  installMarketplaceListing(listingId: ID!, workspaceId: ID!, config: JSON): MarketplaceInstallation!
  uninstallMarketplaceListing(listingId: ID!, workspaceId: ID!): SuccessPayload!
  createMarketplaceListing(input: CreateMarketplaceListingInput!): MarketplaceListing!
  updateMarketplaceListing(id: ID!, input: UpdateMarketplaceListingInput!): MarketplaceListing!
  submitMarketplaceReview(input: CreateReviewInput!): MarketplaceReview!

  # Notifications
  markNotificationRead(id: ID!): Notification!
  markAllNotificationsRead: SuccessPayload!
  updateNotificationPreferences(input: NotificationPreferencesInput!): NotificationPreferences!

  # Media
  uploadAsset(file: Upload!, folderId: ID, tags: [String!], altText: String): MediaAsset!
  deleteAsset(id: ID!): SuccessPayload!
  createFolder(name: String!, parentId: ID): MediaFolder!
}
```

### 6.2 Key Type Definitions

```graphql
scalar Date
scalar DateTime
scalar JSON
scalar Upload

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type Contact {
  id: ID!
  firstName: String
  lastName: String
  email: String
  phone: String
  company: String
  title: String
  status: ContactStatus!
  source: String
  tags: [String!]!
  owner: User
  deals: [Deal!]!
  activities: [Activity!]!
  tasks: [Task!]!
  notes: String
  customFields: JSON
  createdAt: DateTime!
  updatedAt: DateTime!
  deletedAt: DateTime
}

type ContactConnection {
  edges: [ContactEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type ContactEdge {
  node: Contact!
  cursor: String!
}

type Deal {
  id: ID!
  title: String!
  value: Float!
  currency: String!
  status: DealStatus!
  stage: PipelineStage!
  pipeline: Pipeline!
  contact: Contact
  owner: User
  probability: Int!
  expectedCloseDate: Date
  notes: String
  customFields: JSON
  stageChangedAt: DateTime
  timeInCurrentStageHours: Int
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Campaign {
  id: ID!
  name: String!
  description: String
  type: CampaignType!
  status: CampaignStatus!
  segment: Segment
  emailTemplate: EmailTemplate
  senderName: String
  senderEmail: String
  subject: String
  scheduledAt: DateTime
  sentAt: DateTime
  stats: CampaignStats
  tags: [String!]!
  utmParams: JSON
  createdAt: DateTime!
  updatedAt: DateTime!
}

type CampaignStats {
  recipients: Int!
  sent: Int!
  opened: Int!
  clicked: Int!
  bounced: Int!
  unsubscribed: Int!
  converted: Int!
  openRate: Float!
  clickRate: Float!
  bounceRate: Float!
}

type Workflow {
  id: ID!
  name: String!
  description: String
  status: WorkflowStatus!
  triggerType: TriggerType!
  trigger: JSON!
  steps: [WorkflowStep!]!
  errorHandling: JSON
  lastExecutedAt: DateTime
  lastExecutionStatus: ExecutionStatus
  executionCount: Int!
  errorCount: Int!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Agent {
  id: ID!
  name: String!
  description: String
  type: AgentType!
  model: String!
  status: AgentStatus!
  capabilities: [String!]!
  tools: [String!]!
  systemPrompt: String
  temperature: Float
  maxTokens: Int
  memoryConfig: JSON
  guardrails: JSON
  avatarUrl: String
  lastInvokedAt: DateTime
  totalTasks: Int!
  successRate: Float!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Notification {
  id: ID!
  type: NotificationType!
  title: String!
  body: String!
  category: String!
  read: Boolean!
  readAt: DateTime
  actionUrl: String
  actor: User
  createdAt: DateTime!
}
```

### 6.3 REST vs GraphQL Decision Matrix

| Use Case | Recommended API | Rationale |
|----------|:---------------:|-----------|
| Simple CRUD (create contact, update deal) | REST | Clear, cacheable, well-understood |
| File upload | REST | Straightforward multipart POST |
| Dashboard data (nested widget data) | GraphQL | Single request fetches multiple related data points |
| Mobile app (constrained bandwidth) | GraphQL | Client specifies exactly what fields it needs |
| Public integration (third-party) | REST | OpenAPI docs are easier to consume |
| Batch operations | REST | `/batch` endpoint handles atomicity concerns |
| Real-time updates | WebSocket/SSE | Separate from REST/GraphQL entirely |
| Complex nested queries | GraphQL | Single round trip instead of 4+ REST calls |
| Admin dashboards (aggregate metrics) | GraphQL | Can query multiple metrics in one request |
| AI Agent chat | REST | SSE streaming needed for real-time responses |
| Webhook delivery | REST | POST JSON payloads to webhook URLs |
| Bulk export | REST | Direct file download with Content-Disposition |

---

## 7. Webhook Specifications

### 7.1 Webhook Event Catalog

Webhooks enable real-time notifications of events within AMC. Events are delivered via HTTP POST to a user-configured endpoint URL.

#### Auth Module Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `user.created` | New user registered | `user.id`, `user.email`, `user.first_name`, `user.last_name` |
| `user.updated` | User profile updated | `user.id`, `changed_fields` |
| `user.deleted` | User account deleted | `user.id`, `user.email` |
| `user.login` | User logged in | `user.id`, `ip_address`, `user_agent` |
| `user.logout` | User logged out | `user.id`, `session_id` |
| `api_key.created` | API key generated | `api_key.id`, `api_key.name`, `api_key.prefix` |
| `api_key.deleted` | API key revoked | `api_key.id`, `api_key.name` |
| `mfa.enabled` | MFA enabled | `user.id` |
| `mfa.disabled` | MFA disabled | `user.id` |
| `password.changed` | Password changed | `user.id` |

#### Workspace Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `tenant.created` | New tenant created | `tenant.id`, `tenant.name`, `tenant.slug` |
| `tenant.updated` | Tenant updated | `tenant.id`, `changed_fields` |
| `workspace.created` | New workspace created | `workspace.id`, `workspace.name`, `tenant.id` |
| `workspace.updated` | Workspace updated | `workspace.id`, `changed_fields` |
| `workspace.deleted` | Workspace deleted | `workspace.id` |
| `workspace.member.invited` | User invited | `workspace.id`, `user.email`, `role` |
| `workspace.member.joined` | User accepted | `workspace.id`, `user.id`, `role` |
| `workspace.member.removed` | User removed | `workspace.id`, `user.id` |
| `workspace.member.role_changed` | Role changed | `workspace.id`, `user.id`, `previous_role`, `new_role` |

#### CRM Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `contact.created` | Contact created | `contact.id`, `contact.email`, `contact.first_name`, `contact.last_name` |
| `contact.updated` | Contact updated | `contact.id`, `changed_fields` |
| `contact.deleted` | Contact soft-deleted | `contact.id`, `deleted_at` |
| `contact.restored` | Contact restored | `contact.id`, `restored_at` |
| `deal.created` | Deal created | `deal.id`, `deal.title`, `deal.value`, `contact.id` |
| `deal.updated` | Deal updated | `deal.id`, `changed_fields` |
| `deal.stage_changed` | Deal moved to new stage | `deal.id`, `deal.title`, `previous_stage`, `new_stage` |
| `deal.deleted` | Deal soft-deleted | `deal.id` |
| `pipeline.created` | Pipeline created | `pipeline.id`, `pipeline.name` |
| `activity.created` | Activity logged | `activity.id`, `activity.type`, `activity.subject` |
| `task.created` | Task created | `task.id`, `task.subject`, `task.assignee_id` |
| `task.completed` | Task completed | `task.id`, `task.subject`, `completed_at` |

#### Marketing Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `campaign.created` | Campaign created | `campaign.id`, `campaign.name`, `campaign.type` |
| `campaign.scheduled` | Campaign scheduled | `campaign.id`, `scheduled_at` |
| `campaign.sending` | Campaign started sending | `campaign.id`, `recipient_count` |
| `campaign.sent` | Campaign sent | `campaign.id`, `sent_count` |
| `campaign.completed` | Campaign completed | `campaign.id`, `stats` |
| `campaign.opened` | Campaign email opened | `campaign.id`, `contact.id`, `timestamp` |
| `campaign.clicked` | Campaign link clicked | `campaign.id`, `contact.id`, `link_url` |
| `campaign.bounced` | Campaign email bounced | `campaign.id`, `contact.id`, `bounce_type` |
| `campaign.unsubscribed` | Recipient unsubscribed | `campaign.id`, `contact.id` |
| `template.created` | Email template created | `template.id`, `template.name` |
| `segment.created` | Segment created | `segment.id`, `segment.name` |

#### AI Suite Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `ai.generation.completed` | AI generation completed | `generation.id`, `generation.type`, `tokens_used` |
| `ai.generation.failed` | AI generation failed | `generation.id`, `error.message` |
| `ai.credits.low` | Credits running low | `balance`, `remaining_percentage` |
| `ai.credits.depleted` | Credits exhausted | `balance` |

#### SEO Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `seo.audit.completed` | SEO audit finished | `audit.id`, `url`, `score`, `critical_issues` |
| `seo.audit.failed` | SEO audit failed | `audit.id`, `url`, `error.message` |
| `seo.keyword.position_changed` | Keyword ranking changed | `keyword.id`, `previous_position`, `current_position` |

#### Social Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `social.account.connected` | Account connected | `account.id`, `account.platform` |
| `social.account.disconnected` | Account disconnected | `account.id` |
| `social.post.scheduled` | Post scheduled | `post.id`, `post.platform`, `scheduled_at` |
| `social.post.published` | Post published | `post.id`, `post.platform`, `published_at` |
| `social.post.failed` | Post publish failed | `post.id`, `post.platform`, `error.message` |

#### Automation Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `workflow.created` | Workflow created | `workflow.id`, `workflow.name` |
| `workflow.activated` | Workflow activated | `workflow.id`, `activated_at` |
| `workflow.deactivated` | Workflow deactivated | `workflow.id` |
| `workflow.execution.started` | Workflow started | `execution.id`, `workflow.id`, `trigger_data` |
| `workflow.execution.completed` | Workflow completed | `execution.id`, `workflow.id`, `status`, `duration_ms` |
| `workflow.execution.failed` | Workflow failed | `execution.id`, `workflow.id`, `error_message` |

#### AI Agent Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `agent.created` | Agent created | `agent.id`, `agent.name` |
| `agent.updated` | Agent updated | `agent.id`, `changed_fields` |
| `agent.deleted` | Agent deleted | `agent.id` |
| `agent.task.started` | Agent task started | `task.id`, `agent.id`, `task.description` |
| `agent.task.completed` | Agent task completed | `task.id`, `agent.id`, `duration_ms`, `success` |
| `agent.task.failed` | Agent task failed | `task.id`, `agent.id`, `error.message` |
| `agent.task.requires_approval` | Agent needs human approval | `task.id`, `agent.id`, `action`, `reason` |

#### Billing Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `billing.subscription.created` | Subscription started | `subscription.id`, `plan_id` |
| `billing.subscription.updated` | Subscription changed | `subscription.id`, `previous_plan`, `new_plan` |
| `billing.subscription.cancelled` | Subscription cancelled | `subscription.id`, `effective_at` |
| `billing.invoice.created` | Invoice generated | `invoice.id`, `invoice.number`, `amount` |
| `billing.invoice.paid` | Invoice paid | `invoice.id`, `amount`, `paid_at` |
| `billing.invoice.payment_failed` | Payment failed | `invoice.id`, `failure_reason`, `retry_at` |
| `billing.credits.purchased` | Credits purchased | `transaction.id`, `amount`, `new_balance` |

#### Marketplace Events

| Event Type | Description | Payload Includes |
|------------|-------------|-----------------|
| `marketplace.listing.created` | New listing submitted | `listing.id`, `listing.name` |
| `marketplace.listing.published` | Listing published | `listing.id`, `listing.name` |
| `marketplace.listing.installed` | Listing installed | `listing.id`, `workspace.id` |
| `marketplace.listing.uninstalled` | Listing uninstalled | `listing.id`, `workspace.id` |
| `marketplace.review.submitted` | New review submitted | `review.id`, `listing.id`, `rating` |

### 7.2 Delivery Format

Webhook deliveries are sent as HTTP POST requests with a JSON body.

**Request Headers:**
```
POST /webhooks/amc HTTP/1.1
Host: customer.example.com
Content-Type: application/json
User-Agent: AMC-Webhook/1.0
X-AMC-Webhook-ID: wh_evt_a1b2c3d4
X-AMC-Event-Type: contact.created
X-AMC-Delivery-Attempt: 1
X-AMC-Signature: t=1687100000,v1=abc123def456...
X-AMC-Tenant-ID: ten_zk1ym2n3
X-AMC-Workspace-ID: ws_x9y8z7w6
```

**Delivery Payload:**
```json
{
  "id": "wh_evt_a1b2c3d4",
  "event_type": "contact.created",
  "event_version": "1.0",
  "created_at": "2026-06-19T10:00:00Z",
  "tenant_id": "ten_zk1ym2n3",
  "workspace_id": "ws_x9y8z7w6",
  "data": {
    "id": "cont_xyz789",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "created_at": "2026-06-19T10:00:00Z"
  },
  "links": {
    "self": "https://api.amc.io/crm/contacts/cont_xyz789"
  }
}
```

### 7.3 Retry & Deduplication Strategy

**Retry Schedule:** Exponential backoff over 10 attempts (10s, 30s, 2min, 5min, 15min, 30min, 1h, 2h, 4h, 8h). After 10 failures, the webhook is disabled.

**Deduplication:** Each webhook carries a unique `X-AMC-Webhook-ID`. Subscribers should use this for idempotency. AMC guarantees at-least-once delivery.

**Dead Letter Queue:** After 10 failed attempts, events move to a DLQ retained for 14 days. Admins can replay from the webhook settings UI.

### 7.4 Signature Verification

All webhook payloads are signed with **HMAC-SHA256**.

**Signature Header:** `X-AMC-Signature: t=1687100000,v1=abc123def456...`

| Component | Description |
|-----------|-------------|
| `t` | Unix timestamp when the signature was generated |
| `v1` | HMAC-SHA256 signature (hex-encoded) |

**Verification (Python):**
```python
import hmac, hashlib
def verify_signature(payload, signature_header, secret):
    parts = dict(p.split('=') for p in signature_header.split(','))
    timestamp, sig_v1 = parts['t'], parts['v1']
    signed = f"{timestamp}.{payload.decode() if isinstance(payload, bytes) else payload}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_v1)
```

**Verification (TypeScript):**
```typescript
import * as crypto from 'crypto';
function verifySignature(payload: string, header: string, secret: string): boolean {
  const parts = Object.fromEntries(header.split(',').map(p => p.split('=')));
  const signed = `${parts['t']}.${payload}`;
  const expected = crypto.createHmac('sha256', secret).update(signed).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(parts['v1']));
}
```

### 7.5 Webhook Secret Management

Secrets are 32-character random strings, displayed once at creation. Rotation uses a 15-minute overlap window.

**Webhook Management Endpoints:**

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/notifications/webhooks` | Bearer | Create a webhook endpoint |
| `GET` | `/api/v1/notifications/webhooks` | Bearer | List webhook endpoints |
| `GET` | `/api/v1/notifications/webhooks/{id}` | Bearer | Get webhook details |
| `PATCH` | `/api/v1/notifications/webhooks/{id}` | Bearer | Update webhook config |
| `DELETE` | `/api/v1/notifications/webhooks/{id}` | Bearer | Delete webhook endpoint |
| `GET` | `/api/v1/notifications/webhooks/{id}/deliveries` | Bearer | Get delivery history |
| `POST` | `/api/v1/notifications/webhooks/{id}/rotate-secret` | Bearer | Rotate webhook secret |

**Create Webhook:**
```json
{
  "url": "https://hooks.example.com/amc-webhook",
  "description": "My webhook integration",
  "events": ["contact.created", "contact.updated", "deal.stage_changed"],
  "filter": {"workspace_id": "ws_x9y8z7w6"},
  "retry_config": {"max_retries": 5, "retry_interval_seconds": 60}
}
```

---

## 8. SDK / Client Libraries

### 8.1 Python SDK Structure

The AMC Python SDK (`amc-sdk-python`) provides a typed, async-first client.

```
amc_sdk/
├── __init__.py              # Client, version
├── client.py                # Main AMCClient class
├── config.py                # Configuration and settings
├── exceptions.py            # Custom exceptions
├── models/                  # Typed dataclasses
│   ├── auth.py              # User, Token, ApiKey
│   ├── crm.py               # Contact, Deal, Pipeline, Activity, Task
│   ├── marketing.py         # Campaign, EmailTemplate, LandingPage, Segment
│   ├── ai.py                # AIGeneration, BrandVoice
│   ├── seo.py               # Keyword, SEOAudit, Backlink
│   ├── social.py            # SocialAccount, SocialPost
│   ├── automation.py        # Workflow, WorkflowExecution
│   ├── agents.py            # Agent, AgentTask
│   ├── knowledge_base.py    # KBDocument, KBCategory
│   ├── analytics.py         # Dashboard, Report, MetricData
│   ├── billing.py           # Plan, Subscription, Invoice, PaymentMethod
│   ├── marketplace.py       # MarketplaceListing, Review
│   └── media.py             # MediaAsset, MediaFolder
├── resources/               # API resource managers
│   ├── base.py              # BaseResource
│   ├── auth.py
│   ├── crm.py
│   └── ... (one per module)
├── services/
│   ├── export.py
│   ├── batch.py
│   └── webhook.py           # Signature verification
└── utils/
    ├── pagination.py
    ├── filters.py
    └── retry.py
```

**Quick Start:**
```python
from amc_sdk import AMCClient
client = AMCClient(api_key="amc_live_...", tenant_id="ten_...", workspace_id="ws_...")
contacts = client.crm.contacts.list(limit=25, sort="-created_at")
for c in contacts.data:
    print(f"{c.first_name} {c.last_name} - {c.email}")
```

### 8.2 TypeScript SDK Structure

The AMC TypeScript SDK (`@amc/sdk`) provides a typed, promise-based client.

```
src/
├── index.ts                  # Main exports
├── client.ts                 # AMCClient class
├── errors.ts                 # Error classes
├── types/                    # TypeScript interfaces
│   ├── auth.ts, crm.ts, marketing.ts, ai.ts, seo.ts
│   ├── social.ts, automation.ts, agents.ts
│   ├── knowledge-base.ts, analytics.ts, billing.ts
│   └── marketplace.ts, notifications.ts, media.ts
├── resources/                # API resource managers
│   ├── base.ts, auth.ts, crm.ts, ... (one per module)
├── services/
│   ├── export.ts, batch.ts, webhook.ts
└── utils/
    ├── pagination.ts, filters.ts, retry.ts
```

**Quick Start:**
```typescript
import { AMCClient } from '@amc/sdk';
const client = new AMCClient({ apiKey: 'amc_live_...', tenantId: 'ten_...' });
const { data } = await client.crm.contacts.list({ limit: 25 });
```

### 8.3 CLI Tool Specification

The AMC CLI (`amc`) provides command-line access.

**Commands:**
```
amc login                 # Interactive login
amc whoami                # Show current user info
amc api-keys list         # List API keys
amc crm contacts list     # List contacts
amc crm contacts create   # Create contact
amc crm deals list        # List deals
amc marketing campaigns list
amc ai generate "prompt"  # Generate content
amc ai usage              # Show AI credit usage
amc seo audit run --url https://acme.com
amc social calendar --start 2026-07-01
amc billing subscription get
amc admin system health
amc admin usage
```

**Global Options:** `--api-key`, `--tenant`, `--workspace`, `--output` (json/yaml/table/csv), `--verbose`

**Config File:** `~/.amc/config.yaml` with api_key, tenant_id, workspace_id, default_output.

---

## Appendix A: Common Error Codes

| Code | HTTP | Description |
|------|:----:|-------------|
| `invalid_email` | 422 | Invalid email format |
| `invalid_phone` | 422 | Invalid phone format |
| `invalid_url` | 422 | Invalid URL format |
| `missing_field` | 422 | Required field missing |
| `duplicate_entry` | 409 | Resource already exists |
| `resource_not_found` | 404 | Resource not found |
| `invalid_credentials` | 401 | Invalid email/password |
| `token_expired` | 401 | JWT token expired |
| `insufficient_scope` | 403 | Missing required scope |
| `rate_limit_exceeded` | 429 | Too many requests |
| `quota_exceeded` | 429 | Plan quota exceeded |
| `mfa_required` | 401 | MFA code required |
| `file_too_large` | 413 | File exceeds max size |
| `payment_failed` | 402 | Payment method declined |
| `subscription_required` | 402 | Active subscription required |

## Appendix B: Rate Limit Summary by Module

| Module | Default Limit | Burst | Keyed By |
|--------|:------------:|:-----:|:--------:|
| Auth - Login | 10/min per IP | 20 | IP |
| Auth - Register | 5/min per IP | 10 | IP |
| Auth - Other | 30/min per user | 60 | User |
| CRM | 100/min | 200 | Workspace |
| Marketing | 100/min | 200 | Workspace |
| AI Suite | 30/min | 50 | Workspace |
| SEO | 30/min | 50 | Workspace |
| Social | 60/min | 100 | Workspace |
| Automation | 30/min | 50 | Workspace |
| AI Agents | 30/min | 60 | User |
| Knowledge Base | 60/min | 100 | Workspace |
| Analytics | 30/min | 50 | Workspace |
| Billing | 30/min | 60 | User |
| Marketplace | 60/min | 100 | Tenant |
| Notifications | 60/min | 100 | User |
| Media Library | 60/min | 100 | Workspace |
| Admin | 30/min | 50 | User |
| GraphQL | 100/min | 200 | Workspace |
| Webhook Delivery | 500/min | 1000 | Target URL |

---

> **End of Volume 6: Backend API Specification (REST + GraphQL)**  
> **Document Version:** 1.0  
> **Last Updated:** June 2026  
> **Next Volume:** Volume 7: Frontend Architecture & Component Library Specification
