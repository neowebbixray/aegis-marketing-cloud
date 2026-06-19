# 🔍 Aegis Marketing Cloud — Full Project Audit Report

> **Date:** June 19, 2026  
> **Type:** Complete Codebase, Architecture, Infrastructure & Security Audit  
> **Classification:** Confidential — Engineering & Product

---

## Executive Summary

**Project Maturity Score: 5.2 / 10** (Pre-Alpha / Active Development)

Aegis Marketing Cloud has strong foundations — exceptional documentation (15 volumes), a sound architecture (hybrid modular-monolith/microservices with PostgreSQL RLS multi-tenancy), and production-ready auth. However, there are **two parallel codebases** (legacy root-level `backend/` `frontend/` vs active `src/backend/` `src/frontend/`) with incomplete migration, no CI/CD pipeline, and critical service gaps in marketing, AI, billing, and analytics domains.

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Documentation | 9/10 | 15 volumes, production-grade specs |
| Architecture | 7/10 | Sound hybrid approach, monolithic router |
| Backend Implementation | 6/10 | Auth done, CRM good, many services missing |
| Frontend Implementation | 5/10 | UI shell built, features partially wired |
| Database / Migrations | 4/10 | Models defined, no migrations in active codebase |
| Testing | 5/10 | Good fixtures, auth tests exist, coverage low |
| Infrastructure / Docker | 7/10 | 14 services, broken compose path references |
| CI/CD | 0/10 | **Nothing exists** |
| Security | 6/10 | Good auth, HS256 (not RS256), stubs remain |
| AI Integration | 2/10 | Blueprint only, no implementation in active code |

---

## 1. 🏗️ Project Structure & Dual Codebase Problem

### Critical Finding: Two Parallel Codebases

| Component | Legacy Path | Active Path | Migration Status |
|-----------|-------------|-------------|-----------------|
| Backend | `backend/` (full models, tasks) | `src/backend/` (cleaner, modern) | **Partial** |
| Frontend | `frontend/` (v1 shell) | `src/frontend/` (v2, re-created) | **Incomplete** |
| Docker | `docker-compose.yml` (points at `./backend`) | `deployment/docker-compose.yml` (points at `./backend`) | **Broken — references legacy path** |
| Makefile | Root `Makefile` (references `src/` paths) | — | Good, but inconsistent |

**What exists only in legacy `backend/` (NOT migrated to `src/backend/`):**
- Marketing models (Campaign, EmailTemplate, LandingPage, Funnel, Segment, Tag)
- AI models (AIAgent, AIAgentExecution, KnowledgeDocument, Conversation, Message)
- Billing models
- Media models
- Celery task files (ai.py, email.py, reports.py, workflows.py)
- Alembic migration `0001_initial_schema.py`
- GraphQL API structure
- Organization API endpoints

**What exists only in legacy `frontend/` (NOT migrated to `src/frontend/`):**
- Different design system setup (components.json, older package.json)

### Recommendation
Consolidate everything into `src/`. The legacy `backend/` and `frontend/` should be deleted after full migration. This is the #1 technical debt priority.

---

## 2. 🔧 Backend Audit — `src/backend/app/`

### 2.1 Architecture ✓
- ✅ **FastAPI** async application factory pattern
- ✅ **6 middleware layers**: RequestID → CORS → TrustedHost → TenantContext → RateLimit → Logging
- ✅ **Exception handling**: RFC 7807 Problem Details format
- ✅ **Lifespan** management with DB connectivity check
- ✅ **Health endpoint** 
- ✅ **Clean separation**: models / schemas / services / api / core

### 2.2 Models (17 total via `__init__.py`)
| Module | Models | Status |
|--------|--------|--------|
| **Base** | `BaseModel`, `TimestampMixin`, `SoftDeleteMixin`, `TenantMixin` | ✅ Complete |
| **Auth** | `User`, `OAuthAccount`, `Session`, `MfaDevice`, `ApiKey` | ✅ Complete |
| **Tenant** | `Tenant`, `Workspace`, `Team`, `TeamMember`, `Role`, `Permission`, `RolePermission`, `UserRole` | ✅ Complete |
| **CRM** | `Contact`, `Deal`, `Pipeline`, `PipelineStage`, `Activity` | ✅ Complete |

### 2.3 API Endpoints (~35 total)

| Router | Prefix | Endpoints | Status |
|--------|--------|-----------|--------|
| **Auth** | `/api/v1/auth` | register, login, refresh, logout, me, update_me, change_password, list_api_keys, create_api_key, revoke_api_key | ✅ Complete |
| **CRM** | `/api/v1/crm` | CRUD contacts (+search), CRUD deals (+stage change), CRUD pipelines (+stages), CRUD activities | ✅ Complete |
| **Tenants** | `/api/v1/tenants` | list_tenants, get_current, CRUD workspaces, invite_user, remove_member, list_roles | ✅ Complete |

### 2.4 Services
- ✅ **`BaseService`** — Generic CRUD with tenant isolation, soft-delete, pagination (excellent)
- ✅ **`AuthService`** — Registration with auto-tenant/workspace/role creation, login, token refresh with rotation, API key CRUD, password change, token verification
- ✅ **`TenantService`** — Tenant/workspace CRUD, user invite, role management
- ✅ **`ContactService`** — CRUD + search + CSV import/export
- ✅ **`DealService`** — CRUD + stage movement with cross-pipeline validation
- ✅ **`PipelineService`** — CRUD + create-with-stages + eager-load stages
- ✅ **`ActivityService`** — CRUD

### 2.5 Schemas (Pydantic v2)
- ✅ Auth: RegisterRequest (with password strength), LoginRequest, RefreshRequest, TokenResponse, UserResponse, ApiKeyResponse, etc.
- ✅ CRM: ContactCreate/Update/Response, DealCreate/Update/Response, PipelineCreate/Stage/Response, ActivityCreate/Response
- ✅ Tenant: WorkspaceCreate/Update/Response, TenantResponse, InviteUserRequest, RoleResponse
- ⚠️ Missing: Marketing, AI, Billing, Analytics schemas

### 2.6 Gaps in Active Backend
| Missing Feature | Impact | Priority |
|----------------|--------|----------|
| Marketing service (campaigns, email templates) | Core product gap | **P0** |
| AI agent service | Listed in docs, not implemented | **P0** |
| Billing / Subscription service | No revenue model implemented | **P0** |
| Analytics / Reporting service | PRD requires it | **P1** |
| Media / Asset management | MinIO set up, no service | **P1** |
| Webhook / Event bus service | RabbitMQ set up, no producer | **P1** |
| Workflow engine integration | n8n connected, no API | **P1** |
| OAuth provider endpoints | Models exist, no routes | **P2** |
| MFA implementation | Models exist, no verification | **P2** |
| Rate limiting (Redis-backed) | Stub only | **P2** |
| Email sending (SMTP/Mailpit) | Task stubs only | **P2** |

---

## 3. 🗄️ Database & Migrations Audit

### Critical Finding: No Migrations in Active Codebase

| Item | Legacy `backend/` | Active `src/backend/` |
|------|-------------------|----------------------|
| Migrations dir | `alembic/versions/0001_initial_schema.py` (694 lines) | `alembic/versions/.gitkeep` **(empty!)** |
| Alembic config | `alembic.ini` ✓ | `alembic.ini` ✓ |
| Env script | `alembic/env.py` ✓ | `alembic/env.py` ✓ |

The legacy migration creates tables for a DIFFERENT model set (Organization-based, not Tenant-based). The `src/` models have a completely different schema design using `tenant_id` instead of `organization_id`. **These databases are incompatible.**

### Migration Needed: 17 tables
Users, OAuthAccounts, Sessions, MfaDevices, ApiKeys, Tenants, Workspaces, Teams, TeamMembers, Roles, Permissions, RolePermissions, UserRoles, Contacts, Deals, Pipelines, PipelineStages, Activities

Missing from migration: Campaigns, EmailTemplates, LandingPages, Funnels, Segments, Tags, AIAgents, AIAgentExecutions, KnowledgeDocuments, Conversations, Messages (exist in legacy models only)

### Recommendations
1. **Delete legacy migration** — it's incompatible with current model design
2. **Run `alembic revision --autogenerate -m "initial_schema"`** from `src/backend/` to generate a fresh migration based on current models
3. **Add `--sqlalchemy.url` to alembic.ini** or ensure `DATABASE_URL` env is always set
4. **Create seed data script** for default roles, permissions, and demo tenants

---

## 4. 💻 Frontend Audit — `src/frontend/`

### 4.1 Architecture
- ✅ **Next.js 14 App Router** with TypeScript and Tailwind CSS
- ✅ **Zustand** for auth and workspace state (persisted to localStorage)
- ✅ **TanStack Query** (React Query v5) for server state
- ✅ **react-hook-form** + **zod** for form validation
- ✅ **Radix UI** primitives (17 components) + **lucide-react** icons
- ✅ **Custom API client** with auto-auth injection, workspace context, 401 handling

### 4.2 Pages Implemented
| Route | Page | Status |
|-------|------|--------|
| `/` | Landing page | ✅ Built, redirects auth'd users |
| `/login` | Login with validation | ✅ Built |
| `/register` | Registration with validation | ✅ Built |
| `/dashboard` | Dashboard with KPIs, timeline, AI suggestions | ✅ Built (mock data) |
| `/crm/contacts` | Contact list table + Create dialog | ✅ Built (dialog doesn't submit) |
| `/crm/contacts/[id]` | Contact detail | ✅ Built |
| `/crm/deals` | Kanban board | ✅ Built |
| `/crm/pipelines` | Pipeline management | ✅ Built |
| `/marketing/campaigns` | Campaigns (sidebar link) | ❌ **Not implemented** |
| `/ai-suite` | AI Suite (sidebar link) | ❌ **Not implemented** |
| `/marketing/seo` | SEO (sidebar link) | ❌ **Not implemented** |
| `/marketing/social` | Social (sidebar link) | ❌ **Not implemented** |
| `/settings` | Settings (sidebar link) | ❌ **Not implemented** |

### 4.3 Frontend Gaps
| Issue | Severity | Details |
|-------|----------|---------|
| Create Contact dialog exists but **doesn't submit** | **Critical** | Dialog UI renders, no onSubmit handler, no mutation call |
| Dashboard uses **hardcoded mock data** | High | KPIs, activities, AI suggestions all static |
| API client and backend **response format mismatch** | High | Frontend expects `{data: T, meta: ...}`, backend returns flat objects |
| Missing marketing, AI, settings, analytics pages | High | Sidebar links lead to 404s |
| `/crm/contacts/search` endpoint mismatch | Medium | Frontend sends POST with `{q: query}`, backend expects query param |
| `/api/v1/workspaces` path mismatch | Medium | Frontend hits `/api/v1/workspaces`, backend router is `/api/v1/tenants/workspaces` |
| No token refresh interceptor | Medium | 401 → immediate logout, no refresh attempt |
| No loading/error states for workspace fetch on layout | Medium | Layout renders immediately, redirects if not auth'd |
| No E2E tests (Playwright/Cypress) | Medium | Zero browser tests |

### 4.4 UI Component Library
✅ 17 reusable components: Avatar, Badge, Button, Card, Command, Dialog, DropdownMenu, Input, Label, Select, Separator, Skeleton, Table, Tabs, Toast, Tooltip, Index
✅ Consistent styling with `cn()` utility (clsx + tailwind-merge)
✅ Sonner toast notifications

---

## 5. 🧪 Testing Audit

### Backend Tests (`src/backend/tests/`)
| File | Tests | Status |
|------|-------|--------|
| `conftest.py` | Fixtures: setup_database, db_session, app, client, sample_tenant, sample_workspace, sample_role, sample_user, sample_user2, auth_headers, tenant_headers | ✅ Excellent |
| `test_auth.py` | 7 tests: register, duplicate email, login, wrong password, refresh token rotation, protected endpoint, get me authenticated | ✅ Good |
| `test_crm.py` | ~6 tests: create contact, list/create/get contacts, deal CRUD, tenant isolation | ✅ Partial |
| `test_tenant.py` | ~5 tests: create workspace, list, get, update, tenant isolation | ✅ Partial |

### Critical Gaps
| Gap | Impact |
|-----|--------|
| No service-layer tests (unit tests) | Business logic untested |
| No negative-path tests (validation errors, edge cases) | Error handling untested |
| No pipeline/activity endpoint tests | Prominent API surface untested |
| No integration tests with real DB | Test DB naming `_test` append could collide |
| No load/stress tests | Zero perf data |
| No E2E tests for frontend | Zero browser tests |

### Code Quality Tooling
- ✅ `pyproject.toml` has pytest config with `asyncio_mode=auto`
- ⚠️ **No flake8/ruff/mypy configuration** in `src/backend/pyproject.toml` (root-level has them)
- ⚠️ **No pre-commit hooks** configured
- ⚠️ **No commit message conventions** enforced

---

## 6. 🔐 Security Audit

### 6.1 Authentication — ✅ Good but Has Issues
| Component | Status | Notes |
|-----------|--------|-------|
| Password hashing (bcrypt) | ✅ | Via passlib, standard practice |
| JWT signing | ⚠️ **HS256** | Doc says RS256, actual code uses HMAC symmetric — means no cross-service trust without shared secret |
| JWT with jti + type claims | ✅ | Prevents confusion between access/refresh |
| Refresh token rotation | ✅ | Old session revoked, new one issued |
| API key management | ✅ | Prefix + SHA-256 hash, full key shown once |
| Token expiry | ✅ | Configurable (15 min access, 7 day refresh) |

### 6.2 Critical Security Findings
| # | Finding | Severity | Recommendation |
|---|---------|----------|----------------|
| 1 | **HS256 vs RS256 mismatch** | **High** | Docs specify RS256 (asymmetric) which is needed for cross-service JWT trust. Code uses HS256 (symmetric). Switch to RS256. |
| 2 | **Secrets in docker-compose.yml** | **High** | DB passwords, Redis passwords, MinIO credentials, RabbitMQ credentials, n8n encryption key all hardcoded. Use .env files. |
| 3 | **Rate limiting is a stub** | **Medium** | No Redis-backed throttling — vulnerable to brute force. |
| 4 | **MFA models exist, no enforcement** | **Medium** | Login checks `user.mfa_devices` but throws generic error — no MFA challenge flow. |
| 5 | **OAuth endpoints not implemented** | **Medium** | Models exist for social login, no endpoints. |
| 6 | **No CSRF protection** | **Medium** | Cookie-based sessions not used, but should add SameSite/CSRF token for cookie scenarios. |
| 7 | **CORS is wide open** | **Low** | `allow_origins=settings.cors_origins` — defaults to `["*"]`, should lock down per environment. |
| 8 | **No TLS termination** | **Low** | Nginx config exists but no HTTPS enforcement. |
| 9 | **Password change doesn't revoke sessions** | **Low-Medium** | Comment says "NOTE: batch-update sessions here" — not implemented. |
| 10 | **`.env.example` placeholder secret** | **Low** | `SECRET_KEY=change-me...` — easy to miss in deployment. |

### 6.3 Tenant Isolation
- ✅ `TenantContextMiddleware` extracts `X-Tenant-ID` header to `request.state`
- ✅ `BaseService._apply_tenant_filter()` auto-filters queries by `tenant_id`
- ✅ `set_tenant_id()` helper for PostgreSQL `set_config` (RLS support)
- ⚠️ **No actual PostgreSQL RLS policies created** — isolation relies on application-layer filtering, which is not foolproof
- ⚠️ User model has `TenantMixin` but Users should logically belong to tenants via UserRole, not carry tenant_id

---

## 7. 🚀 Infrastructure & DevOps Audit

### 7.1 Docker Stack — ✅ 14 Services
| Service | Technology | Port | Healthcheck | Status |
|---------|-----------|------|-------------|--------|
| PostgreSQL | 16-alpine | 5432 | ✅ pg_isready | ✅ |
| Redis | 7-alpine | 6379 | ✅ ping | ✅ |
| Qdrant | v1.12.0 | 6333, 6334 | ✅ /healthz | ✅ Good |
| MinIO | latest | 9000, 9001 | ✅ /health/live | ✅ |
| RabbitMQ | 4.0-management | 5672, 15672 | ✅ rabbitmq-diagnostics | ✅ |
| n8n | latest | 5678 | ✅ /healthz | ✅ |
| Backend (FastAPI) | Custom | 8000 | ✅ /health | ✅ |
| Worker (Celery) | Custom | — | ⚠️ Depends on backend | ⚠️ |
| Flower | Custom | 5555 | — | ⚠️ |
| Prometheus | v2.54.0 | 9090 | — | ✅ |
| Grafana | 11.2.0 | 3000 | — | ✅ |
| Loki | 3.1.0 | 3100 | — | ✅ |
| Promtail | 3.1.0 | — | — | ✅ |
| Mailpit | latest | 1025, 8025 | — | ✅ |

### 7.2 Docker Compose Issues
| # | Issue | Severity |
|---|-------|----------|
| 1 | **Root `docker-compose.yml` references `./backend` not `./src/backend`** | **Critical** — will run legacy code |
| 2 | `deployment/docker-compose.yml` also references `./backend` | **Critical** — same issue |
| 3 | n8n uses hardcoded encryption key | **Medium** |
| 4 | Promtail mounts `/var/log` (Linux path, won't work on Windows Docker Desktop) | **Medium** |
| 5 | All passwords hardcoded in compose files | **High** |

### 7.3 CI/CD — ❌ Critical Gap
| System | Status | Notes |
|--------|--------|-------|
| GitHub Actions | ❌ None | No workflows for test/build/deploy |
| GitLab CI | ❌ None | |
| Pre-commit hooks | ❌ None | No lint/format enforcement |
| Docker image registry | ❌ None | No published images |
| Deployment target | ❌ None | No Terraform, no k8s manifests, no platform.sh config |
| Secret management | ❌ None | No Vault, Doppler, or GitHub Secrets |

### 7.4 Monitoring Stack ✅
- Prometheus scrape config exists
- Grafana dashboards + datasources provisioned
- Loki + Promtail for log aggregation
- ⚠️ No alerting rules or notification channels configured

---

## 8. 🤖 AI Architecture Audit

### Blueprint (docs/volume-8) — ✅ Excellent
- 12 specialized agents defined (Content Writer, Campaign Optimizer, SEO Analyst, etc.)
- Hermes Agent framework integration planned
- NVIDIA NIM for model hosting
- Qdrant for vector memory
- Prompt management system
- Human-in-the-loop workflows

### Implementation Status — ❌ 2/10
- **Legacy `backend/`**: Has AI models (AIAgent, Execution, KnowledgeDocument, Conversation, Message) and Celery tasks
- **Active `src/backend/`**: Zero AI code. No models, no services, no endpoints
- **No actual LLM integration** (OpenAI, NVIDIA NIM, or self-hosted)
- **No Hermes Agent SDK integration**
- **Qdrant is running but has no schema or collection creation logic**

### Recommendations
1. Migrate AI models from `backend/app/models/ai.py` to `src/backend/app/models/`
2. Create AI service layer with LLM provider abstraction (OpenAI/NVIDIA NIM)
3. Implement vector store service for Qdrant
4. Create agent execution engine
5. Wire AI agent endpoints

---

## 9. 📋 Documentation Audit — ✅ Exceptional

| Volume | Topic | Pages | Quality |
|--------|-------|-------|---------|
| 1 | Vision, Mission, Business Goals | ~5,000 chars | ⭐ |
| 2 | PRD — Product Requirements | ~64,000 chars | ⭐ |
| 3 | SRS — System Requirements | ~32,000 chars | ⭐ |
| 4 | System Architecture | ~22,000 chars | ⭐ |
| 5 | Database Design | ~18,000 chars | ⭐ |
| 6 | API Specification | ~18,000 chars | ⭐ |
| 7 | Frontend Design System | ~22,000 chars | ⭐ |
| 8 | AI Architecture | ~29,000 chars | ⭐ |
| 9 | Workflow Automation | ~12,000 chars | ⭐ |
| 10 | Security Architecture | ~20,000 chars | ⭐ |
| 11 | DevOps Deployment | ~13,000 chars | ⭐ |
| 12 | Testing Strategy | ~26,000 chars | ⭐ |
| 13 | Plugin Marketplace SDK | ~25,000 chars | ⭐ |
| 14 | Operations Manual | ~19,000 chars | ⭐ |
| 15 | Product Roadmap | ~11,000 chars | ⭐ |

---

## 10. 📊 Priority Action Matrix

### P0 — Blockers (Must Fix Before Any Feature Work)
| # | Task | Area | Effort |
|---|------|------|--------|
| 1 | **Generate initial Alembic migration** for `src/` models | DB | 1h |
| 2 | **Fix Docker Compose paths** to use `./src/backend` and `./src/frontend` | Infra | 1h |
| 3 | **Create CI/CD pipeline** (GitHub Actions: lint → test → build) | Infra | 4h |
| 4 | **Fix Create Contact dialog** — wire submit handler | Frontend | 1h |
| 5 | **Fix API contract mismatches** (response shapes, endpoints) | Full-stack | 2h |
| 6 | **Set up secret management** — move passwords to `.env` files | Security | 1h |

### P1 — Core Feature Gaps
| # | Task | Area | Effort |
|---|------|------|--------|
| 7 | **Migrate legacy models** (Marketing, AI, Billing) into `src/` | Backend | 4h |
| 8 | **Implement marketing service** — campaigns, email templates | Backend | 16h |
| 9 | **Build missing frontend pages** (campaigns, AI suite, settings) | Frontend | 16h |
| 10 | **Add frontend E2E tests** (Playwright: login, contacts, deals flow) | QA | 8h |
| 11 | **Implement OAuth provider endpoints** | Backend | 8h |
| 12 | **Switch JWT from HS256 to RS256** | Security | 2h |

### P2 — Quality & Polish
| # | Task | Area | Effort |
|---|------|------|--------|
| 13 | **Implement Redis rate limiting** | Backend | 4h |
| 14 | **Add MFA verification flow** (TOTP) | Backend | 8h |
| 15 | **Add pre-commit hooks** (ruff + format) | Tooling | 1h |
| 16 | **Expand test coverage** (service tests, negative paths) | QA | 8h |
| 17 | **Create seed data for dev environments** | Backend | 2h |
| 18 | **Set up Grafana alerts** + notification channel | Monitoring | 2h |

### P3 — Strategic
| # | Task | Area | Effort |
|---|------|------|--------|
| 19 | **Implement AI agent engine** (Hermes integration) | AI | 24h+ |
| 20 | **Billing/Subscription service** (Stripe integration) | Backend | 16h |
| 21 | **Analytics service + dashboard** | Full-stack | 16h |
| 22 | **Plugin marketplace system** | Full-stack | 24h+ |
| 23 | **Terraform/Pulumi for cloud infra** | Infra | 16h |

---

## 11. ⚠️ Notable Bugs & Issues Found

### Code Bugs
1. **`auth.py` service `change_password`** — Lines 339-344: selects sessions but never revokes them (dead code)
2. **`deps.py` `get_tenant_context`** — Line 92: uses `request.app.state.db` which won't work (app state never set). Falls through to token claims, but if neither header nor token has tenant_id, raises ForbiddenException
3. **`conftest.py` `auth_headers`** — Line 209: accesses `sample_user.tenant_id` but User model has `tenant_id` from `TenantMixin` — this column exists but should come from UserRole relationship
4. **`frontend api.ts`** — workspace endpoints hit `/api/v1/workspaces` but backend router is at `/api/v1/tenants/workspaces`
5. **Frontend `authApi.register`** — calls backend but returns `{message: string}`, while backend actually returns `TokenResponse`
6. **Frontend contacts page** — Create dialog has no `onSubmit`, no form state binding — completely non-functional

### Design Issues
1. User model extends `TenantMixin` — this adds `tenant_id` directly to the `users` table, but users should be tenant-scoped via `UserRole` → `Workspace` → `Tenant`. This creates confusion: a user's "home tenant" vs "workspace tenants"
2. Rate limit middleware stub — would silently pass through even when enabled
3. No `__init__.py` in `src/backend/app/services/` directory (empty file exists, but services directory doesn't have proper exports)

---

## 12. 🏁 Next Steps (Recommended Sprint Plan)

Based on this audit, I recommend the following sprint order:

### Sprint 0 — Foundation Fixes (Week 1)
1. Generate initial Alembic migration
2. Fix Docker Compose paths
3. Set up GitHub Actions CI (lint + test + build)
4. Fix critical frontend bugs (contact dialog, API paths)
5. Move secrets to .env
6. Consolidate all code into `src/`

### Sprint 1 — Core Completeness (Week 2-3)
1. Migrate legacy models into `src/`
2. Implement marketing campaign service + API
3. Build missing frontend pages (campaigns, settings)
4. Add E2E test suite
5. Expand backend test coverage (service tests)

### Sprint 2 — Production Hardening (Week 4)
1. Switch to RS256 JWT
2. Implement Redis rate limiting
3. Add MFA flow
4. Set up OAuth endpoints
5. Create seed data + dev scripts
6. Production monitoring + alerting

### Sprint 3 — AI & Revenue (Week 5+)
1. AI agent engine with Hermes integration
2. Billing/Stripe integration
3. Analytics service
4. Begin plugin marketplace

---

## Audit Methodology

This audit was performed by examining:
- All 16 documentation volumes
- All source files in `src/backend/` (37 Python files)
- All source files in `src/frontend/` (28 TypeScript/TSX files + config)
- All files in legacy `backend/` (including models, tasks) and `frontend/`
- Docker Compose configurations (both root and deployment/)
- Root-level config files (Makefile, pyproject.toml, .env.example)
- All 4 test files and fixtures
- End-to-end tracing: `route → schema → service → model → migration`

**Directories scanned:** `backend/`, `frontend/`, `src/`, `docs/`, `deployment/`, `infra/`, `scripts/`  
**Files examined:** 120+ source files  
**Analysis depth:** Every API endpoint, every model class, every service method, every frontend page
