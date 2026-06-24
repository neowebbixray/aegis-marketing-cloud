# Changelog

All notable changes to Aegis Marketing Cloud are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-06-24

### Enterprise QA Pass — Audit Resolutions

### Fixed

- **TypeScript test errors (20):** Fixed mock Agent (added `tenant_id`), User (added `name`, removed stale fields), Contact (`lead_score`→`score`). All 150 tests pass, `tsc --noEmit` clean.
- **Git default branch:** Renamed `master` → `main` locally to match CI workflows. Added `master` guard in security workflow.
- **Helm chart version:** Updated to match project-wide `1.0.0`.
- **Dockerfile backend paths:** Fixed `COPY` order for layer caching (`pyproject.toml` before source), corrected context references.
- **Ruff linting:** All `scripts/` and `app/` code clean — fixed `print` → `log`, unused imports, loop variables.
- **`.gitignore`:** Added `*.tsbuildinfo`, `next-env.d.ts`, `bandit-report.xml`, `uv.lock`.

### Added

- **Seed data script:** `scripts/seed.py` — creates admin user, demo tenant/workspace, roles/permissions, sample pipelines/stages, contacts, deals, and activities. Idempotent (`--drop` to reset). Runs via `make seed`.
- **`.env.example`:** Robust template with all service configurations documented.
- **README Quick Start:** Added `make seed` step to setup instructions.

### Changed

- **Audit report aging:** All P0 items resolved (migrations exist, compose paths fixed, CI/CD active, contact dialog wired, seed data created).

## [1.0.0] — 2026-06-23

### Production Hardening Finalization

This release marks the v1.0.0 stable release — an enterprise-grade,
multi-tenant AI-native digital marketing operating system.

### Added

- **Infrastructure**:
  - Helm charts for Kubernetes deployment
  - Grafana dashboards + alerts for all services
  - HashiCorp Vault integration for secret management
  - Prometheus rate-limiting metrics (requests per minute per tier)
  - OpenTelemetry tracing (FastAPI auto-instrumentation)
  - Sentry error tracking integration
  - n8n workflow engine integration
  - Rate limiting with per-tier configuration (Free/Starter/Professional/Enterprise)
  - Content Security Policy (CSP) middleware with report-only mode
  - Config validation at startup with halt-on-critical flag
  - GDPR data export API endpoint
  - JWKS endpoint for public key distribution

- **Backend**:
  - AI Suite endpoints (chat, content generation, agents)
  - Knowledge Base with chunking + Qdrant vector search
  - Search service (full-text + vector hybrid)
  - Marketplace for plugins/integrations
  - Full CRM: contacts, deals, pipelines, activities, lead scoring, custom fields
  - Email service: templates, campaigns, tracking (open/click), AWS SES support
  - Webhook delivery system with retries + signatures
  - SSO/OAuth: Google, Microsoft, GitHub, SAML
  - File validation with magic bytes detection
  - Async task management via Celery
  - WebSocket support for real-time notifications
  - API versioning middleware
  - Audit logging across all services

- **Frontend**:
  - Next.js 14 App Router with SSR
  - Dashboard, CRM (contacts, deals, pipelines, custom fields)
  - Analytics (reports, dashboards)
  - AI Suite with chat interface
  - Knowledge Base management UI
  - Media library with upload/preview
  - Webhook management
  - Billing/Subscription UI with Stripe
  - Settings and workspace management
  - PWA support with service worker
  - Command palette (⌘K)
  - E2E tests with Playwright

- **DevOps**:
  - Docker Compose with 14 services (PostgreSQL, Redis, Qdrant, MinIO,
    RabbitMQ, n8n, Prometheus, Grafana, Loki, Promtail, Mailpit, Vault)
  - Multi-stage Dockerfiles (dev/test/production)
  - GitHub Actions: CI, backend CI, frontend CI, Docker CI, security scan, CD
  - Pre-commit hooks: Ruff, mypy, bandit, Black
  - `.env.example` with all 150+ configuration variables
  - Bandit security scanning configuration
  - ESLint security plugin configuration

### Changed

- Migrated all models to `src/` layout (no legacy root `app/` remnants)
- JWT algorithm upgraded from HS256 to RS256 with auto-generated key pairs
- Fixed CSP middleware to skip non-directive settings correctly
- Fixed Qdrant healthcheck to use TCP test
- Fixed Dockerfile multi-stage installation order
- Updated CI validator for `src/` paths
- All 8 legacy TODO stubs eliminated — full persistence implementations

### Security

- JWT signed with RS256 (asymmetric) keys
- Password hashing via bcrypt (passlib)
- CORS restricted to allowed origins
- CSP with configurable directives
- Trusted Host middleware
- Rate limiting per-tenant and per-tier
- Input validation via Pydantic v2 schemas
- File upload validation via magic bytes
- Sensible defaults with no hardcoded secrets in production config
- Bandit + dependency scanning as CI gates

## [0.9.0] — 2026-06-21

### Added

- Frontend component tests (Vitest + Testing Library)
- E2E tests (Playwright) for CRM, billing, media, webhooks, navigation
- Integration tests for all backend modules
- Test factories for CRM, billing, AI

### Fixed

- API contract mismatches between frontend and backend
- Create Contact dialog wiring

## [0.8.0] — 2026-06-20

### Added

- Advanced integrations: n8n workflows, WebSocket real-time
- Notification service with in-app + email delivery
- Celery task infrastructure
- Email template rendering with Jinja2
- SEO analysis toolkit
- Social media management

## [0.7.0] — 2026-06-19

### Added

- Rate limiting with Prometheus metrics
- CSP middleware
- Vault integration
- GDPR compliance endpoints
- Config validation at startup
- Helm chart infrastructure
- Grafana alerting rules
- Audit logging

## [0.6.0] — 2026-06-18

### Added

- AI Suite: agent orchestration, chat, content generation
- Knowledge Base with document chunking + Qdrant vector search
- Frontend AI Suite pages
- Frontend Knowledge Base pages

## [0.5.0] — 2026-06-17

### Added

- GraphQL API with Strawberry
- SSO/OAuth providers (Google, Microsoft, GitHub)
- SAML support
- Webhook management with signing
- Media library with MinIO/S3 storage
- File validation with magic bytes

## [0.4.0] — 2026-06-16

### Added

- Full CRM suite: contacts, deals, pipelines, activities, lead scoring
- Frontend CRM pages
- Billing/Subscription with Stripe
- Frontend billing pages
- Advanced analytics engine

## [0.3.0] — 2026-06-15

### Added

- Multi-tenant architecture with Tenant and Workspace models
- JWT authentication with refresh tokens
- Role-based access control
- API key management
- Frontend authentication with Next.js

## [0.2.0] — 2026-06-14

### Added

- FastAPI application with router structure
- SQLAlchemy async models
- Alembic migrations
- Docker Compose with PostgreSQL + Redis
- CI pipeline with linting and tests

## [0.1.0] — 2026-06-13

### Added

- Project scaffolding
- Monorepo structure with `src/backend/` and `src/frontend/`
- Docker Compose for local development
- Makefile with common commands
- Initial documentation

[1.0.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v1.0.0
[0.9.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.9.0
[0.8.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.8.0
[0.7.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.7.0
[0.6.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.6.0
[0.5.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.5.0
[0.4.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.4.0
[0.3.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.3.0
[0.2.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.2.0
[0.1.0]: https://github.com/nousresearch/aegis-marketing-cloud/releases/tag/v0.1.0
