# Aegis Marketing Cloud — Execution Roadmap

> **Tracking the build-out toward v1.0 production readiness and beyond.**
> Alignment: Volume 15 (Product Roadmap), Volume 2 (PRD MoSCoW), Volume 4 (System Architecture)
> Status: **Active** — Phases 1–5 complete, Phase 6 in progress

---

## Completed Phases (1–5) — Backend Core + Infrastructure

| Phase | Theme | Commit | Status |
|-------|-------|--------|--------|
| **1** | Critical infra: Redis config fix, rate limiting, Celery, Prometheus metrics | `6e9d94a` | ✅ |
| **2a** | Billing module: Stripe integration, subscriptions, invoices, wallet | `6e9d94a` | ✅ |
| **2b** | Media library API: MinIO upload, presigned URLs, thumbnails | `6e9d94a` | ✅ |
| **2c** | Webhook system: 29 event types, HMAC-SHA256, retry/backoff | `6e9d94a` | ✅ |
| **2d** | Analytics pipeline: event tracking, dashboards, metric snapshots | `6e9d94a` | ✅ |
| **3a** | AI Agent orchestrator: 12 agent roles, 17 tools, conversations | `6e9d94a` | ✅ |
| **3b** | Knowledge Base: Qdrant vector search, semantic search, chunking | `6e9d94a` | ✅ |
| **4a** | Frontend test infra: Vitest + RTL (49 tests), Playwright E2E | `6e9d94a` | ✅ |
| **4b** | API client modules (6 new), command palette (Cmd+K) | `6e9d94a` | ✅ |
| **5a** | SSO/SAML: Google, Microsoft, GitHub, SAML 2.0 | `6e9d94a` | ✅ |
| **5b** | Feature flags (20 flags), admin API, API versioning | `6e9d94a` | ✅ |
| **5c** | OpenAPI 3.1 spec generation, security scanning pipeline | `6e9d94a` | ✅ |

---

## Phase 6 — Frontend Application Pages (Next.js)

**Target:** Build full page UIs for every backend module. Each module gets:
- List/detail/create/edit pages matching the Atomic Design pattern
- React Query hooks for data fetching
- Zustand stores where client state is needed
- Route guard and breadcrumb integration

| Step | Module | Pages | 
|------|--------|-------|
| **6a** | Billing + Media | Subscriptions, invoices, wallet; asset gallery, upload, detail |
| **6b** | Webhooks + Analytics | Webhook list/create/detail/deliveries; dashboards, reports |
| **6c** | AI Suite + Knowledge Base | Agent list/conversation, content gen UI; document library, search |

---

## Phase 7 — Backend Production Hardening

| Task | Details |
|------|---------|
| **7a** | DB migration verification — fix `metadata` column clash in `models/ai.py` |
| **7b** | Config validation — `.env.example` audit, required-vars check on startup |
| **7c** | Health check expansion — Redis, MinIO, Qdrant, RabbitMQ connectivity checks |
| **7d** | Docker Compose polish — service dependencies, volume mounts, env alignment |
| **7e** | Makefile targets — `make dev`, `make test`, `make security-scan`, `make openapi` |

---

## Phase 8 — Advanced Integrations

| Task | Details |
|------|---------|
| **8a** | Email delivery engine — SMTP/SES integration, bounce handling, open tracking |
| **8b** | Real-time notifications — WebSocket via FastAPI + Redis pub/sub |
| **8c** | n8n workflow templates — 5 starter workflow templates for common automation |
| **8d** | File type detection + validation — magic bytes, MIME whitelist for uploads |
| **8e** | Search indexing — full-text search on contacts, deals, campaigns via PostgreSQL |

---

## Phase 9 — Testing Expansion

| Task | Details |
|------|---------|
| **9a** | Backend integration tests — billing, media, webhooks endpoints |
| **9b** | Backend integration tests — analytics, AI, knowledge endpoints |
| **9c** | Frontend component tests — billing, media pages |
| **9d** | Frontend component tests — webhooks, analytics, AI, knowledge pages |
| **9e** | E2E expansion — billing flow, AI conversation, media upload |

---

## Phase 10 — Security Hardening

| Task | Details |
|------|---------|
| **10a** | CSP headers — Content Security Policy via FastAPI middleware |
| **10b** | Secrets management — HashiCorp Vault integration guide + env validation |
| **10c** | Dependency audit — `pip-audit` + `npm audit` integrated into CI |
| **10d** | Audit logging — all modules log state-changing events to `audit_log` table |
| **10e** | Rate limit production config — sensible defaults per tenant tier |

---

## Phase 11 — v1.0 Release

| Task | Details |
|------|---------|
| **11a** | Docker Compose end-to-end smoke test — `docker compose up` + health checks |
| **11b** | CI pipeline verification — all GitHub Actions workflows pass |
| **11c** | Release tag — `v1.0.0` tag + GitHub Release with changelog |
| **11d** | Deployment guide — production deployment instructions in `docs/DEPLOY.md` |

---

## Future Milestones (v1.1–v5.0)

Per Volume 15 Product Roadmap:

| Release | Theme | Timeline |
|---------|-------|----------|
| **v1.1** | CRM Deepening — advanced pipelines, contact scoring | Month 3 |
| **v1.2** | Campaign Power — email campaigns, A/B testing, landing pages | Month 6 |
| **v1.3** | AI Expansion — agent autonomy, scheduled tasks, RAG pipelines | Month 9 |
| **v2.0** | Social + SEO deep integration, Ads Manager | Months 13–24 |
| **v3.0** | Marketplace SDK, agent autonomy, agency white-label | Months 25–36 |

---

## Per-Step Commit Convention

Every step is executed atomically with a descriptive commit message:

```
git add -A && git commit -m "Phase X: Description of what was built"
git push origin master
```
