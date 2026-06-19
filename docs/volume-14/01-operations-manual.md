# Volume 14: Operations Manual — Runbooks, Incident Response & Maintenance

> **Document Version:** 1.0  
> **Classification:** Internal — Operations & Engineering  
> **Date:** June 2026  
> **Author:** Operations Team  
> **Status:** ✅ Complete  
> **Page Count Equivalent:** ~90  

---

## Table of Contents

1. [Operations Philosophy](#1-operations-philosophy)
2. [System Overview for On-Call Engineers](#2-system-overview-for-on-call-engineers)
3. [On-Call Procedures](#3-on-call-procedures)
4. [Monitoring & Alerting Runbooks](#4-monitoring--alerting-runbooks)
5. [Database Runbooks (PostgreSQL)](#5-database-runbooks-postgresql)
6. [Redis Runbooks](#6-redis-runbooks)
7. [Qdrant Runbooks](#7-qdrant-runbooks)
8. [RabbitMQ Runbooks](#8-rabbitmq-runbooks)
9. [MinIO Runbooks](#9-minio-runbooks)
10. [Application Service Runbooks](#10-application-service-runbooks)
11. [AI Service Runbooks](#11-ai-service-runbooks)
12. [n8n Workflow Runbooks](#12-n8n-workflow-runbooks)
13. [Tenant/Customer Runbooks](#13-tenantcustomer-runbooks)
14. [Billing Runbooks](#14-billing-runbooks)
15. [Backup & Recovery Runbooks](#15-backup--recovery-runbooks)
16. [Security Incident Runbooks](#16-security-incident-runbooks)
17. [Maintenance Procedures](#17-maintenance-procedures)
18. [Post-Mortem Template](#18-post-mortem-template)
19. [Appendices](#19-appendices)

---

## 1. Operations Philosophy

### 1.1 Runbooks for Everything — No Tribal Knowledge

Every procedure, every fix, every known workaround is documented in this manual. If an engineer discovers a novel way to resolve an issue, they **must** add it to the runbook within 24 hours. The goal is zero reliance on "who knows how to fix this." When the on-call phone rings at 3 AM, the answer is in this document — not in one person's head.

- **Rule:** If it took more than 5 minutes to figure out, it gets a runbook entry.
- **Rule:** No procedure is added verbally — every fix flows through a PR to this document.
- **Rule:** Runbooks are reviewed quarterly for accuracy during the performance review cycle.

### 1.2 Automate First, Manual Fallback Second

Whenever a runbook step is executed more than twice, it becomes a candidate for automation. Our hierarchy of response:

```
1. Automated remediation (Prometheus Alertmanager webhook → automation service)
2. Scripted one-liner (curl / SQL / CLI)
3. Step-by-step manual procedure (this document)
```

Automation is built for the common case; this manual covers the edge cases and fallbacks when automation fails.

### 1.3 Every Incident Is a Learning Opportunity (Blameless Post-Mortems)

We conduct blameless post-mortems for every SEV1 and SEV2 incident, plus any SEV3 with a notable learning outcome. **"Blameless"** means we focus on system failures, process gaps, and missing automation — not individual mistakes. Every engineer should be able to say "I broke prod" without fear of reprisal.

- Post-mortems are written within 48 hours of resolution.
- Action items are tracked in Jira with owners and deadlines.
- The post-mortem template is in [Section 18](#18-post-mortem-template).

### 1.4 Document as You Discover — Runbooks Evolve with the System

This document is a living artifact. As the AMC platform grows, new services, alerts, and failure modes appear. Every on-call shift should end with at least one improvement to this manual.

- **PR review required** for any runbook change.
- **Quarterly deep review** to prune stale procedures.
- **Version-controlled** alongside the codebase (this file lives in the docs repo).

---

## 2. System Overview for On-Call Engineers

### 2.1 Service Inventory

All services running in the AMC platform. Internal ports shown; external ports may differ per environment.

| # | Service | Purpose | Internal Port | Healthcheck URL | Log Location |
|---|---------|---------|--------------|-----------------|--------------|
| 1 | **frontend** | Next.js 14 web application (server + client components) | 3000 | `/api/health` | `docker logs frontend` / `/var/log/frontend/` |
| 2 | **api-gateway** | FastAPI gateway — routing, auth, tenant resolution, rate limiting | 8000 | `/health` | `docker logs api-gateway` / `/var/log/api-gateway/` |
| 3 | **monolith** | Modular monolith — CRM, Marketing, Projects, Knowledge modules | 8001 | `/health` | `docker logs monolith` / `/var/log/monolith/` |
| 4 | **auth-service** | Authentication, JWT issuance, OAuth, SSO | 8002 | `/health` | `docker logs auth-service` / `/var/log/auth/` |
| 5 | **billing-service** | Stripe integration, invoices, subscriptions, credit tracking | 8003 | `/health` | `docker logs billing-service` / `/var/log/billing/` |
| 6 | **notification-service** | Email, SMS, push notifications via RabbitMQ consumers | 8004 | `/health` | `docker logs notification-service` / `/var/log/notifications/` |
| 7 | **media-service** | Image/video processing, CDN integration, asset management | 8005 | `/health` | `docker logs media-service` / `/var/log/media/` |
| 8 | **ai-orchestrator** | AI agent orchestrator — task scheduling, agent dispatch, result aggregation | 8010 | `/health` | `docker logs ai-orchestrator` / `/var/log/ai/orchestrator/` |
| 9 | **ai-agent-runtime** | Hermes agent runtime — per-agent execution environment | 8011 | `/health` | `docker logs ai-agent-runtime` / `/var/log/ai/agents/` |
| 10 | **ai-memory** | Memory service — Qdrant vector storage, Redis short-term memory | 8012 | `/health` | `docker logs ai-memory` / `/var/log/ai/memory/` |
| 11 | **nim** | NVIDIA NIM — GPU inference microservice | 8001 | `/v1/health/ready` | `docker logs nim` / `/var/log/nim/` |
| 12 | **ollama** | Local LLM inference (dev/fallback) | 11434 | `/api/tags` | `docker logs ollama` / `/var/log/ollama/` |
| 13 | **analytics-service** | Analytics aggregation, reporting, dashboards | 8020 | `/health` | `docker logs analytics-service` / `/var/log/analytics/` |
| 14 | **admin-service** | Admin panel API — tenant management, system settings | 8030 | `/health` | `docker logs admin-service` / `/var/log/admin/` |
| 15 | **marketplace-service** | Plugin marketplace — listing, install, license management | 8040 | `/health` | `docker logs marketplace-service` / `/var/log/marketplace/` |
| 16 | **webhook-service** | Outgoing webhooks — delivery, retry, dead letter | 8050 | `/health` | `docker logs webhook-service` / `/var/log/webhooks/` |
| 17 | **n8n** | Workflow automation engine | 5678 | `/healthz` | `docker logs n8n` / `/var/log/n8n/` |
| 18 | **unleash** | Feature flag server | 4242 | `/health` | `docker logs unleash` / `/var/log/unleash/` |
| 19 | **postgres-primary** | PostgreSQL primary database | 5432 | `pg_isready` | `/var/log/postgresql/` |
| 20 | **postgres-replica** | PostgreSQL read replica | 5433 | `pg_isready` | `/var/log/postgresql/` |
| 21 | **pgbouncer** | PostgreSQL connection pooler | 6432 | `pgbouncer -q show databases` | `docker logs pgbouncer` |
| 22 | **redis-cache** | Redis cache (LRU eviction, 2 GB max) | 6379 | `redis-cli ping` | `docker logs redis-cache` |
| 23 | **redis-sessions** | Redis sessions (no eviction, 1 GB max) | 6380 | `redis-cli ping` | `docker logs redis-sessions` |
| 24 | **redis-queue** | Redis queue / BullMQ (no eviction, 4 GB max) | 6381 | `redis-cli ping` | `docker logs redis-queue` |
| 25 | **qdrant** | Vector database for AI memory and search | 6333 (REST), 6334 (gRPC) | `/health` | `docker logs qdrant` / `/var/log/qdrant/` |
| 26 | **minio** | S3-compatible object storage | 9000 (API), 9001 (Console) | `/minio/health/live` | `docker logs minio` / `/var/log/minio/` |
| 27 | **rabbitmq** | Message broker | 5672 (AMQP), 15672 (Management) | `rabbitmq-diagnostics ping` | `docker logs rabbitmq` / `/var/log/rabbitmq/` |
| 28 | **prometheus** | Metrics collection and alerting | 9090 | `/-/healthy` | `docker logs prometheus` |
| 29 | **grafana** | Dashboards and alert management | 3001 | `/api/health` | `docker logs grafana` |
| 30 | **loki** | Log aggregation | 3100 | `/ready` | `docker logs loki` |
| 31 | **promtail** | Log shipping to Loki | — | (sidecar) | `docker logs promtail` |
| 32 | **tempo** | Distributed tracing | 4317 (gRPC), 4318 (HTTP) | `/ready` | `docker logs tempo` |
| 33 | **mailhog** | SMTP mock for dev (dev only) | 1025 (SMTP), 8025 (UI) | (no healthcheck) | `docker logs mailhog` |
| 34 | **ngrok** | Public tunnel for webhook testing (dev only) | 4040 (UI) | (external) | `docker logs ngrok` |

### 2.2 Environment Quick Reference

#### URLs

| Environment | Frontend | API Gateway | Grafana | Admin Panel | Notes |
|-------------|---------|-------------|---------|-------------|-------|
| **Development (local)** | `http://localhost:3000` | `http://localhost:8000` | `http://localhost:3001` | `http://localhost:8030` | Docker Compose |
| **Staging** | `https://staging.amccloud.com` | `https://api-staging.amccloud.com` | `https://grafana-staging.amccloud.com` | `https://admin-staging.amccloud.com` | Swarm cluster |
| **Production** | `https://app.amccloud.com` | `https://api.amccloud.com` | `https://grafana.amccloud.com` | `https://admin.amccloud.com` | Swarm cluster |

#### Credentials

| Resource | Location | Access Method |
|----------|----------|---------------|
| Database (PostgreSQL) | `deployment/secrets/db_password.txt` / Vault secret `kv/db/primary` | `docker compose exec pgbouncer psql -U amc -d amc` |
| Redis | `deployment/secrets/redis_password.txt` / Vault secret `kv/redis/cache` | `redis-cli -h <host> -p <port> -a <password>` |
| MinIO root | `deployment/secrets/minio_password.txt` / Vault secret `kv/minio/root` | Console at `https://<host>:9001` |
| RabbitMQ admin | `deployment/secrets/rabbitmq_password.txt` / Vault secret `kv/rabbitmq/admin` | Management UI at `https://<host>:15672` |
| Grafana admin | Vault secret `kv/grafana/admin` | Login at `https://<host>:3001` |
| AWS (backups) | Vault secret `kv/aws/backup-role` | IAM role — no static keys |
| Stripe (prod) | Vault secret `kv/stripe/prod` | API key in billing service env |
| AI API keys | Vault secret `kv/ai/openai`, `kv/ai/anthropic`, `kv/ai/nim` | Service environment variables |

### 2.3 Infrastructure Topology Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                       │
└───────────────────┬────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────────────────┐
│                      CDN (CloudFront / Cloudflare)                          │
│                    DDoS protection, SSL, static assets                       │
└────────┬──────────────────────────────────────────────┬─────────────────────┘
         │                                              │
┌────────▼────────┐                          ┌─────────▼───────────┐
│  Frontend        │                          │   API Gateway        │
│  Next.js 14      │                          │   FastAPI :8000     │
│  Port 3000       │                          │   GraphQL endpoint   │
└─────────────────┘                          └─────────┬───────────┘
                                                        │
                                ┌───────────────────────┼───────────────────────┐
                                │                       │                       │
                    ┌───────────▼───────────┐  ┌───────▼───────┐  ┌─────────────▼──────┐
                    │   Modular Monolith     │  │ Extracted     │  │   AI Layer          │
                    │   Port 8001            │  │ Microservices │  │                     │
                    │   ┌────────────────┐   │  │               │  │  ┌───────────────┐  │
                    │   │ CRM Module     │   │  │ auth-service  │  │  │ AI Orchestr.  │  │
                    │   │ Marketing      │   │  │ billing-svc   │  │  │ :8010         │  │
                    │   │ Projects       │   │  │ notification  │  │  ┌───────────────┐  │
                    │   │ Knowledge      │   │  │ media-svc     │  │  │ Agent Runtime │  │
                    │   └────────────────┘   │  │ analytics-svc │  │  │ :8011         │  │
                    └────────────────────────┘  │ admin-svc     │  │  ┌───────────────┐  │
                                                │ marketplace   │  │  │ Memory Svc    │  │
                                                │ webhook-svc   │  │  │ :8012         │  │
                                                └───────────────┘  │  ┌───────────────┐  │
                                                                    │  │ NVIDIA NIM    │  │
                                                                    │  │ :8001         │  │
                                                                    │  ┌───────────────┐  │
                                                                    │  │ Ollama        │  │
                                                                    │  │ :11434        │  │
                                                                    └─────────────────────┘
                                │                       │                       │
                                └───────────────┬───────┴───────────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
          ┌─────────▼──────────┐    ┌───────────▼──────────┐   ┌───────────▼──────────┐
          │    PostgreSQL      │    │   Data Layer          │   │   n8n                │
          │    Primary :5432   │    │                       │   │   Workflow Engine    │
          │    Replica :5433   │    │  ┌─────────────────┐  │   │   :5678              │
          │    PgBouncer :6432 │    │  │ Redis Cache     │  │   └──────────────────────┘
          └────────────────────┘    │  │ :6379 (LRU,2GB)│  │
                                    │  │ Sessions :6380  │  │
                                    │  │ Queue :6381     │  │
                                    │  └─────────────────┘  │
                                    │  ┌─────────────────┐  │
                                    │  │ Qdrant          │  │
                                    │  │ :6333 / :6334   │  │
                                    │  └─────────────────┘  │
                                    │  ┌─────────────────┐  │
                                    │  │ MinIO           │  │
                                    │  │ :9000 / :9001   │  │
                                    │  └─────────────────┘  │
                                    │  ┌─────────────────┐  │
                                    │  │ RabbitMQ        │  │
                                    │  │ :5672 / :15672  │  │
                                    │  └─────────────────┘  │
                                    └───────────────────────┘

        ┌─────────────────────────────────────────────────────────────────┐
        │                   Observability Stack                            │
        │   Prometheus :9090 → Grafana :3001 → Loki :3100 → Tempo :4317   │
        └─────────────────────────────────────────────────────────────────┘
```

### 2.4 Key Contacts & Escalation Chain

| Role | Name | Email | Phone | Hours |
|------|------|-------|-------|-------|
| **Primary On-Call** | (Rotating) | oncall@amccloud.com | +1-555-ONCALL | 24/7 |
| **Database Admin** | Alice Chen | alice.chen@amccloud.com | +1-555-DBA-001 | 24/7 |
| **AI Team Lead** | Bob Martinez | bob.martinez@amccloud.com | +1-555-AI-LEAD | 06:00–22:00 UTC |
| **Security Officer** | Carol Williams | carol.williams@amccloud.com | +1-555-SEC-001 | 24/7 (SEV1 security only) |
| **Infra Team Lead** | David Kim | david.kim@amccloud.com | +1-555-INFRA | 24/7 |
| **Engineering Director** | Elena Torres | elena.torres@amccloud.com | +1-555-ENGDIR | Escalation only |
| **VP of Engineering** | Frank Lee | frank.lee@amccloud.com | +1-555-VPENG | Escalation only |
| **CEO** | Grace Chen | grace.chen@amccloud.com | +1-555-CEO | SEV1 customer-facing only |

#### Escalation Chain

```
SEV4 / SEV3 ──→ Primary On-Call
                     │ (unresolved after SLA threshold)
                     ▼
SEV2 ──→ Primary On-Call + Infra Team Lead
                     │ (unresolved after 2 hours)
                     ▼
SEV1 ──→ Primary On-Call + DBA + AI Lead + Infra Lead + Engineering Director
                     │ (customer-facing / revenue impact > 15 min)
                     ▼
          VP Engineering + CEO (if customer-impacting > 1 hour)
```

---

## 3. On-Call Procedures

### 3.1 On-Call Schedule

AMC operates a **follow-the-sun** on-call rotation with two primary regions:

| Region | Coverage Hours | Primary | Secondary |
|--------|---------------|---------|-----------|
| AMER | 06:00–18:00 PT | SRE Team 1 | SRE Team 2 |
| EMEA/APAC | 06:00–18:00 UTC | SRE Team 2 | SRE Team 3 |

- **Rotation length:** 7 days (Monday 09:00 → Monday 09:00 local)
- **Team size:** 4 SREs per team, ensuring 1 primary + 1 secondary always available
- **Schedule tool:** PagerDuty (https://amccloud.pagerduty.com/schedules)
- **Override:** Swap requests must be approved 24h in advance via #ops-schedule Slack channel

#### Handoff Process

1. **Handoff document:** Outgoing on-call creates a handoff doc in Notion (`On-Call Handoff: YYYY-MM-DD`)
2. **Synopsis:** Brief summary of incidents, ongoing investigations, maintenance windows
3. **Knowledge transfer:** Any non-obvious findings from the week
4. **Review runbooks:** Add any new procedures discovered during the week
5. **Dashboard review:** Walk through Grafana dashboards and alert state
6. **Slack notification:** Post handoff summary in #ops-oncall channel
7. **PagerDuty ack:** Confirm shift transfer in PagerDuty

### 3.2 Severity Definitions

| Severity | Label | Definition | Examples |
|----------|-------|------------|----------|
| **SEV1** | 🔴 Critical | Complete platform outage or critical feature unavailable to all users. Revenue impact. Data loss. Security breach. | Full UI down, API returning 500 for all requests, database corruption, confirmed breach |
| **SEV2** | 🟠 Degraded | Major feature unavailable or severely degraded performance for a significant subset of users. | AI agents not responding, campaign sending delayed >30min, high error rate for one service |
| **SEV3** | 🟡 Minor | Partial feature impairment affecting a small number of users. No revenue impact. | Individual tenant issues, non-critical UI bugs, slow but functional pages |
| **SEV4** | 🔵 Informational | Cosmetic issues, minor bugs, monitoring advisory. No user-facing impact. | Stale dashboard metric, non-critical log warning, certificate expiring in >30 days |

### 3.3 Response Time SLAs

| Severity | Acknowledge | Assessment | Mitigation | Fix (permanent) | Update Cadence |
|----------|------------|------------|------------|-----------------|----------------|
| **SEV1** | 5 minutes | 10 minutes | 30 minutes | 4 hours | Every 30 minutes |
| **SEV2** | 15 minutes | 30 minutes | 2 hours | 8 hours | Every 1 hour |
| **SEV3** | 1 hour | 2 hours | 8 hours | 3 days | Every 8 hours |
| **SEV4** | Next business day | Next business day | Next sprint | Next sprint | At resolution |

**Note:** "Mitigation" means making the user-facing impact stop — rolling back a deployment, failing over a database, redirecting traffic. Permanent fix can follow after the fire is out.

### 3.4 Communication Templates

#### SEV1 — Status Page Update

```
## INCIDENT: [Brief Title]
**Severity:** SEV1 — Critical
**Status:** [Investigating / Mitigating / Resolved / Monitoring]
**Started:** YYYY-MM-DD HH:MM UTC
**Last Updated:** YYYY-MM-DD HH:MM UTC

**Impact:** [Description of user-facing impact, % of users affected]

**Root Cause:** [Once known]

**Current Status:**
- [Action taken]
- [Next step]

**Next Update:** YYYY-MM-DD HH:MM UTC
```

#### SEV1 — Slack Message

```
🔴 *SEV1 INCIDENT — [TITLE]*
*Impact:* [users affected, features down]
*Started:* [time] UTC
*Channel:* #inc-[shortid]
*Lead:* @oncall
*Status:* Investigating

PagerDuty has been notified. All hands to #inc-[shortid].
```

#### SEV1 — Email to Leadership

```
Subject: [SEV1] [Title] — [Status]

Severity: SEV1 — Critical
Started: YYYY-MM-DD HH:MM UTC
Duration: X hours Y minutes
Services Affected: [list]
Users Affected: [number / percentage]

Summary:
[2-3 sentence overview]

Impact:
[Detailed impact]

Current Status:
[What we've done and what's next]

Root Cause:
[Once determined]

Next Update: YYYY-MM-DD HH:MM UTC
```

#### SEV2 — Slack Message

```
🟠 *SEV2 DEGRADED — [TITLE]*
*Impact:* [affected functionality]
*Started:* [time] UTC
*Channel:* #inc-[shortid]
*Lead:* @oncall
```

#### SEV3 — Slack Message

```
🟡 *SEV3 MINOR — [TITLE]*
*Details:* [brief description]
*Assigned:* @oncall
*Ticket:* [Jira link]
```

### 3.5 Escalation Matrix

| Condition | Escalate To | Method | Max Wait |
|-----------|------------|--------|----------|
| SEV1 not acknowledged in 5 min | Secondary on-call | PagerDuty + phone | 2 min |
| SEV1 not mitigated in 30 min | Infra Team Lead | PagerDuty + phone | Immediate |
| SEV2 not acknowledged in 15 min | Secondary on-call | PagerDuty | 2 min |
| Database-related incident | DBA (Alice Chen) | Phone + Slack | 5 min |
| AI-related incident | AI Team Lead (Bob Martinez) | Phone + Slack | 10 min |
| Security incident | Security Officer (Carol Williams) | Encrypted channel + phone | Immediate |
| Platform-wide SEV1 > 1 hour | VP Engineering (Frank Lee) | Phone | Immediate |
| Customer-facing SEV1 > 2 hours | CEO (Grace Chen) | Phone | Immediate |
| Unsure about escalation path | Escalate anyway — better safe than sorry | Any channel | — |

### 3.6 Shift Handoff Checklist

Before ending your on-call shift, complete this checklist:

- [ ] All SEV1/SEV2 incidents have post-mortems filed and Jira action items created
- [ ] Open SEV3/SEV4 tickets assigned to the next on-call or appropriate team
- [ ] Handoff document written and posted in #ops-oncall
- [ ] Any new runbook procedures merged via PR
- [ ] PagerDuty schedule confirmed for the next rotation
- [ ] Slack channel #ops-oncall membership current
- [ ] Monitoring dashboards reviewed — no silent fires
- [ ] Backup status confirmed (last backup success, no failures)
- [ ] Known ongoing issues communicated (maintenance windows, gradual rollouts)
- [ ] "What would you have wanted to know at the start of your shift?" documented

---

## 4. Monitoring & Alerting Runbooks

### 4.1 Accessing Observability Tools

#### Grafana

| Environment | URL | Default Credentials |
|-------------|-----|---------------------|
| Development | `http://localhost:3001` | admin / admin |
| Staging | `https://grafana-staging.amccloud.com` | SSO (Okta) |
| Production | `https://grafana.amccloud.com` | SSO (Okta) |

**Key Dashboards:**
- `AMC / Service Overview` — All services health, request rate, error rate, latency
- `AMC / Database` — PostgreSQL connections, query time, replication lag
- `AMC / Redis` — Memory usage, hit rate, command rate
- `AMC / RabbitMQ` — Queue depth, message rate, consumer count
- `AMC / AI Inference` — Model latency, token throughput, GPU utilization
- `AMC / Business Metrics` — Active tenants, campaigns sent, revenue
- `AMC / Kubernetes` — Cluster health, pod status, resource usage

#### Prometheus

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:9090` |
| Staging | `https://prometheus-staging.amccloud.com` |
| Production | `https://prometheus.amccloud.com` |

**Common PromQL Queries:**
```promql
# Service health
up{service="api-gateway"}

# Error rate by service
rate(amc_http_requests_total{status=~"5.."}[5m]) / rate(amc_http_requests_total[5m]) * 100

# P99 latency by endpoint
histogram_quantile(0.99, rate(amc_http_request_duration_seconds_bucket[5m]))

# Queue depth
rabbitmq_queue_messages_ready{queue=~".+"}

# Database connections
pg_stat_activity_count{datname="amc"}
```

#### Loki

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:3100` (Grafana Explore) |
| Staging | Integrated into Grafana (Explore → Loki) |
| Production | Integrated into Grafana (Explore → Loki) |

**Common LogQL Queries:**
```logql
# Errors for a specific service in last hour
{service="api-gateway"} |= "ERROR" | logfmt

# Trace a specific tenant
{service=~".+"} |= "tenant_abc123"

# Find slow queries (> 1s)
{service="monolith"} |= "duration_ms" | logfmt | duration_ms > 1000

# Rate of errors by service
rate({service=~".+"} |= "ERROR"[5m])
```

### 4.2 Alert Runbooks

#### 4.2.1 High API Latency (P99 > 1s)

**Alert Description:** P99 response time for the API gateway exceeds 1 second over a 5-minute window.

**Impact:** User-facing pages load slowly, leading to poor UX and potential churn. Downstream services may also be affected.

**Check:**
1. Open Grafana → `AMC / Service Overview`
2. Identify which endpoint(s) have elevated latency
3. Check if the issue is global or per-tenant
4. Examine downstream dependency latency (DB, Redis, AI, external APIs)
5. Check Loki for slow request traces:
   ```logql
   {service="api-gateway"} | logfmt | duration_ms > 1000 | sort
   ```

**Immediate actions:**
1. If global: Check deployment status — rollback if recently deployed
2. If per-endpoint: Check if it's a DB query, external API, or AI inference
3. If DB-related: Follow [Slow Query Identification](#522-slow-query-identification)
4. If AI-related: Check NVIDIA NIM GPU utilization (`nvidia-smi`)
5. Scale up API gateway: `docker service scale api-gateway=10`

**Resolution:**
- Addressed specific bottleneck (DB index, cache warming, resource scaling)
- Verified P99 back below 500ms

**Verification:**
```promql
histogram_quantile(0.99, rate(amc_http_request_duration_seconds_bucket{service="api-gateway"}[5m]))
```
Should show < 1s for 5 consecutive minutes.

**Post-mortem trigger:** If P99 > 1s for > 15 minutes OR caused by a deployment.

---

#### 4.2.2 High Error Rate (>5% 5xx)

**Alert Description:** Proportion of HTTP 5xx responses exceeds 5% over 5 minutes.

**Impact:** Users receiving errors. Features may be broken. Potential data loss if write operations are failing.

**Check:**
1. Identify which service(s) are returning errors in Grafana
2. Check error distribution by endpoint and status code
3. Examine Loki for error stack traces:
   ```logql
   {service="api-gateway"} |= "5xx" | logfmt
   ```
4. Check dependency health (DB, Redis, RabbitMQ, AI services)
5. Check for recent deployments

**Immediate actions:**
1. If caused by recent deployment → **rollback immediately** (see [Section 10.5](#105-new-deployment-issue--rollback-procedure))
2. If database-related: Check for connection pool exhaustion or deadlocks
3. If AI-related: Check NIM health, GPU, and AI service logs
4. If dependency unavailable: Activate circuit breaker, failover

**Resolution:**
- Rolled back bad deployment
- Restarted unhealthy dependency
- Cleared connection pool

**Verification:**
```promql
rate(amc_http_requests_total{status=~"5.."}[5m]) / rate(amc_http_requests_total[5m]) * 100
```
Below 1% for 5 consecutive minutes.

**Post-mortem trigger:** Any SEV1 error rate event.

---

#### 4.2.3 Database Connection Pool Exhaustion

**Alert Description:** PgBouncer connection pool utilization exceeds 90% of configured `max_client_conn`.

**Impact:** Applications cannot acquire database connections. All dependent services will fail with connection errors. Partial/complete platform outage.

**Check:**
1. Connect to PgBouncer and check pool status:
   ```sql
   SHOW POOLS;
   SHOW STATS;
   ```
2. Check active connections in PostgreSQL:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
   ```
3. Identify idle connections and their source:
   ```sql
   SELECT pid, usename, application_name, client_addr, state, query
   FROM pg_stat_activity
   WHERE state = 'idle' AND query NOT LIKE '%pg_stat%'
   ORDER BY backend_start;
   ```

**Immediate actions:**
1. PgBouncer immediate reset:
   ```bash
   docker compose exec pgbouncer pgbouncer -q reset
   ```
   This drops all client connections — use only in emergencies.
2. Kill idle connections from problematic sources:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
     AND state_change < now() - interval '5 minutes';
   ```
3. Increase connection limits in PgBouncer config:
   ```ini
   max_client_conn = 1000
   default_pool_size = 100
   reserve_pool_size = 20
   ```
   Then reload: `docker compose exec pgbouncer pgbouncer -q reload`

**Resolution:**
- Investigate root cause: connection leaks, increased traffic, misconfigured pool size
- Fix application-side connection management
- Add monitoring on connection usage per service

**Verification:**
```sql
SHOW POOLS;
-- cl_active should be well below max_client_conn
```

**Post-mortem trigger:** Always.

---

#### 4.2.4 Redis Memory High (>80%)

**Alert Description:** Redis memory usage exceeds 80% of `maxmemory` setting.

**Impact:** Redis may begin evicting keys aggressively (cache only) or fail write operations (sessions/queue with `noeviction` policy). Cache hit rate drops, sessions may be lost.

**Check:**
1. Check Redis memory info:
   ```bash
   redis-cli -h redis-cache -a <password> INFO memory
   # Look for: used_memory_human, maxmemory_human, evicted_keys
   ```
2. Find large keys:
   ```bash
   redis-cli -h redis-cache -a <password> --bigkeys
   ```
3. Check memory by key pattern:
   ```bash
   redis-cli -h redis-cache -a <password> --stat
   ```
4. Identify tenants with highest cache usage:
   ```bash
   redis-cli -h redis-cache -a <password> keys 'tenant:*' | head -20
   ```

**Immediate actions:**
1. If `noeviction` policy (redis-sessions, redis-queue) — add memory or remove keys:
   ```bash
   # Check eviction policy
   redis-cli -h redis-sessions -a <password> CONFIG GET maxmemory-policy
   
   # Emergency: change to allkeys-lru to allow eviction (RISK: data loss)
   redis-cli -h redis-sessions -a <password> CONFIG SET maxmemory-policy allkeys-lru
   ```
2. For cache Redis: let LRU eviction work, monitor hit rate
3. Scale up memory limit:
   ```bash
   # Temporarily increase maxmemory (survives restart if saved to redis.conf)
   redis-cli -h redis-cache -a <password> CONFIG SET maxmemory 4gb
   ```
4. Flush stale data:
   ```bash
   # Only if cache data can be rebuilt
   redis-cli -h redis-cache -a <password> FLUSHDB
   ```

**Resolution:**
- Identify the source of increased memory usage (new feature, traffic spike, memory leak)
- Adjust TTLs on cached data
- Add capacity or optimize data structures

**Verification:**
```bash
redis-cli -h redis-cache -a <password> INFO memory | grep -E "used_memory_human|maxmemory_human"
```
Used memory below 70% for 5 minutes.

**Post-mortem trigger:** If memory exceeded 90% or caused service degradation.

---

#### 4.2.5 RabbitMQ Queue Depth Growing

**Alert Description:** One or more RabbitMQ queues have depth exceeding the warning threshold (> 10,000 messages) and growing.

**Impact:** Message processing delay. Campaign sends, notifications, webhooks, AI tasks may be delayed or lost if queue overflows.

**Check:**
1. Open RabbitMQ management UI at `http://<host>:15672`
2. Identify which queues have growing depth
3. Check consumer status (are consumers running? acking messages?)
4. Check for unacked messages (consumers not acking):
   ```bash
   rabbitmqadmin list queues name messages messages_ready messages_unacknowledged
   ```
5. Identify the consuming service and check its logs

**Immediate actions:**
1. Restart the consuming service:
   ```bash
   docker service update --force notification-service
   ```
2. If consumer is stuck on a specific message, skip/remove it:
   ```bash
   # Move messages from main queue to dead letter
   rabbitmqadmin set_queue_operator_policy amc.email.trigger dlq-policy
   ```
3. If queue is critical and consumer can't keep up — purge and regenerate:
   ```bash
   # WARNING: Data loss — only if messages are non-critical or reproducible
   rabbitmqadmin purge queue name=amc.email.trigger
   ```
4. Increase consumer concurrency:
   - Update environment variable `CONSUMER_CONCURRENCY=10` for the affected service
   - Restart the service

**Resolution:**
- Fixed the consumer bug
- Increased consumer capacity
- Re-processed dead-lettered messages

**Verification:**
```bash
rabbitmqadmin list queues name messages
```
All queues should show < 100 messages.

**Post-mortem trigger:** Queue depth > 50,000 or delivery delay > 30 minutes.

---

#### 4.2.6 Qdrant Query Latency High

**Alert Description:** Qdrant query latency (P99) exceeds 500ms.

**Impact:** AI memory retrieval, semantic search, and knowledge base queries are slow. AI agents experience delayed responses. User-facing search is sluggish.

**Check:**
1. Check Qdrant cluster status:
   ```bash
   curl -s http://qdrant:6333/cluster | jq .
   ```
2. Check collection info — segment count is a key metric:
   ```bash
   curl -s http://qdrant:6333/collections/{name} | jq '.result.segments_count'
   ```
3. Check Qdrant logs for slow operations:
   ```bash
   docker logs qdrant --tail 100 | grep -i "slow\|timeout\|error"
   ```
4. Check system resources (CPU, memory, disk I/O) on the Qdrant node

**Immediate actions:**
1. Optimize HNSW parameters for the affected collection:
   ```bash
   curl -X PATCH http://qdrant:6333/collections/{name} \
     -H 'Content-Type: application/json' \
     -d '{
       "hnsw_config": {
         "ef_construct": 100,
         "m": 16
       },
       "optimizers_config": {
         "default_segment_number": 2,
         "memmap_threshold_kb": 20000
       }
     }'
   ```
2. Force segment optimization:
   ```bash
   curl -X POST http://qdrant:6333/collections/{name}/optimize
   ```
3. Add more Qdrant nodes (if clustered)
4. Temporarily reduce search precision:
   ```bash
   curl -X PATCH http://qdrant:6333/collections/{name} \
     -H 'Content-Type: application/json' \
     -d '{"hnsw_config": {"ef": 64}}'
   ```

**Resolution:**
- Optimized segment count (aim for < 10 segments per collection)
- Scaled Qdrant cluster
- Adjusted HNSW parameters for production workload

**Verification:**
```bash
curl -s http://qdrant:6333/collections/{name} | jq '.result'
```
Latency P99 < 200ms.

**Post-mortem trigger:** Latency > 1s for > 15 minutes.

---

#### 4.2.7 AI Provider Down

**Alert Description:** One or more AI providers (OpenAI, Anthropic, NVIDIA NIM) are unreachable or returning errors.

**Impact:** AI agent responses fail or degrade. Features relying on the affected provider (content generation, analysis, agents) are impacted.

**Check:**
1. Check provider health:
   ```bash
   # OpenAI
   curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | head -1
   
   # Anthropic
   curl -s https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
   
   # NVIDIA NIM
   curl -s http://nim:8001/v1/health/ready
   ```
2. Check AI service logs:
   ```logql
   {service=~"ai-orchestrator|ai-agent-runtime"} |= "provider" | logfmt
   ```
3. Check Provider abstraction layer for circuit-breaker status

**Immediate actions:**
1. Automatic failover should route to backup provider — verify:
   - Check the AI provider config at Vault `kv/ai/providers`
   - Verify failover order: OpenAI → Anthropic → Ollama (local fallback)
2. If automatic failover failed, manually force route:
   - Update feature flag `ai_provider_override` via Unleash:
     ```bash
     curl -X PATCH https://unleash:4242/api/admin/projects/default/features/ai_provider_override \
       -H "Authorization: *:*.dev-unleash-token" \
       -d '{"enabled": true, "variants": [{"name": "ollama", "weight": 100}]}'
     ```
3. If using NIM locally, restart the NIM service:
   ```bash
   docker service update --force nim
   ```

**Resolution:**
- Provider restored by vendor or failover completed
- Circuit breaker reset after recovery

**Verification:**
```bash
# Send a test inference
curl -X POST http://ai-orchestrator:8010/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ping"}]}'
```

**Post-mortem trigger:** Always.

---

#### 4.2.8 Certificate Expiring

**Alert Description:** TLS/SSL certificate will expire within 30 days (warning) or 7 days (critical).

**Impact:** If certificate expires, all HTTPS traffic to the affected domain will fail with TLS errors. Complete platform inaccessibility.

**Check:**
1. Check certificate expiry:
   ```bash
   echo | openssl s_client -servername app.amccloud.com -connect app.amccloud.com:443 2>/dev/null | openssl x509 -noout -dates
   ```
2. Check cert-manager logs (if using Let's Encrypt):
   ```bash
   docker logs cert-manager --tail 50
   ```
3. Verify DNS records for ACME challenge domains

**Immediate actions:**
1. Trigger renewal manually:
   ```bash
   # For cert-manager / Let's Encrypt
   kubectl cert-manager renew --all
   
   # For manual certificates
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
     -d app.amccloud.com -d api.amccloud.com
   ```
2. If automated renewal fails:
   - Check DNS propagation
   - Check firewall access to port 80 for ACME challenge
   - Check rate limits (Let's Encrypt: 50 certs/week/domain)
3. Obtain and deploy emergency certificate:
   - Use the break-glass wildcard cert stored in Vault:
   ```bash
   vault read -field=certificate kv/tls/wildcard-amccloud > /tmp/cert.pem
   vault read -field=private_key kv/tls/wildcard-amccloud > /tmp/key.pem
   # Deploy to load balancer / ingress
   ```

**Resolution:**
- Certificate renewed and deployed
- Auto-renewal restored to working order

**Verification:**
```bash
echo | openssl s_client -servername app.amccloud.com -connect app.amccloud.com:443 2>/dev/null | openssl x509 -noout -enddate
```

**Post-mortem trigger:** If certificate expired or critical threshold (< 24h) reached without successful renewal.

---

#### 4.2.9 Disk Space Low (<20%)

**Alert Description:** Disk usage on any node exceeds 80% (warning) or 90% (critical).

**Impact:** Services may crash. Database writes may fail. Logs cannot be written. Pods may be evicted.

**Check:**
1. Check disk usage on the affected node:
   ```bash
   df -h
   ```
2. Identify largest directories:
   ```bash
   du -sh /var/* | sort -rh | head -10
   du -sh /data/* | sort -rh | head -10
   ```
3. Check Docker disk usage:
   ```bash
   docker system df
   ```

**Immediate actions:**
1. Clean Docker resources:
   ```bash
   docker system prune -af --volumes  # WARNING: removes unused volumes
   # Safer alternative:
   docker image prune -af
   docker builder prune -af
   ```
2. Rotate and compress logs:
   ```bash
   # Force log rotation for all containers
   docker exec -t <container> logrotate -f /etc/logrotate.conf
   
   # Or manually truncate large logs
   truncate -s 0 /var/lib/docker/containers/*/*-json.log
   ```
3. Clear temporary files:
   ```bash
   find /tmp -type f -atime +7 -delete
   find /var/tmp -type f -atime +7 -delete
   ```
4. If PostgreSQL WAL is growing:
   ```sql
   SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_receive_lsn()) / 1024 / 1024 AS lag_mb;
   -- Force WAL cleanup if replica is healthy
   SELECT pg_switch_wal();
   ```

**Resolution:**
- Freed sufficient disk space
- Set up log rotation or added storage

**Verification:**
```bash
df -h | grep -E "/data|/var"
```
Below 70% usage.

**Post-mortem trigger:** If disk reached 100% and caused service disruption.

---

#### 4.2.10 Backup Failure

**Alert Description:** Scheduled backup (PostgreSQL, Qdrant, Redis) has failed.

**Impact:** No recent backup available. Recovery point objective (RPO) may be violated. Data at risk.

**Check:**
1. Check backup logs:
   ```bash
   # PostgreSQL pgBackRest
   pgbackrest --stanza=amc check
   
   # Qdrant snapshot
   docker logs qdrant --tail 50 | grep -i "snapshot\|backup\|error"
   
   # MinIO replication status
   mc admin replicate info source/bucket
   ```
2. Check disk space on backup target
3. Check network connectivity to backup storage (S3)

**Immediate actions:**
1. Retry the backup:
   ```bash
   # PostgreSQL
   pgbackrest --stanza=amc --type=full backup
   
   # Qdrant
   curl -X POST "http://qdrant:6333/collections/{name}/snapshots"
   
   # Redis
   redis-cli -h redis-cache -a <password> BGSAVE
   ```
2. If retry fails, create manual backup:
   ```bash
   # Manual pg_dump
   pg_dump -h pgbouncer -U amc -d amc -Fc -f /tmp/manual_backup_$(date +%Y%m%d).dump
   aws s3 cp /tmp/manual_backup_*.dump s3://amc-backups/postgresql/manual/
   ```

**Resolution:**
- Backup completed successfully
- Root cause fixed (disk space, permissions, network)

**Verification:**
```bash
pgbackrest --stanza=amc check
```
"All checks passed."

**Post-mortem trigger:** If backup failure persists > 24 hours.

---

#### 4.2.11 Rate Limit Thresholds Exceeded

**Alert Description:** One or more tenants have exceeded their API rate limit threshold, or the global rate limit is being hit.

**Impact:** Affected tenants receive 429 Too Many Requests. If global limit is hit, all users may experience throttling.

**Check:**
1. Identify the affected tenant(s):
   ```logql
   {service="api-gateway"} |= "429" | logfmt | tenant_id
   ```
2. Check rate limit counters in Redis:
   ```bash
   redis-cli -h redis-cache -a <password> keys "ratelimit:*" | head -20
   redis-cli -h redis-cache -a <password> GET "ratelimit:tenant:abc123"
   ```
3. Check if it's a rogue client or legitimate heavy usage

**Immediate actions:**
1. If a single tenant is the source:
   - Check if it's an API key leak (unusual IPs/user agents)
   - Contact the tenant admin via support channels
   - Temporarily increase rate limit:
     ```bash
     # Via admin API
     curl -X PATCH https://admin.amccloud.com/api/v1/tenants/{tenant_id}/rate-limit \
       -H "Authorization: Bearer $ADMIN_TOKEN" \
       -d '{"rate_limit": 10000}'
     ```
2. If global rate limit is hit:
   - Check for DDoS (see [Section 16.2](#162-ddos-attack))
   - Scale up API gateway instances
   - Verify WAF rules are functioning

**Resolution:**
- Adjusted rate limits appropriately
- Rogue client throttled or blocked

**Verification:**
```logql
{service="api-gateway"} |= "429" | count | unwrap
```
Count of 429s dropping to normal levels.

**Post-mortem trigger:** If caused by misconfiguration or unexpected traffic surge > 10× normal.

---

#### 4.2.12 Unusual Login Spike

**Alert Description:** A sudden spike in login attempts, either globally or for a specific tenant/account.

**Impact:** Could indicate a brute-force attack, credential stuffing, or DDoS on the auth endpoint. Account compromise risk.

**Check:**
1. Check auth service logs:
   ```logql
   {service="auth-service"} |= "login" | logfmt
   ```
2. Check for patterns:
   - Same IP hitting many accounts
   - Same account getting many failed attempts
   - Unusual geographic distribution of login IPs
3. Check failed login rate:
   ```promql
   rate(amc_http_requests_total{endpoint="/auth/login", status="401"}[5m])
   ```

**Immediate actions:**
1. If brute-force detected on a specific account:
   - Temporarily lock the account:
     ```sql
     UPDATE users SET locked_until = now() + interval '1 hour'
     WHERE email = 'target@example.com';
     ```
   - Notify the user to reset password
2. If credential stuffing (many accounts, few IPs):
   - Add IP to WAF block list
   - Enable CAPTCHA on login endpoint (feature flag `login_captcha_enabled`)
   - Rate-limit by source IP:
     ```nginx
     # In ingress config
     limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
     ```
3. If DDoS on auth endpoint:
   - Enable Cloudflare "Under Attack" mode
   - Implement progressive challenge responses

**Resolution:**
- Attack mitigated
- Affected accounts secured
- Rate limiting improved

**Verification:**
```promql
rate(amc_http_requests_total{endpoint="/auth/login", status="200"}[5m])
```
Login rate returned to normal baseline.

**Post-mortem trigger:** Always (security incident).

---

## 5. Database Runbooks (PostgreSQL)

### 5.1 Connection Pool Exhaustion

**Scenario:** Applications receive `FATAL: remaining connection slots are reserved for non-replication superuser connections` or pool is saturated.

#### Check:

```bash
# Check PgBouncer pools
docker compose exec pgbouncer psql -U amc -d amc -c "SHOW POOLS;"
docker compose exec pgbouncer psql -U amc -d amc -c "SHOW STATS;"

# Check active PG connections
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT count(*) AS total_connections,
       count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle') AS idle,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_txn
FROM pg_stat_activity WHERE datname = 'amc';
"
```

#### Clear Idle Connections:

```sql
-- Terminate idle transactions older than 5 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND state_change < now() - interval '5 minutes'
  AND pid <> pg_backend_pid();

-- Terminate all idle connections from a specific application
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE application_name = 'my-app'
  AND state = 'idle'
  AND pid <> pg_backend_pid();
```

#### Scale Up:

1. Increase PgBouncer pool size (minimal restart):
   ```bash
   # Edit deployment/pgbouncer/pgbouncer.ini
   # Change: default_pool_size = 100, max_client_conn = 1000
   
   # Reload without dropping connections
   docker compose exec pgbouncer pgbouncer -q reload
   ```

2. If PostgreSQL itself is hitting `max_connections`:
   ```sql
   -- Check current setting
   SHOW max_connections;
   
   -- Increase temporarily (requires superuser)
   ALTER SYSTEM SET max_connections = 500;
   -- Restart PostgreSQL for this to take effect
   ```

### 5.2 Slow Query Identification

#### Using pg_stat_statements:

```sql
-- Enable if not already enabled (requires restart)
-- shared_preload_libraries = 'pg_stat_statements' in postgresql.conf

-- Top 10 queries by total time
SELECT queryid, LEFT(query, 100) AS query_preview,
       calls, total_exec_time / 1000 AS total_seconds,
       mean_exec_time AS avg_ms,
       rows / calls AS avg_rows,
       shared_blks_hit::float / (shared_blks_hit + shared_blks_read + 1) * 100 AS cache_hit_pct
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY total_exec_time DESC
LIMIT 10;

-- Top 10 by mean time
SELECT queryid, LEFT(query, 100) AS query_preview,
       calls, mean_exec_time AS avg_ms,
       stddev_exec_time AS stddev_ms
FROM pg_stat_statements
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### Explain Analyze a Slow Query:

```sql
-- Get the query from pg_stat_statements
SELECT query FROM pg_stat_statements WHERE queryid = <id>;

-- Run EXPLAIN ANALYZE (careful on prod — use read replica)
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT * FROM contacts WHERE tenant_id = 'abc123' AND email LIKE '%example.com';
```

#### Add Index:

```sql
-- Based on the query pattern found
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_email_trgm
ON contacts USING gin (email gin_trgm_ops)
WHERE deleted_at IS NULL;

-- For common WHERE clauses
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contacts_tenant_status
ON contacts (tenant_id, status)
WHERE deleted_at IS NULL;
```

### 5.3 Replication Lag

#### Check Lag:

```sql
-- On primary
SELECT pg_current_wal_lsn(),
       pg_current_wal_insert_lsn();

-- On replica
SELECT pg_last_wal_receive_lsn(),
       pg_last_wal_replay_lsn(),
       pg_last_xact_replay_timestamp();
       
-- Lag in bytes
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_receive_lsn()) AS receive_lag_bytes,
       pg_wal_lsn_diff(pg_current_wal_lsn(), pg_last_wal_replay_lsn()) AS replay_lag_bytes;
```

```bash
# From shell
docker compose exec postgres-replica psql -U amc -d amc -c "
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
"
```

#### Investigate Causes:

1. Check if replication is running:
   ```sql
   SELECT * FROM pg_stat_replication;
   -- Look for: state='streaming', sync_state='async'|'sync'
   ```

2. Check WAL generation rate on primary:
   ```sql
   SELECT count(*) / 10 AS wal_mb_per_sec
   FROM pg_ls_waldir()
   WHERE modification > now() - interval '10 seconds';
   ```

3. Check for long-running queries on replica that block replay:
   ```sql
   SELECT pid, query, state, backend_start, query_start,
          pg_blocking_pids(pid) AS blocked_by
   FROM pg_stat_activity
   WHERE backend_type = 'client backend'
     AND query NOT LIKE '%pg_stat%'
   ORDER BY query_start;
   ```

#### Failover (if lag is critical and growing):

1. Verify replica is consistent:
   ```sql
   -- On replica
   SELECT pg_is_in_recovery();
   -- Should return 't'
   ```

2. Promote replica to primary:
   ```bash
   docker compose exec postgres-replica psql -U amc -d amc -c "SELECT pg_promote();"
   # Or
   docker compose exec postgres-replica pg_ctl promote
   ```

3. Update PgBouncer to point to the new primary:
   ```bash
   # Update pgbouncer environment
   docker compose exec pgbouncer bash -c "echo 'DB_HOST=new-primary-host' >> /etc/pgbouncer/pgbouncer.ini"
   docker compose exec pgbouncer pgbouncer -q reload
   ```

4. Rebuild the old primary as a replica (once the original primary is back).

### 5.4 Query Lock Contention

#### Identify Blocking Queries:

```sql
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocked_activity.query AS blocked_query,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocking_activity.query AS blocking_query,
       now() - blocked_activity.query_start AS blocked_duration
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_locks.pid = blocked_activity.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocked_locks.locktype = blocking_locks.locktype
  AND blocked_locks.database IS NOT DISTINCT FROM blocking_locks.database
  AND blocked_locks.relation IS NOT DISTINCT FROM blocking_locks.relation
  AND blocked_locks.page IS NOT DISTINCT FROM blocking_locks.page
  AND blocked_locks.tuple IS NOT DISTINCT FROM blocking_locks.tuple
  AND blocked_locks.virtualxid IS NOT DISTINCT FROM blocking_locks.virtualxid
  AND blocked_locks.transactionid IS NOT DISTINCT FROM blocking_locks.transactionid
  AND blocked_locks.classid IS NOT DISTINCT FROM blocking_locks.classid
  AND blocked_locks.objid IS NOT DISTINCT FROM blocking_locks.objid
  AND blocked_locks.objsubid IS NOT DISTINCT FROM blocking_locks.objsubid
  AND blocked_locks.pid <> blocking_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_locks.pid = blocking_activity.pid
WHERE NOT blocked_locks.granted;
```

#### Kill Blocking Query:

```sql
-- Kill the blocking query (does not terminate the connection)
SELECT pg_cancel_backend(<blocking_pid>);

-- Kill the connection entirely (if cancel doesn't work)
SELECT pg_terminate_backend(<blocking_pid>);
```

### 5.5 Database Full

#### Check Disk:

```bash
# On the database host
df -h /var/lib/postgresql/data

# Check database size
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT pg_database_size('amc') / 1024 / 1024 / 1024 AS database_size_gb;
"

# Check largest tables
SELECT schemaname, tablename,
       pg_total_relation_size(schemaname || '.' || tablename) / 1024 / 1024 / 1024 AS total_size_gb,
       pg_relation_size(schemaname || '.' || tablename) / 1024 / 1024 / 1024 AS table_size_gb,
       pg_total_relation_size(schemaname || '.' || tablename) - pg_relation_size(schemaname || '.' || tablename) / 1024 / 1024 / 1024 AS index_size_gb
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 20;
```

#### Extend Volume:

```bash
# If using cloud volume (example: AWS EBS)
# Increase volume size via cloud provider console/CLI
aws ec2 modify-volume --volume-id vol-xxxx --size 500

# Resize filesystem
sudo resize2fs /dev/xvda  # ext4
# OR
sudo xfs_growfs /var/lib/postgresql/data  # xfs
```

#### Archive Old Data:

```sql
-- Archive old campaigns/contacts (example for contacts > 2 years)
BEGIN;
-- Copy to archive table
CREATE TABLE contacts_archived_2024 AS
SELECT * FROM contacts WHERE created_at < '2024-01-01';
-- Delete from main table (in batches to avoid lock issues)
DELETE FROM contacts WHERE created_at < '2024-01-01' AND id IN (
  SELECT id FROM contacts WHERE created_at < '2024-01-01' LIMIT 10000
);
COMMIT;
```

### 5.6 Corrupted Index

#### Identify Corruption:

```sql
-- Check for corrupted indexes
SELECT * FROM pg_amcheck;
-- Or manually: try to query with index
SET enable_seqscan = off;
SELECT count(*) FROM contacts WHERE tenant_id = 'abc123';
-- If this errors, index is likely corrupted
```

#### Reindex Concurrently (no downtime):

```sql
-- Rebuild a single index without locking writes
REINDEX INDEX CONCURRENTLY idx_contacts_tenant_id;

-- Rebuild all indexes on a table
REINDEX TABLE CONCURRENTLY contacts;

-- Rebuild all indexes in a schema
REINDEX SCHEMA CONCURRENTLY public;
```

### 5.7 Migration Failure

#### Rollback:

```bash
# Find the last successful migration
docker compose exec api-gateway alembic history

# Rollback one step
docker compose exec api-gateway alembic downgrade -1

# Rollback to a specific revision
docker compose exec api-gateway alembic downgrade <revision_id>
```

#### Investigate:

```bash
# Check migration logs
docker compose logs api-gateway --tail 100 | grep -i "migration\|alembic"

# Check migration state in the database
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT version_num FROM alembic_version;
"
```

#### Retry:

1. Fix the migration script (bug, data issue)
2. Update the migration revision
3. Apply from clean state:
   ```bash
   docker compose exec api-gateway alembic upgrade head
   ```

### 5.8 Run Manual Queries on Replica vs Primary

```bash
# On Read Replica (for SELECT queries)
docker compose exec postgres-replica psql -U amc -d amc -c "
SELECT count(*) FROM contacts WHERE tenant_id = 'abc123';
"

# On Primary (for writes / DDL)
docker compose exec postgres-primary psql -U amc -d amc -c "
UPDATE contacts SET status = 'active' WHERE id = '123';
"

# Via PgBouncer (transaction-pooled — for application-like queries)
docker compose exec pgbouncer psql -U amc -d amc -c "
SELECT * FROM campaigns WHERE tenant_id = 'abc123' LIMIT 10;
"
```

### 5.9 PgBouncer Restart Procedure

Graceful restart (no connection loss):

```bash
# 1. Suspend PgBouncer (stops accepting new connections, waits for active sessions)
docker compose exec pgbouncer pgbouncer -q suspend

# 2. Check that connections drained
docker compose exec pgbouncer psql -U amc -d amc -c "SHOW POOLS;"

# 3. Reload configuration
docker compose exec pgbouncer pgbouncer -q reload

# 4. Resume accepting connections
docker compose exec pgbouncer pgbouncer -q resume
```

Full restart (brief connection loss):

```bash
docker compose restart pgbouncer
# Wait for health check
docker compose exec pgbouncer bash -c "until pg_isready -U amc; do sleep 1; done"
```

### 5.10 Point-in-Time Recovery (PITR) Step by Step

**Scenario:** Restore PostgreSQL to a specific point in time (e.g., just before a data corruption incident).

```bash
# 1. Stop the application (prevent writes)
docker service scale api-gateway=0 monolith=0

# 2. Identify the target timestamp (UTC)
# PITR_TIME = "2026-06-19 14:23:00 UTC"

# 3. Restore using pgBackRest
pgbackrest --stanza=amc --type=time \
  --target="2026-06-19 14:23:00" \
  --target-action=promote \
  --db-path=/var/lib/postgresql/data \
  restore

# 4. Start PostgreSQL
pg_ctl -D /var/lib/postgresql/data start

# 5. Verify data integrity
psql -U amc -d amc -c "SELECT count(*) FROM contacts;"

# 6. Update PgBouncer config to point to restored DB
docker compose exec pgbouncer pgbouncer -q reload

# 7. Restart application
docker service scale api-gateway=3 monolith=3

# 8. Notify team of restored point-in-time
```

### 5.11 Backup Verification Procedure

```bash
# Daily automated check
pgbackrest --stanza=amc check

# Manual verification — restore to a temporary instance
pgbackrest --stanza=amc --type=none --db-path=/tmp/pg-restore-test restore
pg_ctl -D /tmp/pg-restore-test start -p 5433
psql -p 5433 -U amc -d amc -c "SELECT count(*) FROM contacts;"
pg_ctl -D /tmp/pg-restore-test stop
rm -rf /tmp/pg-restore-test

# Verify WAL archive is complete
pgbackrest --stanza=amc --set=latest check
```

### 5.12 Connection String Rotation

**Scenario:** Rotate database passwords or update connection endpoints.

```bash
# 1. Update Vault secret
vault kv put kv/db/primary password="<new-password>"

# 2. Update PgBouncer auth file
docker compose exec pgbouncer bash -c "
echo 'amc \"<new-password>\"' > /etc/pgbouncer/userlist.txt
"
docker compose exec pgbouncer pgbouncer -q reload

# 3. Update PostgreSQL password
docker compose exec postgres-primary psql -U amc -d amc -c "
ALTER USER amc WITH PASSWORD '<new-password>';
"

# 4. Rotate application connection strings (restart services to pick up new secret)
# Loop through each service
for svc in api-gateway monolith auth-service billing-service notification-service \
           analytics-service admin-service marketplace-service webhook-service; do
  docker service update --detach=false --env-add DATABASE_URL="postgresql://amc:<new-password>@pgbouncer:6432/amc" $svc
done

# 5. Verify connectivity
docker compose exec api-gateway python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Connection OK')
conn.close()
"
```

---

## 6. Redis Runbooks

### 6.1 Memory Usage High

#### Identify Large Keys:

```bash
# Scan for big keys (sample-based, may miss some)
redis-cli -h redis-cache -a <password> --bigkeys

# Manual scan by type
redis-cli -h redis-cache -a <password> --scan --pattern '*' | while read key; do
  type=$(redis-cli -h redis-cache -a <password> TYPE "$key")
  case $type in
    string) size=$(redis-cli -h redis-cache -a <password> STRLEN "$key");;
    list)   size=$(redis-cli -h redis-cache -a <password> LLEN "$key");;
    set)    size=$(redis-cli -h redis-cache -a <password> SCARD "$key");;
    hash)   size=$(redis-cli -h redis-cache -a <password> HLEN "$key");;
    zset)   size=$(redis-cli -h redis-cache -a <password> ZCARD "$key");;
  esac
  echo "$type|$size|$key"
done | sort -t'|' -k2 -rn | head -20
```

#### Evict Keys:

```bash
# If maxmemory-policy allows eviction, it happens automatically
# Check eviction count
redis-cli -h redis-cache -a <password> INFO stats | grep evicted_keys

# Manual eviction of specific patterns
redis-cli -h redis-cache -a <password> --scan --pattern 'temp:*' | xargs redis-cli -h redis-cache -a <password> DEL

# Force LRU eviction (if allkeys-lru policy)
redis-cli -h redis-cache -a <password> CONFIG SET maxmemory 80%
```

#### Scale Up:

```bash
# Temporarily increase maxmemory
redis-cli -h redis-cache -a <password> CONFIG SET maxmemory 4gb

# Permanent: update docker-compose.yml and redeploy
# Change: --maxmemory 4gb
```

### 6.2 Latency Spike

#### Slow Log Analysis:

```bash
# Get current slow log configuration
redis-cli -h redis-cache -a <password> CONFIG GET slowlog-log-slower-than

# Read the slow log (100 most recent entries)
redis-cli -h redis-cache -a <password> SLOWLOG GET 100

# Format nicely
redis-cli -h redis-cache -a <password> --intrinsic-latency 100
```

#### Big Key Detection:

```bash
# Using redis-cli
redis-cli -h redis-cache -a <password> --bigkeys

# Check for keys with high TTL that should have expired
redis-cli -h redis-cache -a <password> --scan --pattern '*' | while read key; do
  ttl=$(redis-cli -h redis-cache -a <password> TTL "$key")
  if [ "$ttl" -gt 86400 ]; then
    echo "$key has TTL of $ttl seconds"
  fi
done
```

### 6.3 Cluster Failover

**Scenario:** Redis cluster node is unhealthy, needs manual failover.

```bash
# Check cluster nodes
redis-cli -h redis-cache -a <password> CLUSTER NODES

# Check node health
redis-cli -h redis-cache -a <password> CLUSTER INFO

# Manual failover to replica
redis-cli -h redis-replica -a <password> CLUSTER FAILOVER

# Remove dead node (if node is truly gone)
redis-cli -h redis-cache -a <password> CLUSTER FORGET <node-id>

# Add new node
redis-cli -h redis-cache -a <password> CLUSTER MEET <new-node-ip> <new-node-port>
```

### 6.4 Cache Miss Storm

**Scenario:** A popular key expires, causing many simultaneous requests to miss cache and hit the database.

#### Check:

```bash
# Check cache hit ratio
redis-cli -h redis-cache -a <password> INFO stats | grep -E "keyspace_hits|keyspace_misses"

# Calculate hit rate: keyspace_hits / (keyspace_hits + keyspace_misses) * 100
```

#### Immediate Actions:

1. **Gradual warmup** — Re-populate cache slowly to avoid thundering herd:
   ```python
   # Backend code pattern
   import random
   import time
   
   def get_with_gradual_warmup(key, ttl, compute_fn):
       cached = redis.get(key)
       if cached:
           return cached
       
       # Add jitter to avoid simultaneous recompute
       time.sleep(random.uniform(0, 0.5))
       
       # Use SET NX to ensure only one process recomputes
       lock = redis.set(f"lock:{key}", "1", nx=True, ex=10)
       if lock or cached := redis.get(key):
           value = compute_fn()
           redis.setex(key, ttl, value)
           return value
       else:
           # Wait for the other process
           time.sleep(0.5)
           return redis.get(key)
   ```

2. **Pre-warm critical keys** manually:
   ```bash
   # Run cache-warming script
   docker compose exec monolith python scripts/warm_cache.py
   ```
3. Increase database connection pool temporarily to handle the load

### 6.5 Redis Restart (Graceful with Persistence)

**Scenario:** Planned restart for maintenance or config change.

```bash
# 1. Trigger a save to ensure persistence
redis-cli -h redis-cache -a <password> SAVE

# 2. Wait for save to complete (check last save time)
redis-cli -h redis-cache -a <password> LASTSAVE

# 3. Restart
docker compose restart redis-cache

# 4. Verify data loaded from persistence
redis-cli -h redis-cache -a <password> DBSIZE
# Should show keys from before restart

# 5. Verify AOF replay (if using appendonly)
redis-cli -h redis-cache -a <password> INFO persistence | grep aof
```

### 6.6 AOF Rewrite Failure

#### Check:

```bash
# Check AOF status
redis-cli -h redis-cache -a <password> INFO persistence

# Look for: aof_rewrite_in_progress, aof_last_bgrewrite_status
```

#### Immediate Actions:

```bash
# Check disk space first
df -h /data

# Force AOF rewrite
redis-cli -h redis-cache -a <password> BGREWRITEAOF

# Check progress
redis-cli -h redis-cache -a <password> INFO persistence | grep aof_rewrite

# If still failing, disable and re-enable AOF
redis-cli -h redis-cache -a <password> CONFIG SET appendonly no
redis-cli -h redis-cache -a <password> CONFIG SET appendonly yes
```

---

## 7. Qdrant Runbooks

### 7.1 High Query Latency

#### Check:

```bash
# Check collection info
curl -s http://qdrant:6333/collections/{name} | jq '.'

# Pay attention to:
# - segments_count: should be < 10 per collection
# - status: should be "green"
# - points_count

# Check Qdrant metrics
curl -s http://qdrant:6333/metrics | grep -E "qdrant_|segment"

# Check system resources
docker stats qdrant --no-stream
```

#### Optimize HNSW:

```bash
# Tune HNSW parameters based on workload
curl -X PATCH http://qdrant:6333/collections/{name} \
  -H 'Content-Type: application/json' \
  -d '{
    "hnsw_config": {
      "m": 32,
      "ef_construct": 200,
      "full_scan_threshold": 10000,
      "max_indexing_threads": 2,
      "payload_m": 16
    },
    "optimizers_config": {
      "default_segment_number": 2,
      "memmap_threshold_kb": 20000,
      "flush_interval_sec": 60,
      "max_optimization_threads": 4
    }
  }'
```

#### Force Segment Optimization:

```bash
# Trigger optimization
curl -X POST http://qdrant:6333/collections/{name}/optimize

# Check optimization status
curl -s http://qdrant:6333/collections/{name} | jq '.result.optimizers_status'
```

#### Add Resources:

```bash
# Scale up Qdrant (if using Docker Swarm / K8s)
docker service update --limit-cpu 8 --limit-memory 16gb qdrant

# Or add more Qdrant nodes to the cluster
```

### 7.2 Replica Lag / Sync Issues

#### Check Cluster Status:

```bash
curl -s http://qdrant:6333/cluster | jq '.'
# Look for: "status", "peer_id", "raft_info"
```

#### Force Sync:

```bash
# Force full snapshot sync from another replica
# On the lagging node:
curl -X POST http://qdrant-lagging:6333/cluster/recover \
  -H 'Content-Type: application/json' \
  -d '{"recover_from_peer": "<healthy-peer-id>"}'
```

### 7.3 Snapshot Backup Failure

#### Check:

```bash
# Check disk space
df -h /qdrant/storage

# Check Qdrant logs
docker logs qdrant --tail 50 | grep -i "snapshot\|error\|fail"

# Check snapshot directory permissions
ls -la /qdrant/storage/snapshots/
```

#### Retry:

```bash
# Manually trigger snapshot
curl -X POST "http://qdrant:6333/collections/{name}/snapshots"

# If successful, upload to backup storage
SNAPSHOT_NAME=$(curl -s http://qdrant:6333/collections/{name}/snapshots | jq -r '.result[-1].name')
curl -s "http://qdrant:6333/collections/{name}/snapshots/$SNAPSHOT_NAME" \
  | aws s3 cp - "s3://amc-backups/qdrant/{name}/$(date +%Y%m%d).snapshot"
```

### 7.4 Collection Corruption

#### Check:

```bash
# Check collection health
curl -s http://qdrant:6333/collections/{name} | jq '.result.status'
# If "status" is "red" or "error", collection is corrupted

# Check for error messages
docker logs qdrant --tail 100 | grep -i "corrupt\|error\|panic"
```

#### Restore from Snapshot:

```bash
# 1. List available snapshots
curl -s http://qdrant:6333/collections/{name}/snapshots | jq '.'

# 2. Download the latest valid snapshot
LATEST_SNAPSHOT=$(aws s3 ls s3://amc-backups/qdrant/{name}/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://amc-backups/qdrant/{name}/$LATEST_SNAPSHOT /tmp/

# 3. Delete corrupted collection
curl -X DELETE http://qdrant:6333/collections/{name}

# 4. Recreate collection configuration
curl -X PUT http://qdrant:6333/collections/{name} \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'

# 5. Upload snapshot data
curl -X POST http://qdrant:6333/collections/{name}/snapshots/upload \
  -F "snapshot=@/tmp/$LATEST_SNAPSHOT"

# 6. Rebuild index
curl -X POST http://qdrant:6333/collections/{name}/optimize
```

### 7.5 Qdrant Cluster Member Down

#### Remove Dead Node:

```bash
# Identify the dead node
curl -s http://qdrant:6333/cluster | jq '.result.peers'

# Remove from cluster
curl -X DELETE http://qdrant:6333/cluster/peer/{peer_id}
```

#### Rejoin Node:

```bash
# On the recovered node
curl -X POST http://qdrant-recovered:6333/cluster/recover \
  -H 'Content-Type: application/json' \
  -d '{"recover_from_peer": "<any-healthy-peer-id>"}'

# Verify rejoin
curl -s http://qdrant:6333/cluster | jq '.result.peers'
```

---

## 8. RabbitMQ Runbooks

### 8.1 Queue Depth Growing

#### Check:

```bash
# List queues with depth
rabbitmqadmin list queues name messages messages_ready messages_unacknowledged consumers

# Check consumers and their status
rabbitmqadmin list consumers queue channel_details.node channel_details.peer_host
```

#### Identify Consumer Issue:

```bash
# Check consumer logs
docker logs notification-service --tail 100 | grep -i "message\|error\|timeout"

# Check if consumer is alive and acking
rabbitmqadmin list queues name messages_unacknowledged consumers
# If messages_unacknowledged is high, consumers are not acking
```

#### Restart Consumer:

```bash
# Force restart the consumer service
docker service update --force notification-service
# or
docker compose restart notification-service
```

#### Purge Queue (if needed):

```bash
# WARNING: Irreversible data loss — only if messages are non-critical
rabbitmqadmin purge queue name=amc.email.trigger

# Or via HTTP API
curl -u amc:password -X DELETE http://rabbitmq:15672/api/queues/%2F/amc.email.trigger/contents
```

### 8.2 Dead Letter Queue Growing

#### Investigate Failed Messages:

```bash
# Check DLQ (dead letter queue)
rabbitmqadmin get queue=amc.email.trigger.dlq --count=10 --payload

# Get dead letter headers (why it failed)
rabbitmqadmin get queue=amc.email.trigger.dlq --count=5 --payload-encoding=auto | jq '.properties.headers'
```

#### Reprocess Messages:

```bash
# Move messages from DLQ back to main queue
# Option 1: Use shovel plugin
rabbitmqctl set_parameter shovel reprocess-dlq \
  '{"src-queue": "amc.email.trigger.dlq", "dest-queue": "amc.email.trigger"}'

# Option 2: Manual move via admin tool
python scripts/reprocess_dlq.py --source amc.email.trigger.dlq --dest amc.email.trigger
```

### 8.3 RabbitMQ Node Down

#### Detect:

```bash
# Check node status
rabbitmqctl node_health_check
# or
rabbitmqctl cluster_status

# Check management UI
curl -u amc:password http://rabbitmq:15672/api/nodes
```

#### Promote Mirror:

```bash
# In a mirrored queue setup, promotion is automatic
# Verify mirror status
rabbitmqctl list_queues name policy slave_nodes synchronised_slave_nodes
```

#### Restart Failed Node:

```bash
# Restart RabbitMQ
docker compose restart rabbitmq

# Wait for sync
rabbitmqctl await_startup
rabbitmqctl cluster_status

# Verify all queues are backed up
rabbitmqctl list_queues name slave_nodes synchronised_slave_nodes
```

### 8.4 Connection Limit Reached

#### Check:

```bash
# Check current connections
rabbitmqctl list_connections name user host port state

# Count connections
rabbitmqctl list_connections | wc -l

# Check configured limit
rabbitmqctl environment | grep connection_max
```

#### Increase Limit:

```bash
# Increase global connection limit
rabbitmqctl set_vm_memory_high_watermark 0.8

# Increase connection limit
rabbitmqctl set_channel_max 2048

# Or in rabbitmq.conf:
# channel_max = 2048
# connection_max = 2048
```

#### Identify Leaky Connections:

```bash
# List connections by service with count
rabbitmqctl list_connections name client_properties | grep -oP '(?<="service":")\w+' | sort | uniq -c | sort -rn

# Force close leaky connections
rabbitmqctl close_connection "<connection-name>" "Connection limit reached — closing leaky connection"
```

### 8.5 Message Rate Spike

#### Investigate Source:

```bash
# Check message rates per queue
rabbitmqadmin list queues name message_stats.publish_details.rate message_stats.deliver_details.rate

# Identify source service
rabbitmqctl list_connections name channel_max client_properties

# Check if it's expected (feature launch, campaign) or anomalous (bug, attack)
```

#### Throttle if Needed:

```bash
# Set queue max length (overflow drops oldest messages)
rabbitmqctl set_policy throttle-queue "^amc\.email\." '{"max-length":50000,"overflow":"drop-head"}' --apply-to queues

# Or limit publish rate per connection
rabbitmqctl set_rate_limit amc.email.trigger 1000/s
```

---

## 9. MinIO Runbooks

### 9.1 Disk Space Critical

#### Identify Large Buckets:

```bash
# List buckets with disk usage
mc du source/
# or
mc du --recursive source/ | sort -rh | head -10

# Check per-bucket sizes
mc admin info source/ | grep -E "Bucket|Size"
```

#### Apply Lifecycle Policy:

```bash
# Example: expire objects older than 90 days in temporary bucket
mc ilm rule add source/amc-uploads --expire-days 90

# Check current lifecycle rules
mc ilm rule list source/amc-uploads
```

#### Add Storage:

```bash
# Add a new disk to the MinIO cluster
# On new node:
minio server /data1 /data2 --console-address ":9001"
```

### 9.2 Bucket Access Error

#### Check Permissions:

```bash
# Check bucket policy
mc policy get source/amc-assets

# Set bucket policy (example: public read)
mc policy set public source/amc-assets

# Check user/credentials
mc admin user list source/
mc admin user info source/ <username>
```

#### Check Bucket Policy:

```bash
# List bucket policies
mc policy list source/amc-assets

# Set policy JSON
cat > bucket-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::amc-assets/*"]
    }
  ]
}
EOF
mc policy import source/amc-assets bucket-policy.json
```

### 9.3 Replication Failure

#### Check Connectivity:

```bash
# Check replication status
mc admin replicate info source/bucket

# Check remote endpoint connectivity
mc ping remote-endpoint

# Check for errors in MinIO logs
docker logs minio --tail 50 | grep -i "replication\|error"
```

#### Re-trigger Sync:

```bash
# Re-sync a bucket
mc admin replicate sync source/bucket --remote-bucket bucket --remote-endpoint https://dr-region.s3.amazonaws.com

# Check sync status
mc admin replicate status source/bucket
```

### 9.4 Object Corruption

#### Check:

```bash
# Verify object integrity
mc stat source/amc-assets/path/to/file

# Check for checksum mismatches
mc ls --versions source/amc-assets/path/to/file
```

#### Restore from Backup or Replica:

```bash
# Option 1: Restore from cross-region replica
mc cp remote/amc-assets/path/to/file source/amc-assets/path/to/file

# Option 2: Restore from MinIO backup
mc ls s3://amc-backups/minio/amc-assets/
mc cp s3://amc-backups/minio/amc-assets/path/to/file source/amc-assets/path/to/file

# Option 3: Version recovery (if versioning enabled)
mc rm source/amc-assets/path/to/file  # Remove corrupted version
mc cp source/amc-assets/path/to/file --version-id <previous-version-id> /tmp/restored
mc cp /tmp/restored source/amc-assets/path/to/file
```

---

## 10. Application Service Runbooks

### 10.1 Service Crash / Restart Loop

#### Check Logs:

```bash
# View recent logs
docker logs <service-name> --tail 100

# Follow logs
docker logs <service-name> --tail 50 --follow

# Check for panic/exception/fatal
docker logs <service-name> --tail 200 | grep -E "PANIC|panic|FATAL|fatal|ERROR|Traceback|Segmentation"
```

#### Check Resource Limits:

```bash
# Check memory/CPU usage
docker stats <service-name> --no-stream

# Check OOM scores
cat /proc/<container-pid>/oom_score
# If > 500, OOM killer may target it

# Check for OOM in syslog
journalctl -k | grep -i "oom\|killed"
```

#### Check Dependencies:

```bash
# Test database connectivity
docker compose exec <service> python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('DB: OK')
conn.close()
"

# Test Redis connectivity
docker compose exec <service> redis-cli -h redis-cache -a <password> ping

# Test RabbitMQ
docker compose exec <service> python -c "
import pika, os
params = pika.URLParameters(os.environ['RABBITMQ_URL'])
conn = pika.BlockingConnection(params)
print('RabbitMQ: OK')
conn.close()
"
```

### 10.2 Health Check Failing

#### Deep Dive into Dependencies:

```bash
# Check the health endpoint directly
curl -v http://<service>:<port>/health

# Check dependent services health
for dep in pgbouncer redis-cache rabbitmq qdrant; do
  curl -s http://$dep:<port>/health && echo " $dep: OK" || echo " $dep: FAIL"
done

# Check if service-specific dependency is down (e.g., AI model)
curl -s http://nim:8001/v1/health/ready
```

#### Connectivity Check:

```bash
# DNS resolution
docker compose exec <service> nslookup redis-cache
docker compose exec <service> nslookup pgbouncer

# Port connectivity
docker compose exec <service> bash -c "timeout 5 bash -c 'echo >/dev/tcp/pgbouncer/6432' && echo 'Port open' || echo 'Port closed'"
```

### 10.3 Memory Leak

#### Heap Dump (Python):

```bash
# Install heapy or dump_trace
docker compose exec <service> pip install guppy3

# Run heap dump
docker compose exec <service> python -c "
from guppy import hpy
hp = hpy()
print(heap := hp.heap())
heap.dump('/tmp/heap_$(date +%Y%m%d_%H%M%S).hpy')
"
```

#### Thread Dump:

```bash
# Python thread dump
docker compose exec <service> python -c "
import threading, sys, traceback
for thread_id, frame in sys._current_frames().items():
    name = threading.enumerate()[thread_id].name if thread_id < len(threading.enumerate()) else 'Unknown'
    print(f'Thread {thread_id} ({name}):')
    traceback.print_stack(frame)
    print()
"
# Or send SIGQUIT to the process
docker kill --signal=QUIT <container-id>
```

#### Increase Memory Temporarily:

```bash
# For Docker Swarm
docker service update --limit-memory 4g <service>

# For Docker Compose
# Update docker-compose.yml: mem_limit: 4g
docker compose up -d <service>
```

### 10.4 Slow Endpoint

#### Identify Bottleneck:

```bash
# Use distributed tracing (Tempo)
# Check trace in Grafana Explore → Tempo
# Look for spans with high duration

# Check if it's a DB query
# 1. Enable query logging
docker compose exec pgbouncer psql -U amc -d amc -c "
SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;
"

# 2. Check slow queries
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT LEFT(query, 100) AS query, calls, mean_exec_time AS avg_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 5;
"
```

#### Check Cache Hit Rate:

```bash
redis-cli -h redis-cache -a <password> INFO stats | grep -E "keyspace_hits|keyspace_misses"
# Hit rate should be > 90%
```

#### Check External API:

```bash
# Trace external API call latency
docker compose exec <service> python -c "
import time, requests
start = time.time()
r = requests.get('https://api.external.com/endpoint')
duration = time.time() - start
print(f'External API: {r.status_code} in {duration*1000:.0f}ms')
"
```

#### Check AI Inference:

```bash
# Test NIM latency
time curl -X POST http://nim:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "meta/llama3-8b-instruct", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'
```

### 10.5 New Deployment Issue — Rollback Procedure

**Scenario:** A deployment caused errors, increased latency, or service instability.

```bash
# Step 1: Identify the previous stable version
docker service ps <service-name> | grep -v "Shutdown" | head -5

# Step 2: Rollback using Docker Swarm
docker service rollback <service-name>

# Step 3: Or manually deploy the previous image
# First, find the previous image tag
git log --oneline -5  # Find the previous deploy commit
# Check registry for the previous tag
docker service update --image ghcr.io/amccloud/<service>:<previous-tag> <service>

# Step 4: Verify rollback succeeded
docker service ps <service-name>
curl -f http://<service>:<port>/health && echo "Health check passed"

# Step 5: Verify in staging first (if possible)
# Deploy the fix to staging, validate, then promote to production

# Step 6: Add a tag to the broken deployment for post-mortem
git tag broken-deploy-$(date +%Y%m%d) <broken-sha>
git push origin --tags
```

### 10.6 Feature Flag Toggle Procedure

**Tools:** Unleash feature flag server at `https://unleash:4242`

#### Toggle a Feature Flag:

```bash
# Via Unleash Admin API
curl -X PATCH https://unleash:4242/api/admin/projects/default/features/<flag-name> \
  -H "Authorization: <unleash-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "strategies": [
      {
        "name": "gradualRollout",
        "parameters": {
          "percentage": "50",
          "groupId": "<flag-name>"
        }
      }
    ]
  }'
```

#### Kill Switch (Emergency Disable):

```bash
# Disable a feature immediately for all users
curl -X PATCH https://unleash:4242/api/admin/projects/default/features/<flag-name> \
  -H "Authorization: <unleash-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

### 10.7 Cache Invalidation (Redis + CDN)

#### Redis Cache Invalidation:

```bash
# Invalidate by pattern
redis-cli -h redis-cache -a <password> --scan --pattern 'tenant:abc123:*' | xargs redis-cli -h redis-cache -a <password> DEL

# Invalidate by tag (if using tagged cache)
redis-cli -h redis-cache -a <password> DEL "tag:tenant:abc123:campaigns"
redis-cli -h redis-cache -a <password> DEL "tag:global:features"
```

#### CDN Cache Invalidation:

```bash
# CloudFront invalidation
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"

# Cloudflare API purge
curl -X POST https://api.cloudflare.com/client/v4/zones/<zone-id>/purge_cache \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"purge_everything": true}'
```

---

## 11. AI Service Runbooks

### 11.1 AI Provider Down

#### Automatic Failover:

The AI layer has built-in failover: OpenAI → Anthropic → Ollama (local). The failover order is configured in Vault at `kv/ai/providers`.

```json
// Expected provider config
{
  "providers": [
    {"name": "openai", "weight": 70, "model": "gpt-4o-mini"},
    {"name": "anthropic", "weight": 20, "model": "claude-3-haiku"},
    {"name": "ollama", "weight": 10, "model": "llama3.2:3b"}
  ],
  "fallback_order": ["openai", "anthropic", "ollama"]
}
```

#### Manual Force Route to Backup:

```bash
# Step 1: Check current provider status
curl -s http://ai-orchestrator:8010/v1/providers/status | jq '.'

# Step 2: Force route to Anthropic
curl -X POST http://ai-orchestrator:8010/v1/providers/force \
  -H 'Content-Type: application/json' \
  -d '{"provider": "anthropic", "model": "claude-3-haiku-20240307"}'

# Step 3: Or fall back all to Ollama (local, no external dependency)
curl -X POST http://ai-orchestrator:8010/v1/providers/force \
  -H 'Content-Type: application/json' \
  -d '{"provider": "ollama", "model": "llama3.2:3b"}'

# Step 4: Verify routing
curl -s http://ai-orchestrator:8010/v1/providers/status | jq '.active_provider'
```

### 11.2 High AI Latency

#### Check NVIDIA NIM:

```bash
# Check NIM health
curl -s http://nim:8001/v1/health/ready

# Check NIM model status
curl -s http://nim:8001/v1/models | jq '.'

# Check NIM metrics
curl -s http://nim:8001/metrics | grep -E "nv_inference|request_duration"
```

#### Check GPU Utilization:

```bash
# On GPU node
nvidia-smi

# Check GPU metrics in Prometheus
# nvidia_gpu_duty_cycle, nvidia_memory_used_bytes

# Check GPU memory
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader
```

#### Scale GPU:

```bash
# Add more GPU workers (if using K8s)
kubectl scale deployment nim --replicas=2

# Or increase GPU per node (if using MIG)
nvidia-smi mig -cgi 1g.10gb -C
```

### 11.3 AI Responses Degrading

#### Prompt Drift Investigation:

```bash
# Step 1: Compare response quality over time
# Check the prompt template version in Vault
vault read kv/ai/prompts/agent-marketing-director

# Step 2: List recent prompt changes
git log --oneline --all -- backend/ai/prompts/

# Step 3: A/B test old vs new prompt
curl -X POST http://ai-orchestrator:8010/v1/prompts/test \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt_version_a": "v1.0",
    "prompt_version_b": "v2.1",
    "test_input": "Write an email campaign for product launch"
  }'
```

#### Rollback Prompts:

```bash
# Step 1: List available prompt versions
curl -s http://ai-orchestrator:8010/v1/prompts/versions | jq '.'

# Step 2: Rollback to previous known-good version
curl -X POST http://ai-orchestrator:8010/v1/prompts/rollback \
  -H 'Content-Type: application/json' \
  -d '{"prompt_name": "agent-marketing-director", "version": "v1.0"}'

# Step 3: Verify
curl -s http://ai-orchestrator:8010/v1/prompts/active | jq '.'
```

### 11.4 Token Usage Spike

#### Investigate:

```bash
# Check token usage by tenant
curl -s http://ai-orchestrator:8010/v1/metrics/tokens | jq '.'

# Check for unusual activity
docker logs ai-orchestrator --tail 200 | grep -i "token\|usage\|cost"

# Check Loki
{service=~"ai-orchestrator|ai-agent-runtime"} |= "token_usage"
```

#### Cap at Tenant Level:

```bash
# Set token limit per tenant
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/{tenant_id}/ai-limits \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"daily_token_limit": 1000000, "monthly_token_limit": 30000000}'
```

#### Alert Customer:

```bash
# Trigger notification via admin API
curl -X POST https://admin.amccloud.com/api/v1/tenants/{tenant_id}/notifications \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"type": "token_usage_warning", "message": "Your AI token usage has exceeded 80% of your monthly limit."}'
```

### 11.5 Agent Stuck in Loop

#### Detect:

```bash
# Check active agent executions
curl -s http://ai-orchestrator:8010/v1/executions/active | jq '.'

# Look for executions with high iteration count
curl -s http://ai-orchestrator:8010/v1/executions/active | jq '.executions[] | select(.iterations > 10)'
```

#### Force Kill Execution:

```bash
# Kill a specific execution
curl -X POST http://ai-orchestrator:8010/v1/executions/{execution_id}/kill \
  -H 'Content-Type: application/json'

# Kill all active executions for a tenant
curl -X POST http://ai-orchestrator:8010/v1/executions/kill-by-tenant \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id": "abc123"}'

# Kill all (emergency)
docker service scale ai-agent-runtime=0
docker service scale ai-agent-runtime=2  # Restart
```

#### Investigate Root Cause:

```bash
# Check the agent's execution trace
curl -s http://ai-orchestrator:8010/v1/executions/{execution_id}/trace | jq '.'

# Check if a tool returned unexpected results
# Check if the agent's prompt caused a loop
vault read kv/ai/prompts/agent-{name}
```

### 11.6 Model Deployment — Rolling Model Update

```bash
# Step 1: Upload new model to NIM
# (Follow NVIDIA NIM documentation for your model)

# Step 2: Deploy to a canary instance first
docker service update \
  --image nvcr.io/nvidia/nim:new-model-version \
  --replicas 1 \
  nim-canary

# Step 3: Run validation tests
curl -X POST http://nim-canary:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "new-model", "messages": [{"role": "user", "content": "Test"}], "max_tokens": 50}'

# Step 4: Gradual rollout to production
docker service update \
  --image nvcr.io/nvidia/nim:new-model-version \
  --update-parallelism 1 \
  --update-delay 30s \
  nim

# Step 5: Monitor for regressions
# Check: token throughput, latency, response quality scores

# Step 6: If issues, rollback
docker service rollback nim
```

### 11.7 GPU Node Failure

#### Reschedule:

```bash
# If using K8s — pods auto-reschedule if node is unhealthy
# If using Swarm — check service status
docker service ps nim

# Manually reschedule
docker service update --force nim
```

#### Failover to CPU Fallback:

```bash
# Enable CPU-only inference mode
curl -X POST http://ai-orchestrator:8010/v1/failover/cpu \
  -H 'Content-Type: application/json' \
  -d '{"enabled": true}'

# This routes all NIM requests to Ollama running on CPU
# Verify with:
curl -s http://ai-orchestrator:8010/v1/providers/status | jq '.active_provider'
```

---

## 12. n8n Workflow Runbooks

### 12.1 Workflow Execution Stuck

#### Check:

```bash
# List active executions
curl -s http://n8n:5678/rest/executions?status=running \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.'
```

#### Force Kill:

```bash
# Stop a specific execution
curl -X POST http://n8n:5678/rest/executions/{execution_id}/stop \
  -H "X-N8N-API-KEY: $N8N_API_KEY"

# Or via n8n UI → Executions → Select → Stop
```

#### Restart:

```bash
# Restart the n8n service
docker compose restart n8n

# Check workflow state after restart
curl -s http://n8n:5678/healthz
```

### 12.2 High Workflow Failure Rate

#### Identify Failing Nodes:

```bash
# Get failed executions
curl -s http://n8n:5678/rest/executions?status=error&limit=10 \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[].workflowName'

# View execution error details
curl -s http://n8n:5678/rest/executions/{execution_id} \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data.resultData.error'
```

#### Fix Permissions/Credentials:

```bash
# Check credential expiry
curl -s http://n8n:5678/rest/credentials \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {name, type, id}'

# Test a credential
curl -X POST http://n8n:5678/rest/credentials/{id}/test \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

### 12.3 n8n Service Down

#### Restart:

```bash
docker compose restart n8n

# Check n8n database health
curl -s http://n8n:5678/healthz

# Check n8n database connection
docker compose exec n8n n8n db:check

# Check Redis (if n8n uses Redis for queue)
redis-cli -h redis-queue -a <password> ping
```

#### Check Database:

```bash
# Check n8n's PostgreSQL database
docker compose exec postgres-primary psql -U amc -d amc_n8n -c "
SELECT count(*) FROM workflow_entity;
SELECT state, count(*) FROM execution_entity GROUP BY state;
"
```

### 12.4 Credential Rotation for n8n

```bash
# Step 1: Decrypt current credentials (if needed for migration)
# Credentials are encrypted at rest in the database

# Step 2: Update the credential via API
curl -X PATCH http://n8n:5678/rest/credentials/{credential_id} \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AWS Production",
    "type": "aws",
    "data": {
      "accessKeyId": "<new-access-key>",
      "secretAccessKey": "<new-secret-key>",
      "region": "us-east-1"
    }
  }'

# Step 3: Verify
curl -X POST http://n8n:5678/rest/credentials/{credential_id}/test \
  -H "X-N8N-API-KEY: $N8N_API_KEY"

# Step 4: Update n8n environment if the credential was in env
docker service update --env-add "NEW_CREDENTIAL=n8n_cred_id" n8n

# Step 5: Remove old credential
curl -X DELETE http://n8n:5678/rest/credentials/{old_credential_id} \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

### 12.5 Workflow Migration (Export/Import)

```bash
# Step 1: Export workflow from source environment
curl -s http://n8n-source:5678/rest/workflows/{workflow_id} \
  -H "X-N8N-API-KEY: $SOURCE_API_KEY" | jq '.' > workflow_export.json

# Step 2: Adjust credentials reference in the JSON
# Replace credential IDs with those in the target environment
# This is manual — map old IDs to new IDs in the JSON

# Step 3: Import to target environment
curl -X POST http://n8n-target:5678/rest/workflows \
  -H "X-N8N-API-KEY: $TARGET_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflow_export.json

# Step 4: Activate the workflow
curl -X PATCH http://n8n-target:5678/rest/workflows/{new_workflow_id} \
  -H "X-N8N-API-KEY: $TARGET_API_KEY" \
  -d '{"active": true}'

# Step 5: Verify
curl -s http://n8n-target:5678/rest/workflows/{new_workflow_id} \
  -H "X-N8N-API-KEY: $TARGET_API_KEY" | jq '.active'
# Should be true
```

---

## 13. Tenant/Customer Runbooks

### 13.1 New Tenant Onboarding Procedure

```bash
# Step 1: Create tenant via admin API
curl -X POST https://admin.amccloud.com/api/v1/tenants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "domain": "acme.amccloud.com",
    "tier": "growth",
    "admin_email": "admin@acmecorp.com",
    "admin_name": "John Doe"
  }'

# Step 2: Note the returned tenant_id — this is used for all downstream provisioning
# Expected response:
{
  "tenant_id": "tnt_abc123def",
  "status": "provisioning"
}

# Step 3: Verify tenant provisioning completed
curl -s https://admin.amccloud.com/api/v1/tenants/tnt_abc123def \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.status'
# Should be "active"

# Step 4: Create admin user and send welcome email
# (Automated by onboarding workflow)

# Step 5: Verify MinIO bucket created
mc ls source/ | grep "tnt_abc123def"

# Step 6: Verify Qdrant collections created
curl -s http://qdrant:6333/collections | jq '.result.collections[] | select(.name | startswith("tnt_abc123def"))'

# Step 7: Verify initial configuration (feature flags, defaults)
# Check Unleash for tenant-specific flags

# Step 8: Send onboarding confirmation to the tenant admin
```

### 13.2 Tenant Data Corruption

#### Identify Scope:

```sql
-- Check which tables have data corruption for the tenant
-- Compare row counts with expected state
SELECT 'contacts' AS table_name, count(*) FROM contacts WHERE tenant_id = 'tnt_abc123def'
UNION ALL
SELECT 'campaigns' AS table_name, count(*) FROM campaigns WHERE tenant_id = 'tnt_abc123def'
UNION ALL
SELECT 'campaign_contacts' AS table_name, count(*) FROM campaign_contacts WHERE tenant_id = 'tnt_abc123def';

-- Check for orphaned records
SELECT id FROM contacts WHERE tenant_id = 'tnt_abc123def'
  AND campaign_id NOT IN (SELECT id FROM campaigns WHERE tenant_id = 'tnt_abc123def');
```

#### Restore from Backup:

```bash
# Step 1: Identify the point before corruption occurred
# Check audit logs for the tenant
SELECT * FROM audit_log
WHERE tenant_id = 'tnt_abc123def'
  AND table_name IN ('contacts', 'campaigns')
  AND operation IN ('UPDATE', 'DELETE')
ORDER BY changed_at DESC
LIMIT 20;

# Step 2: Restore specific tables from backup
# Option A: Single table restore from pg_dump
pg_restore -h pgbouncer -U amc -d amc \
  --table=contacts \
  --data-only \
  --schema=public \
  latest_backup.dump

# Then delete records not belonging to this tenant
DELETE FROM contacts
WHERE tenant_id = 'tnt_abc123def'
  AND id NOT IN (SELECT id FROM contacts_restored WHERE tenant_id = 'tnt_abc123def');

# Option B: Full tenant restore from backup
# (Extract only this tenant's data from backup)
```

### 13.3 Tenant Exceeding Limits

#### Check:

```bash
# Check current usage vs limits
curl -s https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/usage \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.'

# Check: api_calls, storage_gb, ai_tokens, active_users, campaigns
```

#### Enforce Throttling:

```bash
# Apply rate limiting to the tenant
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/rate-limit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"rate_limit": 500, "rate_limit_period": "minute"}'

# Or temporary block
curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/block \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "usage_threshold_exceeded", "until": "2026-06-20T00:00:00Z"}'
```

#### Contact Customer:

```bash
# Trigger notification to tenant admin
# Use the notification service
curl -X POST http://notification-service:8004/api/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tnt_abc123def",
    "type": "usage_limit_warning",
    "channels": ["email", "in_app"],
    "template": "usage_limit_exceeded",
    "params": {
      "usage_type": "AI tokens",
      "current": 850000,
      "limit": 1000000,
      "upgrade_link": "https://app.amccloud.com/settings/billing"
    }
  }'
```

### 13.4 Tenant Deletion Request (GDPR)

```bash
# Step 1: Validate the request
# Ensure it comes from an authorized requester (tenant admin)
# Verify identity via support ticket or signed communication

# Step 2: Lock the tenant (prevent further data processing)
curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/lock \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "GDPR deletion request", "ticket_id": "SUP-12345"}'

# Step 3: Export data for the tenant (if requested)
# See Section 13.5

# Step 4: Delete tenant data — PostgreSQL
# This is done via the admin API which handles cascading deletes
curl -X DELETE https://admin.amccloud.com/api/v1/tenants/tnt_abc123def \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Or manually (for verification):
docker compose exec postgres-primary psql -U amc -d amc -c "
BEGIN;
-- Delete tenant-level data (cascading)
DELETE FROM tenants WHERE id = 'tnt_abc123def';
-- Verify cleanup
SELECT count(*) AS remaining_records
FROM (
  SELECT 'contacts' AS t, count(*) FROM contacts WHERE tenant_id = 'tnt_abc123def'
  UNION ALL SELECT 'campaigns', count(*) FROM campaigns WHERE tenant_id = 'tnt_abc123def'
) AS counts WHERE count > 0;
COMMIT;
"

# Step 5: Delete from Redis
redis-cli -h redis-cache -a <password> --scan --pattern 'tenant:tnt_abc123def:*' | xargs redis-cli -h redis-cache -a <password> DEL

# Step 6: Delete from Qdrant
curl -X DELETE http://qdrant:6333/collections/tnt_abc123def_memory
curl -X DELETE http://qdrant:6333/collections/tnt_abc123def_knowledge

# Step 7: Delete MinIO bucket
mc rm --recursive --force source/tnt-abc123def/

# Step 8: Delete from n8n (remove tenant workflows)
for wf_id in $(curl -s http://n8n:5678/rest/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq -r ".data[] | select(.tags[].name == \"tenant:tnt_abc123def\") | .id"); do
  curl -X DELETE http://n8n:5678/rest/workflows/$wf_id \
    -H "X-N8N-API-KEY: $N8N_API_KEY"
done

# Step 9: Verification pull
# Confirm all data deleted
SELECT count(*) FROM contacts WHERE tenant_id = 'tnt_abc123def';
# Should return 0

# Step 10: Send GDPR deletion confirmation to the requester
```

### 13.5 Tenant Data Export Request

```bash
# Step 1: Generate export request
EXPORT_ID=$(curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format": "json", "include": ["contacts", "campaigns", "analytics", "ai_history"]}' | jq -r '.export_id')

# Step 2: Export PostgreSQL data
docker compose exec postgres-primary psql -U amc -d amc -c "
COPY (SELECT * FROM contacts WHERE tenant_id = 'tnt_abc123def')
TO '/tmp/exports/$EXPORT_ID/contacts.json';
"

# Step 3: Export Qdrant data
curl -X POST http://qdrant:6333/collections/tnt_abc123def_memory/snapshots

# Step 4: Export MinIO data
mc cp --recursive source/tnt-abc123def/ /tmp/exports/$EXPORT_ID/minio/

# Step 5: Package and upload
tar -czf /tmp/exports/$EXPORT_ID.tar.gz -C /tmp/exports/$EXPORT_ID .
aws s3 cp /tmp/exports/$EXPORT_ID.tar.gz s3://amc-exports/$EXPORT_ID.tar.gz

# Step 6: Generate download link (expiring)
PRESIGNED_URL=$(aws s3 presign s3://amc-exports/$EXPORT_ID.tar.gz --expires-in 86400)

# Step 7: Notify tenant admin
curl -X POST http://notification-service:8004/api/v1/send \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"tnt_abc123def\",
    \"type\": \"data_export_ready\",
    \"channels\": [\"email\"],
    \"params\": {
      \"download_url\": \"$PRESIGNED_URL\",
      \"expires_in_hours\": 24
    }
  }"

# Step 8: Clean up temp files
rm -rf /tmp/exports/$EXPORT_ID*
```

### 13.6 White-Label Domain Setup Procedure

```bash
# Step 1: Validate domain ownership (tenant must add TXT record)
# Generate verification token
VERIFY_TOKEN=$(openssl rand -hex 16)

# Step 2: Ask tenant to add DNS record
echo "Please add this TXT record to your domain:
  amc-verify.{tenant-domain} TXT \"$VERIFY_TOKEN\""

# Step 3: Verify DNS record
dig TXT amc-verify.acmecorp.com +short
# Expected: "$VERIFY_TOKEN"

# Step 4: Configure custom domain
curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/custom-domain \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "marketing.acmecorp.com",
    "verification_token": "'"$VERIFY_TOKEN"'"
  }'

# Step 5: Provision SSL certificate
# (Automated via cert-manager / Let's Encrypt)

# Step 6: Ask tenant to add CNAME
echo "Please add this CNAME record:
  marketing.acmecorp.com CNAME app.amccloud.com"

# Step 7: Verify DNS propagation
dig CNAME marketing.acmecorp.com +short
# Expected: "app.amccloud.com."

# Step 8: Verify SSL and routing
curl -I https://marketing.acmecorp.com
# Expected: 200 OK with SSL

# Step 9: Activate white-label
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/tnt_abc123def \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"white_label_active": true}'
```

### 13.7 Suspicious Tenant Activity

#### Investigate:

```bash
# Step 1: Check login patterns
{service="auth-service"} |= "tnt_abc123def" | logfmt

# Check for unusual IPs
{service="api-gateway"} |= "tnt_abc123def" | logfmt | user_ip

# Step 2: Check API usage patterns
# High volume of writes/deletes
SELECT query, calls
FROM pg_stat_statements
WHERE query ILIKE '%tnt_abc123def%'
ORDER BY calls DESC
LIMIT 20;

# Step 3: Check for data scraping
# Sudden spike in GET requests for all contacts
# In Grafana: API requests by endpoint for this tenant

# Step 4: Check AI usage for abuse
# High volume of AI calls, prompt injection attempts
docker logs ai-orchestrator --tail 200 | grep "tnt_abc123def" | grep -i "injection|abuse|blocked"
```

#### Isolate:

```bash
# Step 1: Lower rate limit drastically
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/rate-limit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"rate_limit": 10, "rate_limit_period": "minute"}'

# Step 2: Disable AI features
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/features \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"ai_agents": false, "ai_content": false}'

# Step 3: Disable webhooks
curl -X PATCH https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/webhooks \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"active": false}'
```

#### Disable if Needed:

```bash
# Step 1: Lock the tenant entirely
curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/lock \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "suspicious_activity_investigation"}'

# Step 2: Force-invalidate all sessions
redis-cli -h redis-sessions -a <password> --scan --pattern 'session:tnt_abc123def:*' | xargs redis-cli -h redis-sessions -a <password> DEL

# Step 3: Revoke API keys
curl -X POST https://admin.amccloud.com/api/v1/tenants/tnt_abc123def/api-keys/revoke-all \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Step 4: Notify security team (if confirmed abuse)
```

---

## 14. Billing Runbooks

### 14.1 Invoice Generation Failure

#### Check:

```bash
# Check Stripe webhook logs
docker logs billing-service --tail 100 | grep -i "invoice\|stripe\|webhook"

# Check Stripe dashboard for recent events
# https://dashboard.stripe.com/events

# Check billing database
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT i.id, i.tenant_id, i.amount_due, i.status, i.created_at, i.updated_at
FROM invoices i
WHERE i.created_at > now() - interval '24 hours'
ORDER BY i.created_at DESC;
"
```

#### Regenerate:

```bash
# Step 1: Identify the affected invoices
curl -s http://billing-service:8003/api/v1/invoices/failed \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '.'

# Step 2: Regenerate invoice
for invoice_id in $(curl -s http://billing-service:8003/api/v1/invoices/failed \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq -r '.[].id'); do
  curl -X POST http://billing-service:8003/api/v1/invoices/$invoice_id/regenerate \
    -H "Authorization: Bearer $BILLING_TOKEN"
done

# Step 3: Verify
docker compose exec postgres-primary psql -U amc -d amc -c "
SELECT count(*) FROM invoices
WHERE status = 'open' AND created_at > now() - interval '1 hour';
"
```

### 14.2 Payment Failure

#### Contact Customer:

```bash
# Step 1: Identify failed payments
curl -s http://billing-service:8003/api/v1/payments/failed \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '.'

# Step 2: Trigger dunning email (automatic)
# n8n workflow "dunning-email-sequence" handles this
# Verify the workflow is active:
curl -s http://n8n:5678/rest/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | select(.name == "Dunning Email Sequence") | .active'

# Step 3: Manual payment retry (if needed)
curl -X POST http://billing-service:8003/api/v1/payments/retry \
  -H "Authorization: Bearer $BILLING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "in_abc123"}'
```

#### Dunning Logic:

The dunning sequence is automated via n8n workflow:

| Attempt | Delay | Method |
|---------|-------|--------|
| 1 | 1 day | Email reminder |
| 2 | 3 days | Email + in-app notification |
| 3 | 7 days | Email + SMS |
| 4 | 14 days | Email + downgrade tier notice |
| 5 | 30 days | Suspend tenant |

### 14.3 Subscription Not Activating

#### Manual Activation:

```bash
# Step 1: Check Stripe subscription status
curl -s https://api.stripe.com/v1/subscriptions/sub_abc123 \
  -H "Authorization: Bearer $STRIPE_SECRET_KEY" | jq '.status'

# Step 2: Check webhook delivery
curl -s http://billing-service:8003/api/v1/webhooks/stripe/log \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '.events[] | select(.type == "checkout.session.completed")'

# Step 3: Manually activate subscription
curl -X POST http://billing-service:8003/api/v1/subscriptions/sub_abc123/activate \
  -H "Authorization: Bearer $BILLING_TOKEN"

# Step 4: Verify
curl -s http://billing-service:8003/api/v1/tenants/tnt_abc123def/subscription \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '.status'
# Should be "active"
```

### 14.4 Credit Balance Inconsistency

#### Audit Trail Investigation:

```sql
-- Check credit transactions for the tenant
SELECT ct.id, ct.amount, ct.balance_after, ct.transaction_type, ct.created_at, ct.description
FROM credit_transactions ct
WHERE ct.tenant_id = 'tnt_abc123def'
ORDER BY ct.created_at DESC
LIMIT 50;

-- Recalculate expected balance
SELECT sum(CASE
  WHEN transaction_type IN ('credit', 'refund') THEN amount
  WHEN transaction_type IN ('debit', 'charge') THEN -amount
  ELSE 0 END) AS calculated_balance
FROM credit_transactions
WHERE tenant_id = 'tnt_abc123def';

-- Compare with actual balance
SELECT current_credit_balance
FROM tenants
WHERE id = 'tnt_abc123def';
```

#### Manual Correction:

```sql
BEGIN;
-- Insert correction transaction
INSERT INTO credit_transactions (tenant_id, amount, balance_after, transaction_type, description, created_by)
VALUES (
  'tnt_abc123def',
  <calculated_difference>,
  (SELECT current_credit_balance FROM tenants WHERE id = 'tnt_abc123def') + <calculated_difference>,
  'adjustment',
  'Manual correction — audit ID: AUD-12345',
  'ops-internal'
);

-- Update tenant balance
UPDATE tenants
SET current_credit_balance = current_credit_balance + <calculated_difference>
WHERE id = 'tnt_abc123def';
COMMIT;
```

### 14.5 Refund Procedure

```bash
# Step 1: Verify refund eligibility
curl -s http://billing-service:8003/api/v1/invoices/in_abc123 \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '{status, amount_paid, refunded_amount}'

# Step 2: Process refund via Stripe
curl -X POST https://api.stripe.com/v1/refunds \
  -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  -d '{
    "charge": "ch_abc123",
    "amount": 2999,
    "reason": "requested_by_customer",
    "metadata": {"tenant_id": "tnt_abc123def", "ticket": "SUP-67890"}
  }'

# Step 3: Record refund in AMC billing system
curl -X POST http://billing-service:8003/api/v1/refunds \
  -H "Authorization: Bearer $BILLING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": "in_abc123",
    "amount": 29.99,
    "reason": "Customer requested refund per support ticket SUP-67890",
    "processed_by": "oncall@amccloud.com"
  }'

# Step 4: Notify customer
curl -X POST http://notification-service:8004/api/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tnt_abc123def",
    "type": "refund_processed",
    "channels": ["email"],
    "params": {"amount": 29.99, "invoice_id": "in_abc123"}
  }'

# Step 5: Verify tenant's credit balance is updated
curl -s http://billing-service:8003/api/v1/tenants/tnt_abc123def/credits \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '.balance'
```

### 14.6 Trial Extension Procedure

```bash
# Step 1: Check current trial end date
curl -s http://billing-service:8003/api/v1/tenants/tnt_abc123def/subscription \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '{status, trial_end, plan}'

# Step 2: Extend trial by N days
curl -X POST http://billing-service:8003/api/v1/tenants/tnt_abc123def/trial/extend \
  -H "Authorization: Bearer $BILLING_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"extra_days": 14, "reason": "Customer requested extension via support ticket SUP-67890"}'

# Step 3: Verify extension
curl -s http://billing-service:8003/api/v1/tenants/tnt_abc123def/subscription \
  -H "Authorization: Bearer $BILLING_TOKEN" | jq '{trial_end}'

# Step 4: Notify the customer
curl -X POST http://notification-service:8004/api/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tnt_abc123def",
    "type": "trial_extended",
    "channels": ["email"],
    "params": {"new_trial_end": "$(date -d '+14 days' +%Y-%m-%d)"}
  }'
```

---

## 15. Backup & Recovery Runbooks

### 15.1 Database Backup Failure

#### Investigate:

```bash
# Check pgBackRest logs
pgbackrest --stanza=amc check

# Check recent backup status
pgbackrest --stanza=amc info

# Check disk space on backup volume
df -h /backups

# Check S3 connectivity
aws s3 ls s3://amc-backups/postgresql/
```

#### Manual pg_dump:

```bash
# If automated backup failed, create manual backup
pg_dump -h pgbouncer -U amc -d amc -Fc \
  -f /tmp/manual_backup_$(date +%Y%m%d_%H%M%S).dump

# Compress
gzip /tmp/manual_backup_*.dump

# Upload to S3
aws s3 cp /tmp/manual_backup_*.dump.gz s3://amc-backups/postgresql/manual/

# Verify
aws s3 ls s3://amc-backups/postgresql/manual/ | tail -3

# Clean up local
rm /tmp/manual_backup_*.dump.gz
```

### 15.2 Full Database Restore

#### Scenario A: Single Table Restore

```bash
# Step 1: Identify the backup containing the table
pgbackrest --stanza=amc info

# Step 2: Extract the specific table from backup
pgbackrest --stanza=amc --type=time --target="2026-06-19 12:00:00" --db-path=/tmp/pg-restore restore

# Step 3: Dump the specific table from restored instance
pg_ctl -D /tmp/pg-restore start -p 5433
pg_dump -p 5433 -U amc -d amc --table=contacts --data-only -f /tmp/contacts_restore.sql
pg_ctl -D /tmp/pg-restore stop

# Step 4: Import into production (with careful review)
psql -h pgbouncer -U amc -d amc -f /tmp/contacts_restore.sql

# Step 5: Verify
psql -h pgbouncer -U amc -d amc -c "SELECT count(*) FROM contacts;"
```

#### Scenario B: Single Tenant Restore

```bash
# Step 1: Restore from backup to temp instance
pgbackrest --stanza=amc --type=time --target="2026-06-19 12:00:00" --db-path=/tmp/pg-restore restore
pg_ctl -D /tmp/pg-restore start -p 5433

# Step 2: Extract tenant data
pg_dump -p 5433 -U amc -d amc \
  --table=contacts --data-only \
  -f /tmp/tenant_contacts.sql \
  --inserts \
  --where="tenant_id = 'tnt_abc123def'"

pg_ctl -D /tmp/pg-restore stop

# Step 3: Delete current tenant data in production
BEGIN;
DELETE FROM contacts WHERE tenant_id = 'tnt_abc123def';
-- (repeat for each table)
COMMIT;

# Step 4: Import restored data
psql -h pgbouncer -U amc -d amc -f /tmp/tenant_contacts.sql

# Step 5: Verify
psql -h pgbouncer -U amc -d amc -c \
  "SELECT count(*) FROM contacts WHERE tenant_id = 'tnt_abc123def';"
```

#### Scenario C: Full Database Restore

```bash
# Step 1: Stop the application
docker service scale api-gateway=0 monolith=0 auth-service=0 billing-service=0
docker compose down --timeout 30

# Wait for all connections to drain
sleep 30

# Step 2: Restore from pgBackRest
pgbackrest --stanza=amc --type=time \
  --target="2026-06-19 12:00:00" \
  --target-action=promote \
  --db-path=/var/lib/postgresql/data \
  restore

# Step 3: Start PostgreSQL
pg_ctl -D /var/lib/postgresql/data start

# Step 4: Verify database integrity
psql -U amc -d amc -c "SELECT count(*) FROM tenants;"
psql -U amc -d amc -c "SELECT count(*) FROM contacts;"

# Step 5: Start application
docker compose up -d pgbouncer redis-cache rabbitmq
docker service scale api-gateway=3 monolith=3 auth-service=2 billing-service=2

# Step 6: Wait for health checks
for svc in api-gateway monolith auth-service billing-service; do
  until curl -sf http://<service>:<port>/health; do
    echo "Waiting for $svc..."
    sleep 5
  done
done

# Step 7: Run smoke tests
python scripts/smoke_tests.py

# Step 8: Monitor for errors
# Check Grafana dashboards for error rates
```

### 15.3 Qdrant Restore from Snapshot

```bash
# Step 1: Find the snapshot
LATEST_SNAPSHOT=$(aws s3 ls s3://amc-backups/qdrant/ai_memory_abc123/ | sort | tail -1 | awk '{print $4}')
echo "Restoring from: $LATEST_SNAPSHOT"

# Step 2: Download snapshot
aws s3 cp s3://amc-backups/qdrant/ai_memory_abc123/$LATEST_SNAPSHOT /tmp/

# Step 3: Get the original collection configuration
curl -s http://qdrant:6333/collections/ai_memory_abc123 | jq '.result.config'

# Step 4: Delete existing collection (if corrupted)
curl -X DELETE http://qdrant:6333/collections/ai_memory_abc123

# Step 5: Recreate collection with original config
curl -X PUT http://qdrant:6333/collections/ai_memory_abc123 \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {"size": 1536, "distance": "Cosine"},
    "hnsw_config": {"m": 32, "ef_construct": 200},
    "optimizers_config": {"default_segment_number": 2}
  }'

# Step 6: Upload snapshot
curl -X POST http://qdrant:6333/collections/ai_memory_abc123/snapshots/upload \
  -F "snapshot=@/tmp/$LATEST_SNAPSHOT"

# Step 7: Force optimization
curl -X POST http://qdrant:6333/collections/ai_memory_abc123/optimize

# Step 8: Verify
curl -s http://qdrant:6333/collections/ai_memory_abc123 | jq '{points_count: .result.points_count, status: .result.status}'
```

### 15.4 MinIO Restore from Cross-Region Replica

```bash
# Step 1: Check cross-region replica status
mc admin replicate info source/tnt-abc123def

# Step 2: Sync from replica
mc mirror --overwrite remote/tnt-abc123def/ source/tnt-abc123def/

# Step 3: Verify integrity
mc diff source/tnt-abc123def/ remote/tnt-abc123def/

# Step 4: If no cross-region replica, restore from backup
aws s3 sync s3://amc-backups/minio/tnt-abc123def/ /tmp/minio-restore/
mc cp --recursive /tmp/minio-restore/ source/tnt-abc123def/
rm -rf /tmp/minio-restore
```

### 15.5 Redis Restore from RDB File

```bash
# Step 1: Find the latest RDB backup
LATEST_RDB=$(aws s3 ls s3://amc-backups/redis/cache/ | sort | tail -1 | awk '{print $4}')
echo "Restoring from: $LATEST_RDB"

# Step 2: Download RDB
aws s3 cp s3://amc-backups/redis/cache/$LATEST_RDB /tmp/redis_dump.rdb.gz
gunzip /tmp/redis_dump.rdb.gz

# Step 3: Stop Redis
docker compose stop redis-cache

# Step 4: Copy RDB to Redis data directory
cp /tmp/redis_dump.rdb /var/lib/docker/volumes/amc-dev_redis-data/_data/dump.rdb

# Step 5: Start Redis
docker compose start redis-cache

# Step 6: Verify
redis-cli -h redis-cache -a <password> DBSIZE
# Should show keys matching the backup

# Step 7: Clean up
rm /tmp/redis_dump.rdb
```

### 15.6 Multi-Service Recovery Sequence

When recovering from a major outage, services must be started in dependency order:

```
1. PostgreSQL (primary → replica → PgBouncer)
2. Redis (cache → sessions → queue)
3. RabbitMQ
4. MinIO
5. Qdrant
6. Backend services (api-gateway → monolith → extracted microservices)
7. AI services (NIM → Ollama → ai-memory → ai-agent-runtime → ai-orchestrator)
8. n8n
9. Frontend
10. Monitoring (Prometheus → Grafana → Loki)
```

```bash
# Recovery script (pseudo)
for service_group in \
  "postgres-primary postgres-replica pgbouncer" \
  "redis-cache redis-sessions redis-queue" \
  "rabbitmq" \
  "minio" \
  "qdrant" \
  "api-gateway monolith auth-service billing-service notification-service media-service" \
  "analytics-service admin-service marketplace-service webhook-service" \
  "nim ollama ai-memory ai-agent-runtime ai-orchestrator" \
  "n8n" \
  "frontend" \
  "prometheus grafana loki promtail tempo"; do
  for service in $service_group; do
    docker compose up -d $service
    until curl -sf http://$service:<port>/health; do
      echo "Waiting for $service..."
      sleep 5
    done
    echo "$service is healthy"
  done
done
echo "All services recovered"
```

---

## 16. Security Incident Runbooks

### 16.1 Suspected Data Breach

**Immediate actions — followed in order, no deviation:**

```bash
# 1. ISOLATE — Prevent further data exfiltration
# Identify the compromised system and disconnect it
# If specific service is compromised:
docker service scale <compromised-service>=0
# Or block at network level
iptables -A INPUT -s <suspicious-ip> -j DROP

# 2. PRESERVE EVIDENCE — Snapshot before remediation
# Database snapshot
pg_dump -h pgbouncer -U amc -d amc -Fc -f /tmp/forensic_snapshot_$(date +%Y%m%d_%H%M%S).dump
# Container logs
docker logs <compromised-service> --tail 10000 > /tmp/forensic_logs_$(date +%Y%m%d_%H%M%S).txt
# System memory (if feasible)
li /tmp/forensic_memory.lime

# 3. INVESTIGATE — Determine scope
# Check access logs for unusual activity
{service="auth-service"} |= "login" | logfmt | user_ip | topk(10, count) by (user_ip)
# Check for data export activity
{service="api-gateway"} |= "export\|download" | logfmt

# 4. NOTIFY — Internal security team
# Page Security Officer (Carol Williams) immediately
# Do NOT send details over unencrypted channels
# Use: Signal or encrypted email
```

**Post-investigation procedures:**
- Determine which tenants/data were affected
- Notify affected tenants per SLA (72 hours for GDPR)
- Engage legal and PR teams
- File incident report with relevant authorities

### 16.2 DDoS Attack

#### Check:

```bash
# Identify traffic pattern
# In Grafana: check request rate, source IP distribution, endpoint distribution

# Check Cloudflare analytics
curl -s https://api.cloudflare.com/client/v4/zones/<zone-id>/analytics/dashboard \
  -H "Authorization: Bearer <token>" | jq '.result.totals.requests'

# Check for unusual request patterns
{service="api-gateway"} | logfmt | user_ip | topk(20, count) by (user_ip)
```

#### WAF Rules:

```bash
# Enable Cloudflare WAF managed rules
curl -X PATCH https://api.cloudflare.com/client/v4/zones/<zone-id>/settings/security_level \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "under_attack"}'

# Add IP block rule
curl -X POST https://api.cloudflare.com/client/v4/zones/<zone-id>/firewall/rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "block",
    "priority": 1000,
    "description": "DDoS mitigation - auto",
    "filter": {
      "expression": "(ip.src in {1.2.3.0/24 4.5.6.0/24})",
      "description": "Block DDoS source IPs"
    }
  }'
```

#### Rate Limiting:

```bash
# Aggressive rate limiting at Cloudflare
curl -X POST https://api.cloudflare.com/client/v4/zones/<zone-id>/rate_limits \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "DDoS rate limit - aggressive",
    "threshold": 100,
    "period": 60,
    "action": {
      "mode": "block",
      "timeout": 600
    },
    "match": {
      "request": {
        "url": "*.amccloud.com/*",
        "schemes": ["HTTPS"],
        "methods": ["GET", "POST"],
        "headers": []
      }
    }
  }'
```

#### Cloudflare Mitigation:

```bash
# Enable "I'm Under Attack" mode
curl -X PATCH https://api.cloudflare.com/client/v4/zones/<zone-id>/settings/security_level \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": "under_attack"}'

# Challenge all requests with JS challenge
curl -X PATCH https://api.cloudflare.com/client/v4/zones/<zone-id>/settings/challenge_ttl \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": 300}'
```

### 16.3 Account Compromise

#### Force Logout:

```bash
# Revoke all active sessions for the user
docker compose exec redis-sessions redis-cli -a <password> --scan --pattern 'session:*:<user_id>' | xargs docker compose exec redis-sessions redis-cli -a <password> DEL

# Or via admin API
curl -X POST https://admin.amccloud.com/api/v1/users/{user_id}/revoke-sessions \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Revoke Tokens:

```bash
# Revoke API keys
curl -X DELETE https://admin.amccloud.com/api/v1/users/{user_id}/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Reset JWT secret for the tenant (forces re-login for all users)
curl -X POST https://admin.amccloud.com/api/v1/tenants/{tenant_id}/rotate-jwt-secret \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Notify User:

```bash
# Send security alert notification
curl -X POST http://notification-service:8004/api/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tnt_abc123def",
    "user_id": "usr_xyz",
    "type": "security_alert",
    "channels": ["email", "sms"],
    "template": "account_compromised",
    "params": {
      "action_taken": "All sessions revoked, password reset required",
      "support_link": "https://support.amccloud.com/security",
      "incident_id": "SEC-67890"
    }
  }'
```

### 16.4 Malware/Phishing

#### Identify Scope:

```bash
# Check for unusual outbound traffic
# In network monitoring dashboard

# Check for unusual files/modifications
find /app -name "*.exe" -o -name "*.bat" -o -name "*.ps1" 2>/dev/null

# Check for process injection
docker exec <container> ps aux | grep -v "PID\|sleep\|bash"

# Scan container with ClamAV (if available)
docker exec <container> clamscan --recursive /app
```

#### Remove:

```bash
# Isolate affected container
docker network disconnect amc-dev <container-id>
docker stop <container-id>

# Rebuild from clean image
docker compose build --no-cache <service>
docker compose up -d <service>

# Scan other containers
for container in $(docker ps -q); do
  docker exec $container clamscan --recursive /app 2>/dev/null
done
```

#### Report:

```bash
# File a report with:
# 1. Internal security team (Carol Williams)
# 2. CISA (if US-based infrastructure)
# 3. Relevant data protection authority (if EU data involved)
# 4. Hosting provider for abuse report
```

### 16.5 Vulnerability Disclosure Processing

```bash
# Step 1: Acknowledge receipt within 24 hours
# Template:
# "Thank you for your vulnerability disclosure. We have received your report
# and assigned it ID VULN-XXXXX. Our security team will review it within
# 72 hours and provide an initial assessment."

# Step 2: Triage and validate
# Reproduce the vulnerability in a staging environment
# Determine severity (CVSS score)
# Identify affected services and data

# Step 3: Develop fix and timeline
# Critical: 48 hours
# High: 7 days
# Medium: 30 days
# Low: 90 days

# Step 4: Notify reporter of resolution timeline
# "We have validated your report and classified it as [severity].
# We expect to deploy a fix by [date]. We will notify you when
# the fix is live and coordinate disclosure."

# Step 5: Deploy fix
# Follow normal deployment procedure
# Add security regression test

# Step 6: Coordinate disclosure
# Agree on public disclosure date with reporter
# Prepare advisory
# Publish CVE if applicable
```

### 16.6 Bug Bounty Triage

```bash
# Step 1: Receive report via HackerOne / Bugcrowd
# Step 2: Initial triage (within 24 hours)
# - Reproducible? → Proceed
# - Duplicate? → Close with reference
# - Out of scope? → Close with explanation

# Step 3: Severity classification (using CVSS 3.1)
# Critical (9.0-10.0): $5,000+
# High (7.0-8.9): $2,000
# Medium (4.0-6.9): $500
# Low (0.1-3.9): $100

# Step 4: Fix validation
# Reporter validates fix in staging

# Step 5: Award bounty
# Process via HackerOne / Bugcrowd platform

# Step 6: Disclosure
# Critical/High: Coordinated disclosure after 30 days
# Medium/Low: Public disclosure allowed after 90 days
```

---

## 17. Maintenance Procedures

### 17.1 Scheduled Maintenance Planning

#### Maintenance Window Schedule:

| Type | Frequency | Window | Expected Duration | User Impact |
|------|-----------|--------|-------------------|-------------|
| Security patching | Monthly | Sunday 02:00–06:00 UTC | 30 min rolling | None (rolling) |
| Database maintenance | Quarterly | Sunday 04:00–06:00 UTC | 2 hours | Brief read-only mode |
| Feature deployment | Weekly | Tuesday 10:00–12:00 UTC | 30 min | None (zero-downtime) |
| Capacity upgrade | As needed | Planned 2 weeks ahead | Varies | Varies |

#### Planning Checklist:

- [ ] Jira ticket created: `MAINT-YYYY-MM-DD-description`
- [ ] Status page scheduled 48 hours in advance
- [ ] Stakeholders notified (Slack #ops-announce)
- [ ] Tenant admins notified (if > 5 min downtime expected)
- [ ] Rollback plan documented
- [ ] Testing completed in staging
- [ ] On-call engineer briefed
- [ ] Communication templates prepared

### 17.2 Zero-Downtime Deployment Procedure

```bash
# Step 1: Ensure the deployment strategy is configured
# docker-compose.yml or service config:
#   update_config:
#     parallelism: 2
#     delay: 10s
#     order: start-first
#     failure_action: rollback

# Step 2: Deploy new version
docker stack deploy -c docker-stack.yml amc --with-registry-auth

# Or for individual service:
docker service update --image ghcr.io/amccloud/<service>:<new-tag> <service>

# Step 3: Monitor rollout
docker service ps <service> | grep -E "Running|Ready"
watch -n 5 'curl -sf http://<service>:<port>/health && echo "Healthy" || echo "Unhealthy"'

# Step 4: Run smoke tests
./scripts/smoke_tests.sh

# Step 5: Verify in monitoring
# Check: error rate, latency, request count not dropping
```

### 17.3 Database Migration with Zero Downtime (Expand-Contract)

**Principle:** Every schema change is split into forward-compatible phases.

#### Phase 1: Expand (add new schema alongside old)

```sql
-- Example: Rename column "name" to "full_name"
-- Step 1: Add new column (non-breaking — old code ignores it)
ALTER TABLE contacts ADD COLUMN full_name TEXT;
-- Step 2: Backfill data (background job)
UPDATE contacts SET full_name = name WHERE full_name IS NULL;
-- Step 3: Deploy application code that writes to BOTH columns
-- (old code: writes to "name", new code: writes to both "name" AND "full_name")
```

#### Phase 2: Migrate (deploy code that reads from new schema)

```bash
# Deploy application update that reads from "full_name" instead of "name"
# Old deployment still reads "name" — both work simultaneously
docker service update --image ghcr.io/amccloud/monolith:<migration-tag> monolith
```

#### Phase 3: Contract (remove old schema)

```sql
-- After all instances are reading from "full_name":
ALTER TABLE contacts DROP COLUMN name CASCADE;
-- Or mark as deprecated and drop in next release:
ALTER TABLE contacts RENAME COLUMN name TO name_deprecated;
```

### 17.4 Certificate Renewal (Automated and Manual Fallback)

#### Automated (Let's Encrypt + cert-manager):

```bash
# Check cert-manager status
kubectl get certificates --all-namespaces
kubectl describe certificate amc-prod-tls

# Force renewal
kubectl cert-manager renew amc-prod-tls
```

#### Manual Fallback:

```bash
# Step 1: Generate new certificate
docker compose run --rm certbot certonly --manual \
  -d app.amccloud.com \
  -d api.amccloud.com \
  -d *.app.amccloud.com \
  --preferred-challenges dns

# Step 2: Combine cert and key
cat /etc/letsencrypt/live/app.amccloud.com/fullchain.pem \
  /etc/letsencrypt/live/app.amccloud.com/privkey.pem > /tmp/combined.pem

# Step 3: Deploy to load balancer
# (Method depends on infrastructure)
# Example for nginx:
cp /tmp/combined.pem /etc/nginx/certs/amccloud.pem
nginx -s reload

# Step 4: Verify
echo | openssl s_client -servername app.amccloud.com -connect app.amccloud.com:443 2>/dev/null | openssl x509 -noout -dates
```

### 17.5 OS Security Patching Procedure

```bash
# Step 1: Drain the node (if clustered)
docker node update --availability drain <node-id>

# Step 2: Apply security patches
# For Ubuntu/Debian:
sudo apt-get update && sudo apt-get upgrade -y

# For RHEL/CentOS:
sudo yum update -y --security

# Step 3: Reboot
sudo reboot

# Step 4: Verify node health
docker node ls | grep <node-id>
# Should show "Ready" and "Active"

# Step 5: Uncordon the node (K8s) / set back to active (Swarm)
docker node update --availability active <node-id>

# Step 6: Verify services rescheduled
docker service ps <service> | grep <node-id>
```

### 17.6 Log Rotation and Archival

#### Docker Log Rotation Configuration:

```yaml
# In docker-compose.yml (already configured)
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### Manual Log Cleanup:

```bash
# Check disk usage of Docker logs
du -sh /var/lib/docker/containers/*/*-json.log

# Force log rotation
docker system prune --volumes -af  # WARNING: removes unused volumes
# Safer — just truncate Docker logs:
truncate -s 0 /var/lib/docker/containers/*/*-json.log

# Application logs archival
tar -czf /backups/logs/amc-logs-$(date +%Y%m%d).tar.gz /var/log/amc/
aws s3 cp /backups/logs/amc-logs-*.tar.gz s3://amc-backups/logs/
```

### 17.7 Performance Tuning Schedule (Quarterly Review)

| Quarter | Focus Area | Activities |
|---------|-----------|------------|
| Q1 | Database | Index review, query optimization, vacuum analysis |
| Q2 | Cache | Hit rate optimization, TTL tuning, eviction policy review |
| Q3 | AI Inference | Model quantization, batch optimization, GPU utilization |
| Q4 | Full platform | Load testing, capacity planning, architecture review |

**Quarterly Review Checklist:**
- [ ] Review top 10 slowest queries via `pg_stat_statements`
- [ ] Check cache hit rates (target > 95%)
- [ ] Review Redis memory / eviction rates
- [ ] Analyze Qdrant segment counts and optimize
- [ ] Review RabbitMQ consumer lag
- [ ] Load test critical endpoints
- [ ] Update capacity projections
- [ ] Review and prune unused indexes

### 17.8 Capacity Review (Monthly)

```bash
# Check current resource utilization
# CPU
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}"

# Disk
df -h

# Database connections
psql -h pgbouncer -U amc -d amc -c "SELECT count(*) FROM pg_stat_activity;"

# PromQL queries for trending
# Rate of requests over last 30 days
rate(amc_http_requests_total[30d])
# 99th percentile latency trend
histogram_quantile(0.99, rate(amc_http_request_duration_seconds_bucket[7d]))
```

**Monthly Report Template:**
- Current vs. projected growth
- Services near capacity thresholds (> 70% CPU, > 75% memory, > 80% disk)
- Recommended scaling actions (with timeline)
- Cost impact of recommended actions

---

## 18. Post-Mortem Template

```markdown
# Post-Mortem: [Incident Title]

| Field | Value |
|-------|-------|
| **Incident ID** | INC-YYYY-MM-DD-NNN |
| **Severity** | SEV1 / SEV2 / SEV3 |
| **Date** | YYYY-MM-DD |
| **Duration** | X hours Y minutes |
| **Report Author** | Name |
| **Review Date** | YYYY-MM-DD |

---

## Incident Summary

[2-3 sentence summary of what happened and the impact]

---

## Timeline (All Times in UTC)

| Time | Event |
|------|-------|
| HH:MM | [First alert fired / issue detected] |
| HH:MM | [On-call acknowledged] |
| HH:MM | [Initial assessment — what was thought] |
| HH:MM | [Action taken] |
| HH:MM | [Escalation if any] |
| HH:MM | [Root cause identified] |
| HH:MM | [Fix applied] |
| HH:MM | [Verified resolved] |
| HH:MM | [Monitoring period ended] |

---

## Root Cause Analysis

### Direct Cause

[What directly caused the incident — one sentence]

### Contributing Factors

- [Factor 1 — e.g., missing monitoring on metric X]
- [Factor 2 — e.g., deployment was not tested for this scenario]
- [Factor 3 — e.g., runbook was outdated]

### Why Did It Happen? (5 Whys)

1. [Why?]
2. [Why?]
3. [Why?]
4. [Why?]
5. [Why?]

---

## Impact Assessment

| Metric | Value |
|--------|-------|
| **Users affected** | [Number or percentage] |
| **Revenue impact** | [$ amount, if known] |
| **Data loss** | [Yes/No — details] |
| **Downtime duration** | [X minutes/hours] |
| **PagerDuty alerts** | [Number of alerts triggered] |

---

## Detection and Response Evaluation

### How Was It Detected?

- [Automated alert / Customer report / Manual check]

### Response Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Time to acknowledge | [5 min for SEV1] | [Actual] |
| Time to mitigate | [30 min for SEV1] | [Actual] |
| Time to resolve | [4 hours for SEV1] | [Actual] |

### What Would Have Made Detection/Response Faster?

- [Better monitoring on X]
- [Runbook for Y scenario]
- [Automated remediation for Z]

---

## What Went Well

- [ ] [Thing that went well]
- [ ] [Thing that went well]
- [ ] [Thing that went well]

## What Went Wrong

- [ ] [Thing that went wrong]
- [ ] [Thing that went wrong]
- [ ] [Thing that went wrong]

---

## Action Items

| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | [Action description] | @name | YYYY-MM-DD | 🟢 Open / 🟡 In Progress / ✅ Done |
| 2 | [Action description] | @name | YYYY-MM-DD | 🟢 Open / 🟡 In Progress / ✅ Done |
| 3 | [Action description] | @name | YYYY-MM-DD | 🟢 Open / 🟡 In Progress / ✅ Done |
| 4 | [Action description] | @name | YYYY-MM-DD | 🟢 Open / 🟡 In Progress / ✅ Done |

**Action Item Categories:**
- 🔧 **Process:** Workflow, communication, or procedure improvements
- 📊 **Monitoring:** New alerts, dashboards, or observability
- 🤖 **Automation:** Scripts or remediation automation
- 📝 **Documentation:** Runbook or process guide updates

---

## Blameless Attribution Statement

> **This incident was caused by systemic issues in our systems and processes, not by individual actions or mistakes. All team members acted in good faith with the information available at the time. The goal of this post-mortem is to improve our systems, not to assign blame.**
>
> *— Signed, Engineering Leadership*

---

## Lessons Learned

### What Should We Start Doing?

- [New practice to adopt]

### What Should We Stop Doing?

- [Practice to stop]

### What Should We Continue Doing?

- [Practice to continue]

---

## Follow-Up Meeting

- **Date:** YYYY-MM-DD
- **Attendees:** [List]
- **Agenda:** Review action items, share learnings with broader team
```

---

## 19. Appendices

### Appendix A: All Service Endpoints and Ports Reference

| Service | Protocol | Internal Port | External Port (Prod) | External Port (Staging) |
|---------|----------|--------------|---------------------|------------------------|
| frontend | HTTP | 3000 | 443 (HTTPS) | 443 (HTTPS) |
| api-gateway | HTTP | 8000 | 443 (HTTPS) | 443 (HTTPS) |
| monolith | HTTP | 8001 | — (internal) | — (internal) |
| auth-service | HTTP | 8002 | — (internal) | — (internal) |
| billing-service | HTTP | 8003 | — (internal) | — (internal) |
| notification-service | HTTP | 8004 | — (internal) | — (internal) |
| media-service | HTTP | 8005 | — (internal) | — (internal) |
| ai-orchestrator | HTTP | 8010 | — (internal) | — (internal) |
| ai-agent-runtime | HTTP | 8011 | — (internal) | — (internal) |
| ai-memory | HTTP | 8012 | — (internal) | — (internal) |
| nim | HTTP | 8001 | — (GPU internal) | — (GPU internal) |
| ollama | HTTP | 11434 | — (internal) | — (internal) |
| analytics-service | HTTP | 8020 | — (internal) | — (internal) |
| admin-service | HTTP | 8030 | 443 (HTTPS) | 443 (HTTPS) |
| marketplace-service | HTTP | 8040 | — (internal) | — (internal) |
| webhook-service | HTTP | 8050 | — (internal) | — (internal) |
| n8n | HTTP | 5678 | — (internal) | — (internal) |
| unleash | HTTP | 4242 | — (internal) | — (internal) |
| postgres-primary | PostgreSQL | 5432 | — (internal) | — (internal) |
| postgres-replica | PostgreSQL | 5433 | — (internal) | — (internal) |
| pgbouncer | PostgreSQL | 6432 | — (internal) | — (internal) |
| redis-cache | Redis | 6379 | — (internal) | — (internal) |
| redis-sessions | Redis | 6380 | — (internal) | — (internal) |
| redis-queue | Redis | 6381 | — (internal) | — (internal) |
| qdrant | REST/gRPC | 6333 / 6334 | — (internal) | — (internal) |
| minio | S3 API | 9000 / 9001 | — (internal) | — (internal) |
| rabbitmq | AMQP/Mgmt | 5672 / 15672 | — (internal) | — (internal) |
| prometheus | HTTP | 9090 | — (internal) | — (internal) |
| grafana | HTTP | 3001 | 443 (HTTPS) | 443 (HTTPS) |
| loki | HTTP | 3100 | — (internal) | — (internal) |
| tempo | gRPC/HTTP | 4317 / 4318 | — (internal) | — (internal) |

### Appendix B: Environment Variables Reference

| Variable | Description | Source | Example |
|----------|-------------|--------|---------|
| `DATABASE_URL` | PostgreSQL primary connection string | Vault `kv/db/primary` | `postgresql://amc:***@pgbouncer:6432/amc` |
| `DATABASE_URL_READ` | Replica connection string for reads | Vault `kv/db/replica` | `postgresql://amc:***@postgres-replica:5432/amc` |
| `REDIS_URL` | Redis cache connection | Vault `kv/redis/cache` | `redis://:password@redis-cache:6379/0` |
| `REDIS_SESSION_URL` | Redis sessions connection | Vault `kv/redis/sessions` | `redis://:password@redis-sessions:6379/0` |
| `RABBITMQ_URL` | AMQP connection string | Vault `kv/rabbitmq/admin` | `amqp://amc:***@rabbitmq:5672/` |
| `QDRANT_URL` | Qdrant REST endpoint | Vault `kv/qdrant/endpoint` | `http://qdrant:6333` |
| `MINIO_ENDPOINT` | MinIO API endpoint | Vault `kv/minio/endpoint` | `minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | Vault `kv/minio/root` | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO secret key | Vault `kv/minio/root` | (secret) |
| `N8N_URL` | n8n base URL | Vault `kv/n8n/endpoint` | `http://n8n:5678` |
| `N8N_API_KEY` | n8n API authentication | Vault `kv/n8n/api-key` | (secret) |
| `OPENAI_API_KEY` | OpenAI API key | Vault `kv/ai/openai` | (secret) |
| `ANTHROPIC_API_KEY` | Anthropic API key | Vault `kv/ai/anthropic` | (secret) |
| `NIM_ENDPOINT` | NVIDIA NIM endpoint | Vault `kv/ai/nim` | `http://nim:8001/v1` |
| `STRIPE_API_KEY` | Stripe secret key | Vault `kv/stripe/prod` | (secret) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing | Vault `kv/stripe/prod` | `whsec_...` |
| `JWT_SECRET` | JWT signing secret | Vault `kv/auth/jwt` | (secret) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector | Vault `kv/otel/endpoint` | `http://tempo:4317` |
| `SERVICE_NAME` | Service identifier | Hardcoded per service | `api-gateway` |
| `ENVIRONMENT` | Deployment environment | Per environment | `production`, `staging`, `development` |
| `LOG_LEVEL` | Log verbosity | Per service config | `INFO`, `DEBUG`, `WARNING` |
| `UNLEASH_URL` | Feature flag server | Vault `kv/unleash/endpoint` | `http://unleash:4242/api` |
| `UNLEASH_API_TOKEN` | Unleash API token | Vault `kv/unleash/token` | (secret) |

### Appendix C: Tool Installation and Configuration

#### Essential CLI Tools

```bash
# Docker — https://docs.docker.com/engine/install/
docker --version  # Must be >= 24.x

# Docker Compose plugin
docker compose version  # Must be >= 2.20

# AWS CLI
pip install awscli  # or brew install awscli

# MinIO Client (mc)
curl -sL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
chmod +x /usr/local/bin/mc

# jq (JSON processor)
sudo apt-get install jq  # or brew install jq

# pgBackRest (for DBA operations)
sudo apt-get install pgbackrest

# Redis CLI
sudo apt-get install redis-tools

# RabbitMQ admin
pip install rabbitmqadmin

# Vault CLI
curl -sL https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip -o /tmp/vault.zip
unzip /tmp/vault.zip -d /usr/local/bin/

# kubectl (if using K8s)
curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && mv kubectl /usr/local/bin/
```

#### On-Call Engineer Laptop Setup

```bash
# 1. Clone the repository
git clone https://github.com/amccloud/aegis-marketing-cloud.git ~/aegis-marketing-cloud

# 2. Install tools (see above)

# 3. Configure AWS credentials
aws configure
# AWS Access Key ID: (from Vault kv/aws/oncall-role)
# AWS Secret Access Key: (from Vault kv/aws/oncall-role)
# Default region: us-east-1

# 4. Authenticate with Vault
vault login -method=oidc  # or token from admin

# 5. Set up MinIO client
mc alias set source https://minio.amccloud.com \
  $(vault read -field=access_key kv/minio/root) \
  $(vault read -field=secret_key kv/minio/root)

# 6. Verify connectivity
curl -sf https://grafana.amccloud.com/api/health && echo "Grafana OK"
curl -sf https://api.amccloud.com/health && echo "API OK"

# 7. Join on-call Slack channels
# #ops-oncall, #ops-announce, #inc-* (auto-join)
```

### Appendix D: Emergency Access Procedures (Break-Glass Accounts)

#### Overview

Break-glass accounts provide emergency access to critical systems when normal authentication (SSO, VPN) is unavailable. These accounts are:
- Stored in Vault under `kv/break-glass/`
- Credentials are rotated every 90 days
- Usage is logged and audited
- Requires two-person approval to retrieve (except in genuine emergencies)

#### Accessing Break-Glass Credentials

```bash
# Normal procedure (requires 2nd person approval)
vault read -format=json kv/break-glass/aws | jq '.data'
vault read -format=json kv/break-glass/postgresql | jq '.data'
vault read -format=json kv/break-glass/minio | jq '.data'

# Emergency procedure (single person — immediately logs to security team)
# Use the emergency-code from physical safe in NOC
# Combined with Vault one-time recovery code
vault operator generate-root -init -otp=<emergency-code>
# Then follow the generate-root workflow
```

#### Break-Glass Account Inventory

| System | Username | Where Stored | Rotation | Audit |
|--------|----------|-------------|----------|-------|
| AWS (admin) | `break-glass-admin` | Vault `kv/break-glass/aws` | 90 days | CloudTrail |
| PostgreSQL (superuser) | `postgres` | Vault `kv/break-glass/postgresql` | 90 days | PG audit logs |
| MinIO (root) | `minioadmin` | Vault `kv/break-glass/minio` | 90 days | MinIO audit |
| RabbitMQ (admin) | `break-glass` | Vault `kv/break-glass/rabbitmq` | 90 days | RabbitMQ audit |
| Grafana (admin) | `break-glass` | Vault `kv/break-glass/grafana` | 90 days | Grafana audit |
| Stripe (admin) | `break-glass@amccloud.com` | Vault `kv/break-glass/stripe` | 90 days | Stripe audit log |

#### Post-Use Procedure

After using a break-glass account:

1. Rotate the credential immediately
2. File an incident report explaining why normal auth was insufficient
3. Review and fix the authentication failure root cause
4. Notify security team via #ops-security

### Appendix E: Offline / Air-Gapped Operations Guide

#### Scenario: Complete Loss of External Network Connectivity

```bash
# 1. Verify connectivity status
curl -s --connect-timeout 5 https://api.github.com || echo "No external connectivity"

# 2. Switch AI providers to local-only
curl -X POST http://ai-orchestrator:8010/v1/providers/force \
  -H 'Content-Type: application/json' \
  -d '{"provider": "ollama", "model": "llama3.2:3b"}'

# 3. Verify local model availability
curl -s http://ollama:11434/api/tags | jq '.'

# 4. Disable external webhooks
for wf_id in $(curl -s http://n8n:5678/rest/workflows \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq -r '.data[] | select(.active == true) | .id'); do
  curl -X PATCH http://n8n:5678/rest/workflows/$wf_id \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -d '{"active": false}'
done

# 5. Disable Stripe-related billing operations
docker service scale billing-service=0

# 6. Switch to local logging (disable remote log shipping)
# Loki still works locally; disable promtail remote targets

# 7. Verify core functionality
# CRM, Marketing, Projects modules work without external deps
# AI uses local models (reduced quality but functional)
# n8n internal workflows still run
```

#### Operating Without AI Cloud Providers

| Feature | Normal | Air-Gapped |
|---------|--------|------------|
| Content generation | OpenAI / Anthropic | Ollama (llama3.2:3b) |
| Embeddings | OpenAI text-embedding-3-small | Ollama (nomic-embed-text) |
| Agents (complex) | GPT-4o / Claude 3.5 | Ollama (mistral:7b) |
| Agents (simple) | GPT-4o-mini | Ollama (llama3.2:3b) |
| Image generation | DALL-E / Stable Diffusion | Disabled |

### Appendix F: Frequently Used Commands Cheat Sheet

#### Docker / Swarm

```bash
# View all services
docker service ls

# View service logs
docker service logs --tail 50 <service>

# Restart a service
docker service update --force <service>

# Scale a service
docker service scale <service>=5

# Rollback a service
docker service rollback <service>

# Execute command in service container
docker exec -it $(docker ps -f "name=<service>" -q | head -1) bash

# View resource usage
docker stats --no-stream

# Clean up
docker system prune -af
```

#### PostgreSQL

```bash
# Connect to primary
psql -h postgres-primary -U amc -d amc

# Connect via PgBouncer
psql -h pgbouncer -U amc -d amc -p 6432

# Top 10 slow queries
SELECT queryid, LEFT(query, 80), calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;

# Current connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

# Kill a connection
SELECT pg_terminate_backend(<pid>);

# Database size
SELECT pg_size_pretty(pg_database_size('amc'));

# Table size
SELECT pg_size_pretty(pg_total_relation_size('contacts'));

# Check replication lag
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

#### Redis

```bash
# Ping
redis-cli -h redis-cache -a <password> ping

# Monitor keyspace
redis-cli -h redis-cache -a <password> --stat

# Big keys scan
redis-cli -h redis-cache -a <password> --bigkeys

# Delete by pattern
redis-cli -h redis-cache -a <password> --scan --pattern 'prefix:*' | xargs redis-cli -h redis-cache -a <password> DEL

# Check memory
redis-cli -h redis-cache -a <password> INFO memory

# Slow log
redis-cli -h redis-cache -a <password> SLOWLOG GET 10
```

#### RabbitMQ

```bash
# List queues
rabbitmqadmin list queues name messages consumers

# List connections
rabbitmqctl list_connections

# Get messages from queue
rabbitmqadmin get queue=amc.email.trigger count=5

# Purge queue
rabbitmqadmin purge queue name=amc.email.trigger

# Check cluster status
rabbitmqctl cluster_status
```

#### Qdrant

```bash
# List collections
curl -s http://qdrant:6333/collections | jq '.'

# Collection info
curl -s http://qdrant:6333/collections/{name} | jq '.'

# Cluster status
curl -s http://qdrant:6333/cluster | jq '.'

# Create snapshot
curl -X POST http://qdrant:6333/collections/{name}/snapshots
```

#### MinIO

```bash
# List buckets
mc ls source/

# List objects
mc ls source/tnt-abc123def/

# Copy/Mirror
mc cp local/file.ext source/bucket/
mc mirror local/dir/ source/bucket/

# Check disk
mc admin info source/

# Set policy
mc policy set public source/bucket/
```

#### Networking / DNS

```bash
# DNS lookup
nslookup app.amccloud.com

# Port check
nc -zv pgbouncer 6432

# SSL certificate check
echo | openssl s_client -servername app.amccloud.com -connect app.amccloud.com:443 2>/dev/null | openssl x509 -noout -dates

# HTTP check
curl -sfI https://app.amccloud.com/health

# Trace route
traceroute -n app.amccloud.com
```

#### Git / Deployments

```bash
# View recent commits
git log --oneline -10

# Tag a deployment
git tag deploy-$(date +%Y%m%d-%H%M)

# Rollback to previous deploy
git checkout <previous-deploy-tag>

# View diffs between deploys
git diff <tag-1>..<tag-2> --stat
```

---

> **End of Volume 14: Operations Manual**  
> *"Hope is not a strategy. Runbooks are."*
