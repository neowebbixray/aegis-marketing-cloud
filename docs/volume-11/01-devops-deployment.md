# Volume 11: DevOps, Deployment, Monitoring, Backup & Disaster Recovery

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering  
> **Date:** June 2026  
> **Author:** Platform Engineering Team  
> **Status:** ✅ Complete

---

## Table of Contents

1. [DevOps Philosophy](#1-devops-philosophy)
2. [Development Environment](#2-development-environment)
3. [CI/CD Pipeline (GitHub Actions)](#3-cicd-pipeline-github-actions)
4. [Docker Strategy](#4-docker-strategy)
5. [Production Deployment Architecture](#5-production-deployment-architecture)
6. [Database Operations](#6-database-operations)
7. [Redis Operations](#7-redis-operations)
8. [Qdrant Operations](#8-qdrant-operations)
9. [MinIO Operations](#9-minio-operations)
10. [RabbitMQ Operations](#10-rabbitmq-operations)
11. [Monitoring Stack (Prometheus + Grafana + Loki)](#11-monitoring-stack-prometheus--grafana--loki)
12. [Logging Strategy](#12-logging-strategy)
13. [Backup Strategy](#13-backup-strategy)
14. [Disaster Recovery](#14-disaster-recovery)
15. [Capacity Planning](#15-capacity-planning)
16. [Security Scanning Pipeline](#16-security-scanning-pipeline)
17. [Environment Matrix](#17-environment-matrix)

---

## 1. DevOps Philosophy

### 1.1 Infrastructure as Code (IaC) Everything

Every infrastructure component in AMC is defined as code — not a single resource is provisioned manually. This includes:

- **Compute:** Docker Compose (dev), Docker Swarm stacks (staging/prod), Kubernetes manifests (future)
- **Networking:** overlay networks, ingress rules, firewall policies, DNS records
- **Storage:** volume definitions, S3 bucket policies, lifecycle rules
- **Configuration:** environment variables, secrets, feature flags, service discovery
- **Monitoring:** dashboards, alert rules, scrape targets, log pipelines

```yaml
# .github/workflows/infra-validate.yml
# Every IaC change runs validation before merge
name: Infrastructure Validation

on:
  pull_request:
    paths:
      - 'deployment/**'
      - 'docker-compose*.yml'
      - 'docker-stack*.yml'
      - 'k8s/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Docker Compose
        run: docker compose -f deployment/docker-compose.yml config
      - name: Validate Swarm stack
        run: docker stack deploy --compose-file deployment/docker-stack.yml --dry-run
      - name: Validate K8s manifests
        run: |
          kubectl kustomize k8s/overlays/staging --dry-run=client
```

**Principle:** If it can be defined in code, it must be. Manual changes are forbidden as they create drift. Any operator who manually `exec`s into a container to fix an issue must open a PR that encodes the fix permanently.

### 1.2 Immutable Deployments — No SSH Patching

```mermaid
flowchart LR
    A[Code Commit] --> B[Build Image]
    B --> C[Scan Image]
    C --> D{Pass?}
    D -->|Yes| E[Push to Registry]
    D -->|No| F[Notify & Block]
    E --> G[Deploy New Image]
    G --> H[Health Check]
    H -->|Pass| I[Scale Down Old]
    H -->|Fail| J[Rollback to Previous Image]
```

**Rules:**
- Containers are **never** patched at runtime. Every fix requires a new build + deploy cycle.
- SSH access to production containers is **disabled** (no `ssh` daemon, no `docker exec` shell).
- Emergency hotfixes follow the same pipeline as normal releases — only the review process is expedited.
- Configuration changes (environment variables, feature flags) are the **only** live mutation allowed, and they propagate via service restart or sidecar reload.

### 1.3 Observability as a Feature

Observability is not a bolt-on tool — it ships as a first-class feature of every service. The contract:

| Concern | Implementation | SLA |
|---------|---------------|-----|
| **Logging** | Structured JSON via `structlog` (Python) / `pino` (Node) | Every request |
| **Metrics** | Prometheus client counters, histograms, gauges | Every endpoint |
| **Tracing** | OpenTelemetry with W3C `traceparent` propagation | Every span |
| **Health** | `/health` (liveness), `/ready` (readiness), `/metrics` | Every service |

```python
# Every FastAPI service enforces this in its lifespan
@app.on_event("startup")
async def startup():
    setup_tracing(service_name=os.getenv("SERVICE_NAME", "unknown"))
    setup_metrics(service_name=os.getenv("SERVICE_NAME"))
    logger.info("service_started", service=os.getenv("SERVICE_NAME"))
```

### 1.4 Failure Is Expected — Design for Graceful Degradation

AMC treats failure as a normal operating condition. Every service must:

1. **Start without its dependencies** — If Redis is down, the API still returns cached results or degrades gracefully (e.g., 15-minute stale cache instead of 500).
2. **Retry with exponential backoff** — All inter-service calls use configurable retry policies (3 attempts, jitter).
3. **Circuit break** — After N consecutive failures to a dependency, the caller opens the circuit and serves degraded responses.
4. **Bulkhead** — Each tenant's requests are isolated so one noisy tenant cannot exhaust resources.

```python
# lib/circuit_breaker.py
from aiocircuitbreaker import CircuitBreaker

redis_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    name="redis-cache",
)

@redis_breaker
async def get_cached_or_fallback(key: str, fallback_fn):
    try:
        return await cache.get(key)
    except ConnectionError:
        logger.warning("cache_unavailable", key=key)
        return await fallback_fn()  # serve stale or recompute
```

### 1.5 Security Scanning in Every Pipeline Stage

Security is not a phase at the end — it runs at **every** stage of the pipeline:

| Stage | Tool | What It Checks |
|-------|------|---------------|
| **Pre-commit** | `pre-commit` hooks, `gitleaks` | Secrets in source, formatting |
| **Lint** | `ruff`, `eslint-security` | Code quality, common vulns |
| **Type-check** | `mypy`, `tsc` | Type confusion, injection risks |
| **Unit test** | `pytest`, `jest` | Functional correctness |
| **Build** | `docker build` with `--squash` | Minimal attack surface |
| **Security scan** | `trivy`, `pip-audit`, `npm audit` | CVEs in dependencies |
| **DAST** | OWASP ZAP (staging) | Runtime web vulns |
| **Post-deploy** | `kube-bench`, `kube-hunter` | Cluster CIS benchmarks |

---

## 2. Development Environment

### 2.1 Docker Compose File Structure (~25 Services)

```yaml
# deployment/docker-compose.yml — Base file for all environments
version: "3.9"

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

x-healthcheck: &default-healthcheck
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 30s

services:
  # ── Presentation Layer ──
  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8000/api/v1/graphql
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
      - NODE_ENV=development
    volumes:
      - ../frontend:/app
      - /app/node_modules
      - /app/.next
    command: npm run dev
    depends_on:
      api-gateway:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/api/health', r => process.exit(r.statusCode !== 200))"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── API Gateway Layer ──
  api-gateway:
    build:
      context: ../backend
      dockerfile: deployment/Dockerfile.api-gateway
      target: development
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - DATABASE_URL_WRITE=postgresql://amc:***@postgres-primary:5432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - REDIS_SESSION_URL=redis://:amc@redis-sessions:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - QDRANT_URL=http://qdrant:6333
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=***      - MINIO_USE_SSL=false
      - N8N_URL=http://n8n:5678
      - OLLAMA_URL=http://ollama:11434
      - NIM_ENDPOINT=http://nim:8001/v1
      - ENVIRONMENT=development
      - SERVICE_NAME=api-gateway
      - LOG_LEVEL=DEBUG
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
      - UNLEASH_URL=http://unleash:4242/api
      - SECRET_KEY=dev-se...on
    volumes:
      - ../backend:/app
    command: uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
    depends_on:
      pgbouncer:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Modular Monolith ──
  monolith:
    build:
      context: ../backend
      dockerfile: deployment/Dockerfile.monolith
      target: development
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - DATABASE_URL_WRITE=postgresql://amc:***@postgres-primary:5432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - QDRANT_URL=http://qdrant:6333
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=***      - MINIO_USE_SSL=false
      - OLLAMA_URL=http://ollama:11434
      - ENVIRONMENT=development
      - SERVICE_NAME=monolith
      - LOG_LEVEL=DEBUG
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
      - SECRET_KEY=dev-se...on
    volumes:
      - ../backend:/app
    command: uvicorn monolith.main:app --reload --host 0.0.0.0 --port 8001 --log-level debug
    depends_on:
      pgbouncer:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Auth Service ──
  auth-service:
    build:
      context: ../backend/auth
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_SESSION_URL=redis://:amc@redis-sessions:6379/0
      - JWT_SECRET=dev-jw...on
      - ENVIRONMENT=development
      - SERVICE_NAME=auth-service
    volumes:
      - ../backend/auth:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8002
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Billing Service ──
  billing-service:
    build:
      context: ../backend/billing
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - STRIPE_API_KEY=***      - STRIPE_WEBHOOK_SECRET=whsec_...er
      - ENVIRONMENT=development
      - SERVICE_NAME=billing-service
    volumes:
      - ../backend/billing:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8003
    depends_on:
      pgbouncer:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Notification Service ──
  notification-service:
    build:
      context: ../backend/notifications
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - SMTP_HOST=mailhog:1025
      - SMTP_PORT=1025
      - SMTP_USER=
      - SMTP_PASS=
      - TWILIO_ACCOUNT_SID=placeholder
      - TWILIO_AUTH_TOKEN=***      - ENVIRONMENT=development
      - SERVICE_NAME=notification-service
    volumes:
      - ../backend/notifications:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8004
    depends_on:
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Media Service ──
  media-service:
    build:
      context: ../backend/media
      dockerfile: Dockerfile.dev
    environment:
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=***      - MINIO_USE_SSL=false
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - ENVIRONMENT=development
      - SERVICE_NAME=media-service
    volumes:
      - ../backend/media:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8005
    depends_on:
      minio:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── AI Orchestrator ──
  ai-orchestrator:
    build:
      context: ../backend/ai
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - NIM_ENDPOINT=http://nim:8001/v1
      - OPENAI_API_KEY=${OPEN...-}
      - ANTHROPIC_API_KEY=${ANTH...-}
      - ENVIRONMENT=development
      - SERVICE_NAME=ai-orchestrator
    volumes:
      - ../backend/ai:/app
    command: uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8010
    depends_on:
      qdrant:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── AI Agent Runtime (Hermes) ──
  ai-agent-runtime:
    build:
      context: ../backend/ai/agent-runtime
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - ENVIRONMENT=development
      - SERVICE_NAME=ai-agent-runtime
    volumes:
      - ../backend/ai/agent-runtime:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8011
    depends_on:
      qdrant:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── AI Memory Service ──
  ai-memory:
    build:
      context: ../backend/ai/memory
      dockerfile: Dockerfile.dev
    environment:
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - ENVIRONMENT=development
      - SERVICE_NAME=ai-memory
    volumes:
      - ../backend/ai/memory:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8012
    depends_on:
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8012/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── AI NIM (NVIDIA Inference Microservice) ──
  nim:
    image: nvcr.io/nvidia/nim:latest
    ports:
      - "8001:8001"
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - nim-cache:/opt/nim/.cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/v1/health/ready"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Analytics Service ──
  analytics-service:
    build:
      context: ../backend/analytics
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - DATABASE_URL_READ=postgresql://amc:***@postgres-replica:5432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - ENVIRONMENT=development
      - SERVICE_NAME=analytics-service
    volumes:
      - ../backend/analytics:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8020
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Admin Service ──
  admin-service:
    build:
      context: ../backend/admin
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - ENVIRONMENT=development
      - SERVICE_NAME=admin-service
    volumes:
      - ../backend/admin:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8030
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8030/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Marketplace Service ──
  marketplace-service:
    build:
      context: ../backend/marketplace
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - ENVIRONMENT=development
      - SERVICE_NAME=marketplace-service
    volumes:
      - ../backend/marketplace:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8040
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8040/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Webhook Service ──
  webhook-service:
    build:
      context: ../backend/webhooks
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc
      - REDIS_URL=redis://:amc@redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:***@rabbitmq:5672/
      - ENVIRONMENT=development
      - SERVICE_NAME=webhook-service
    volumes:
      - ../backend/webhooks:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8050
    depends_on:
      rabbitmq:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050/health"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── n8n Workflow Engine ──
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    volumes:
      - n8n-data:/home/node/.n8n
    environment:
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - N8N_HOST=localhost
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=pgbouncer
      - DB_POSTGRESDB_PORT=6432
      - DB_POSTGRESDB_DATABASE=amc_n8n
      - DB_POSTGRESDB_USER=amc
      - DB_POSTGRESDB_PASSWORD=***      - N8N_METRICS=true
      - N8N_METRICS_INCLUDE_DEFAULT_METRICS=true
      - N8N_METRICS_PREFIX=n8n_
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:5678/healthz"]
      <<: *default-healthcheck
    logging: *default-logging

  # ── Data Layer: PostgreSQL ──
  postgres-primary:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: amc
      POSTGRES_PASSWORD: amc
      POSTGRES_DB: amc
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ../deployment/postgres/init:/docker-entrypoint-initdb.d
      - ../deployment/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U amc -d amc"]
      interval: 5s
      timeout: 3s
      retries: 5
    logging: *default-logging

  postgres-replica:
    image: postgres:16-alpine
    depends_on:
      postgres-primary:
        condition: service_healthy
    volumes:
      - pg-replica-data:/var/lib/postgresql/data
    environment:
      PGUSER: amc
      PGPASSWORD: amc
    command: >
      bash -c "
        until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U amc -vP -W --slot=replica_slot --create-slot; do
          sleep 2;
        done;
        echo 'primary_conninfo = host=postgres-primary port=5432 user=amc password=amc' >> /var/lib/postgresql/data/postgresql.conf;
        echo 'primary_slot_name = replica_slot' >> /var/lib/postgresql/data/postgresql.conf;
        pg_ctl -D /var/lib/postgresql/data -l /var/log/postgres.log start;
        tail -f /var/log/postgres.log;
      "
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U amc -d amc"]
      interval: 10s
    logging: *default-logging

  # ── PgBouncer Connection Pooler ──
  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DB_USER: amc
      DB_PASSWORD: amc
      DB_HOST: postgres-primary
      DB_PORT: "5432"
      DB_NAME: amc
      POOL_MODE: transaction
      MAX_CLIENT_CONN: "500"
      DEFAULT_POOL_SIZE: "50"
      RESERVE_POOL_SIZE: "10"
      SERVER_RESET_QUERY: DISCARD ALL
    ports:
      - "6432:6432"
    depends_on:
      postgres-primary:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "pgbouncer -q show databases"]
      interval: 10s
    logging: *default-logging

  # ── Redis Cache ──
  redis-cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --requirepass amc
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "amc", "ping"]
      interval: 5s
    logging: *default-logging

  # ── Redis Sessions ──
  redis-sessions:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - redis-sessions-data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync always
      --maxmemory 1gb
      --maxmemory-policy noeviction
      --requirepass amc
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "amc", "ping"]
      interval: 5s
    logging: *default-logging

  # ── Redis Queue (Bull/BullMQ) ──
  redis-queue:
    image: redis:7-alpine
    ports:
      - "6381:6379"
    volumes:
      - redis-queue-data:/data
    command: >
      redis-server
      --appendonly yes
      --appendfsync everysec
      --maxmemory 4gb
      --maxmemory-policy noeviction
      --requirepass amc
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "amc", "ping"]
      interval: 5s
    logging: *default-logging

  # ── Qdrant Vector DB ──
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant-data:/qdrant/storage
      - ../deployment/qdrant/config.yaml:/qdrant/config/production.yaml
    environment:
      QDRANT__SERVICE__GRPC_PORT: "6334"
      QDRANT__SERVICE__GRPC_ENABLED: "true"
    command: ["/qdrant/entrypoint.sh"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 15s
    logging: *default-logging

  # ── MinIO Object Storage ──
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      MINIO_DOMAIN: minio
      MINIO_STORAGE_CLASS_STANDARD: EC:2
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 15s
    logging: *default-logging

  # ── RabbitMQ Message Broker ──
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
      - ../deployment/rabbitmq/definitions.json:/etc/rabbitmq/definitions.json
      - ../deployment/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf
    environment:
      RABBITMQ_DEFAULT_USER: amc
      RABBITMQ_DEFAULT_PASS: amc
      RABBITMQ_ERLANG_COOKIE: amc-cluster-cookie-dev
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 10s
      retries: 5
    logging: *default-logging

  # ── Monitoring ──
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - prometheus-data:/prometheus
      - ../deployment/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ../deployment/prometheus/alert-rules.yml:/etc/prometheus/alert-rules.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:9090/-/healthy"]
      interval: 15s
    logging: *default-logging

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_INSTALL_PLUGINS: grafana-piechart-panel, grafana-worldmap-panel
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_SERVER_ROOT_URL: http://localhost:3001
    volumes:
      - grafana-data:/var/lib/grafana
      - ../deployment/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ../deployment/grafana/datasources:/etc/grafana/provisioning/datasources
      - ../deployment/grafana/alerting:/etc/grafana/provisioning/alerting
    depends_on:
      prometheus:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3000/api/health"]
      interval: 15s
    logging: *default-logging

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
      - ../deployment/loki/loki-config.yaml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3100/ready"]
      interval: 15s
    logging: *default-logging

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ../deployment/loki/promtail-config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml
    depends_on:
      loki:
        condition: service_healthy
    logging: *default-logging

  tempo:
    image: grafana/tempo:latest
    ports:
      - "4317:4317"
      - "4318:4318"
    volumes:
      - tempo-data:/tmp/tempo
      - ../deployment/tempo/tempo.yaml:/etc/tempo.yaml
    command: -config.file=/etc/tempo.yaml
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3200/ready"]
      interval: 15s
    logging: *default-logging

  # ── Development Tools ──
  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"
      - "8025:8025"
    logging: *default-logging

  ngrok:
    image: ngrok/ngrok:latest
    command: http api-gateway:8000 --domain=${NGROK_DOMAIN:-}
    environment:
      NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN:-}
    depends_on:
      api-gateway:
        condition: service_healthy
    logging: *default-logging

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
      - ../deployment/ollama/models:/models
    environment:
      OLLAMA_HOST: 0.0.0.0
      OLLAMA_MODELS: /models
    entrypoint: >
      bash -c "ollama serve &
      sleep 5 &&
      ollama pull llama3.2:3b &&
      ollama pull nomic-embed-text &&
      ollama pull mistral:7b &&
      wait"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      retries: 10
      start_period: 120s
    logging: *default-logging

  # ── Feature Flags (Unleash) ──
  unleash:
    image: unleashorg/unleash-server:latest
    ports:
      - "4242:4242"
    environment:
      DATABASE_URL: postgresql://amc:***@pgbouncer:6432/amc_unleash
      DATABASE_NAME: amc_unleash
      UNLEASH_DATABASE_USER: amc
      UNLEASH_DATABASE_PASSWORD: amc
      UNLEASH_DATABASE_HOST: pgbouncer
      UNLEASH_DATABASE_PORT: 6432
      INIT_ADMIN_API_TOKENS: "*:*.dev-unleash-token"
      LOG_LEVEL: debug
    depends_on:
      pgbouncer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:4242/health"]
      <<: *default-healthcheck
    logging: *default-logging

volumes:
  pg-data:
  pg-replica-data:
  redis-data:
  redis-sessions-data:
  redis-queue-data:
  qdrant-data:
  minio-data:
  rabbitmq-data:
  n8n-data:
  prometheus-data:
  grafana-data:
  loki-data:
  tempo-data:
  ollama-data:
  unleash-data:
  nim-cache:

networks:
  default:
    name: amc-dev
    driver: bridge
```

**Service Count Summary:**

| Layer | Services | Count |
|-------|----------|-------|
| Presentation | `frontend` | 1 |
| API Gateway | `api-gateway` | 1 |
| Core Services | `monolith`, `auth-service`, `billing-service`, `notification-service`, `media-service` | 5 |
| AI Layer | `ai-orchestrator`, `ai-agent-runtime`, `ai-memory`, `nim`, `ollama` | 5 |
| Analytics | `analytics-service` | 1 |
| Admin | `admin-service` | 1 |
| Platform | `marketplace-service`, `webhook-service`, `n8n`, `unleash` | 4 |
| Data | `postgres-primary`, `postgres-replica`, `pgbouncer`, `redis-cache`, `redis-sessions`, `redis-queue`, `qdrant`, `minio`, `rabbitmq` | 9 |
| Monitoring | `prometheus`, `grafana`, `loki`, `promtail`, `tempo` | 5 |
| Dev Tools | `mailhog`, `ngrok` | 2 |
| **Total** | | **34** |

### 2.2 Hot-Reload Configurations

#### Next.js (Frontend)

```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json ./
RUN npm ci && npm cache clean --force

# Copy source (will be overridden by volume mount)
COPY . .

EXPOSE 3000

ENV NODE_ENV=development \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "run", "dev"]
```

The `WATCHPACK_POLLING=true` flag is critical on Docker Desktop (macOS/Windows) where filesystem events don't propagate to container mounts.

#### FastAPI (Backend Services)

```dockerfile
# backend/deployment/Dockerfile.api-gateway
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Development target ──
FROM base AS development
COPY backend/requirements/dev.txt requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install watchfiles for hot reload
RUN pip install watchfiles

EXPOSE 8000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["uvicorn", "api_gateway.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--reload-dir", "/app"]

# ── Production target ──
FROM base AS production
COPY backend/ .
RUN useradd -m -u 1000 amc && chown -R amc:amc /app
USER amc

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2.3 ngrok for Webhook Testing

```yaml
# deployment/docker-compose.override.dev.yml (dev only)
services:
  ngrok:
    image: ngrok/ngrok:latest
    command: http api-gateway:8000 --domain=${NGROK_DOMAIN:-}
    environment:
      NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
    ports:
      - "4040:4040"
    depends_on:
      api-gateway:
        condition: service_healthy
```

**Workflow:**

1. Set `NGROK_AUTHTOKEN` in `.env.local`
2. Start the stack: `docker compose up ngrok`
3. Get the public URL from `http://localhost:4040/status`
4. Configure webhook endpoints in external services (Stripe, SendGrid, etc.) to point to `https://<your-domain>.ngrok.io/api/v1/webhooks/stripe`
5. Webhooks are forwarded to the local `api-gateway` service

### 2.4 Local AI with Ollama

Ollama runs inside the Docker Compose stack alongside the AI services, enabling fully offline AI development:

```bash
# Pull models on first startup (done automatically in docker-compose)
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull mistral:7b
docker compose exec ollama ollama pull codellama:7b
```

**Model strategy for local development:**

| Use Case | Model | Size | RAM Required |
|----------|-------|------|-------------|
| Chat / Agent | `llama3.2:3b` | 2.0 GB | 4 GB |
| Embeddings | `nomic-embed-text` | 0.3 GB | 1 GB |
| Code generation | `codellama:7b` | 3.8 GB | 8 GB |
| Mistral alternative | `mistral:7b` | 4.1 GB | 8 GB |
| Vision (future) | `llava:7b` | 4.5 GB | 8 GB |

The AI layer automatically falls back to Ollama when cloud LLM API keys are absent:

```python
# backend/ai/providers.py
class LLMProvider:
    def __init__(self):
        self.providers = []
        if os.getenv("OPENAI_API_KEY"):
            self.providers.append(OpenAIProvider())
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers.append(AnthropicProvider())
        # Always available — local fallback
        self.providers.append(OllamaProvider(base_url=os.getenv("OLLAMA_URL", "http://ollama:11434")))
```

### 2.5 Local MinIO

MinIO provides S3-compatible object storage for local development:

```bash
# Console: http://localhost:9001 (credentials: minioadmin / minioadmin)
# API: http://localhost:9000

# Create development buckets
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb local/amc-assets
docker compose exec minio mc mb local/amc-uploads
docker compose exec minio mc mb local/amc-exports
docker compose exec minio mc mb local/amc-ai-models
docker compose exec minio mc policy set public local/amc-assets
```

### 2.6 Seed Data Scripts

```bash
# scripts/seed-dev.sh — Run after first docker compose up
#!/bin/bash
set -euo pipefail

echo "⏳ Waiting for services..."
docker compose exec -T pgbouncer bash -c "until pg_isready -U amc; do sleep 1; done"
sleep 5

echo "📦 Running database migrations..."
docker compose exec -T api-gateway alembic upgrade head
docker compose exec -T monolith alembic upgrade head

echo "🌱 Seeding data..."
docker compose exec -T api-gateway python scripts/seed_tenants.py --count 5
docker compose exec -T api-gateway python scripts/seed_users.py --count 50
docker compose exec -T api-gateway python scripts/seed_campaigns.py --count 20
docker compose exec -T monolith python scripts/seed_contacts.py --count 10000
docker compose exec -T monolith python scripts/seed_ai_agents.py --count 10

echo "📊 Seeding analytics data..."
docker compose exec -T analytics-service python scripts/seed_analytics.py --days 90

echo "🧠 Creating vector embeddings..."
docker compose exec -T ai-memory python scripts/seed_memory.py --documents 500

echo "🪣 Setting up MinIO buckets..."
docker compose exec -T minio sh -c '
  mc alias set local http://localhost:9000 minioadmin minioadmin
  for bucket in amc-assets amc-uploads amc-exports amc-ai-models; do
    mc mb local/$bucket --ignore-existing
  done
  mc policy set public local/amc-assets
'

echo "🔧 Setting up RabbitMQ queues..."
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.email.trigger durable=true
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.sms.trigger durable=true
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.webhook.deliver durable=true
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.media.process durable=true
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.ai.inference durable=true
docker compose exec -T rabbitmq rabbitmqadmin declare queue name=amc.analytics.ingest durable=true

echo "✅ Dev environment seeded successfully!"
```

### 2.7 Environment Variable Management

Each service has a corresponding `.env.example` template checked into the repository:

```
backend/.env.example
backend/auth/.env.example
backend/billing/.env.example
backend/notifications/.env.example
backend/media/.env.example
backend/ai/.env.example
backend/analytics/.env.example
backend/admin/.env.example
backend/marketplace/.env.example
backend/webhooks/.env.example
frontend/.env.local.example
```

```bash
# Usage: copy .env.example to .env and customize
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# Validate all required variables are set
scripts/validate-env.sh
```

```bash
# scripts/validate-env.sh
#!/bin/bash
set -euo pipefail

required_vars=(
  "SECRET_KEY"
  "DATABASE_URL"
  "REDIS_URL"
  "RABBITMQ_URL"
)

missing=0
for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ Missing required env var: $var"
    missing=1
  fi
done

if [ "$missing" -eq 1 ]; then
  exit 1
fi
echo "✅ All required environment variables are set"
```

---

## 3. CI/CD Pipeline (GitHub Actions)

### 3.1 Pipeline Stages

```mermaid
flowchart LR
    PR[Pull Request] --> LINT[Lint & Format]
    LINT --> TYPE[Type Check]
    TYPE --> UNIT[Unit Tests]
    UNIT --> BUILD[Build Images]
    BUILD --> SCAN[Security Scan]
    SCAN --> INTEGRATION[Integration Tests]
    INTEGRATION -->|main branch| DEPLOY[Deploy]
    INTEGRATION -->|other branches| DONE[Done ✅]

    subgraph Deploy[Deploy Stage]
        direction LR
        MIGRATE[Run Migrations]
        BLUE[Deploy Blue Stack]
        SMOKE[Smoke Tests]
        SWAP[Swap Traffic]
        OBSERVE[Observation Period]
    end

    DEPLOY --> MIGRATE
    MIGRATE --> BLUE
    BLUE --> SMOKE
    SMOKE -->|Pass| SWAP
    SMOKE -->|Fail| ROLLBACK[Auto Rollback]
    SWAP --> OBSERVE
    OBSERVE -->|Pass| CUTOVER[Done ✅]
    OBSERVE -->|Fail| ROLLBACK
```

**Stage details:**

| Stage | Tool(s) | Avg. Time | Gate |
|-------|---------|-----------|------|
| **Lint** | `ruff`, `prettier`, `eslint`, `markdownlint` | 2 min | Must pass |
| **Type Check** | `mypy` (strict), `tsc` (strict) | 3 min | Must pass |
| **Unit Test** | `pytest` with coverage ≥80%, `jest` with coverage ≥80% | 5 min | Coverage gate |
| **Build** | `docker buildx` with multi-stage, layer caching | 8 min | Must succeed |
| **Security Scan** | `trivy`, `pip-audit`, `npm audit`, `gitleaks` | 5 min | No CRITICAL/HIGH |
| **Integration Test** | `pytest` integration suite, Playwright e2e | 12 min | Must pass |
| **Deploy** | Blue-green with health observation | 10 min | Manual approval (prod) |

### 3.2 Branch Strategy

```mermaid
flowchart LR
    subgraph Feature[Feature Branches]
        FEAT1[feature/AMP-1234-campaign-builder]
        FEAT2[feature/AMP-5678-ai-writer]
    end

    subgraph Develop[Develop Branch]
        DEV[develop]
    end

    subgraph Staging[Staging Branch]
        STG[staging]
    end

    subgraph Main[Main Branch]
        MAIN[main]
    end

    subgraph Production[Production Tags]
        PROD[v1.x.x]
    end

    FEAT1 --> DEV
    FEAT2 --> DEV
    DEV -->|Release Cut| STG
    STG -->|QA Pass| MAIN
    MAIN -->|Release| PROD
```

| Branch | Purpose | Deploy Target | Protection |
|--------|---------|---------------|------------|
| `feature/*` | Feature work | None | None (pre-commit hooks) |
| `develop` | Integration | `dev.amc.dev` | PR required, 1 approval |
| `staging` | Pre-production validation | `staging.amc.dev` | PR required, 2 approvals |
| `main` | Release ready | `app.amccloud.com` | PR required, 2 approvals, frozen for releases |
| `release/*` | Release branches from `main` | `app.amccloud.com` | Hotfix bypass, emergency approvals |

### 3.3 PR Checks Automation

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: ghcr.io/aegis-marketing-cloud
  TAG: pr-${{ github.event.pull_request.number }}-${{ github.sha }}

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Python linting tools
        run: pip install ruff mypy
      
      - name: Python lint (ruff)
        run: ruff check backend/ --output-format=github
      
      - name: Python type check (mypy)
        run: mypy backend/ --strict --ignore-missing-imports
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: TypeScript lint and type check
        run: |
          cd frontend
          npm ci
          npm run lint
          npm run type-check
      
      - name: Secret scanning (Gitleaks)
        uses: gitleaks/gitleaks-action@v2
        with:
          config-path: .gitleaks.toml
      
      - name: Markdown lint
        uses: avto-dev/markdown-lint@v1
        with:
          args: 'docs/**/*.md'

  unit-tests:
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: amc
          POSTGRES_PASSWORD: amc
          POSTGRES_DB: amc_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready -U amc
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      minio:
        image: minio/minio:latest
        ports:
          - 9000:9000
        env:
          MINIO_ROOT_USER: minioadmin
          MINIO_ROOT_PASSWORD: minioadmin
        options: >-
          --health-cmd "curl -f http://localhost:9000/minio/health/live"
          --health-interval 5s
    steps:
      - uses: actions/checkout@v4
      
      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements/dev.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install backend dependencies
        run: |
          cd backend
          pip install -r requirements/prod.txt -r requirements/dev.txt
          pip install -e .
      
      - name: Run backend unit tests
        run: |
          cd backend
          pytest tests/unit/ \
            --cov=. \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results/unit.xml \
            -x -v
        env:
          DATABASE_URL: postgresql://amc:***@localhost:5432/amc_test
          REDIS_URL: redis://localhost:6379/0
      
      - name: Upload backend coverage
        uses: codecov/codecov-action@v3
        with:
          files: backend/coverage.xml
          flags: backend
      
      - name: Setup Node and run frontend tests
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
        if: always()
      
      - name: Run frontend tests
        run: |
          cd frontend
          npm ci
          npm run test:ci -- --coverage --coverageDirectory=coverage
        env:
          CI: true
        if: always()
      
      - name: Upload frontend coverage
        uses: codecov/codecov-action@v3
        with:
          files: frontend/coverage/lcov.info
          flags: frontend
        if: always()

  build-and-scan:
    needs: unit-tests
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Cache Docker layers
        uses: actions/cache@v4
        with:
          path: /tmp/.buildx-cache
          key: ${{ runner.os }}-buildx-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-buildx-
      
      - name: Build images
        run: |
          docker buildx build \
            --cache-from=type=local,src=/tmp/.buildx-cache \
            --cache-to=type=local,dest=/tmp/.buildx-cache-new \
            --load \
            -f deployment/Dockerfile.api-gateway \
            -t $REGISTRY/api-gateway:$TAG .
          
          docker buildx build \
            --cache-from=type=local,src=/tmp/.buildx-cache \
            --cache-to=type=local,dest=/tmp/.buildx-cache-new \
            --load \
            -f deployment/Dockerfile.monolith \
            -t $REGISTRY/monolith:$TAG .
          
          # Build all other services
          for svc in auth-service billing-service notification-service media-service \
                     ai-orchestrator ai-agent-runtime ai-memory analytics-service \
                     admin-service marketplace-service webhook-service; do
            docker buildx build \
              --cache-from=type=local,src=/tmp/.buildx-cache \
              --cache-to=type=local,dest=/tmp/.buildx-cache-new \
              --load \
              -f backend/$svc/Dockerfile \
              -t $REGISTRY/$svc:$TAG backend/$svc
          done
      
      - name: Move cache
        run: |
          rm -rf /tmp/.buildx-cache
          mv /tmp/.buildx-cache-new /tmp/.buildx-cache
      
      - name: Trivy scan (api-gateway)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/api-gateway:${{ env.TAG }}
          severity: CRITICAL,HIGH
          exit-code: 1
          format: sarif
          output: trivy-results-api-gateway.sarif
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results-api-gateway.sarif
        if: always()
      
      - name: Dependency scan (pip-audit)
        run: |
          cd backend
          pip install pip-audit
          pip-audit -r requirements/prod.txt --desc on
      
      - name: Dependency scan (npm audit)
        run: |
          cd frontend
          npm ci
          npm audit --audit-level=high

  integration-tests:
    needs: build-and-scan
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      
      - name: Start full stack
        run: |
          docker compose -f deployment/docker-compose.yml \
            -f deployment/docker-compose.ci.yml \
            up -d --wait --wait-timeout 120
      
      - name: Wait for services
        run: |
          sleep 30
          ./scripts/wait-for-health.sh 15
      
      - name: Run integration tests
        run: |
          docker compose exec -T api-gateway \
            pytest tests/integration/ \
            --junitxml=test-results/integration.xml \
            -x -v
      
      - name: Run e2e tests
        run: |
          cd frontend
          npm run test:e2e
        env:
          BASE_URL: http://localhost:3000
      
      - name: Run smoke tests
        run: |
          ./scripts/smoke-test.sh http://localhost:8000
      
      - name: Tear down
        if: always()
        run: docker compose -f deployment/docker-compose.yml down -v

  deploy-staging:
    if: github.ref == 'refs/heads/develop' && success()
    needs: integration-tests
    runs-on: ubuntu-latest
    environment: staging
    concurrency: staging
    steps:
      - name: Deploy to staging
        run: |
          # Deploy with current sha tag
          docker stack deploy -c deployment/docker-stack.staging.yml amc-staging
      
      - name: Run post-deploy smoke tests
        run: |
          sleep 60
          ./scripts/smoke-test.sh https://staging.amc.dev
          ./scripts/test-migrations.sh
    
    # ── Production deployment requires manual approval ──
  deploy-production:
    if: github.ref == 'refs/heads/main' && success()
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    concurrency: production
    steps:
      - name: Wait for approval
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ secrets.GITHUB_TOKEN }}
          approvers: ${{ vars.PRODUCTION_APPROVERS }}
          minimum-approvals: 2
          issue-title: "Deploy to Production"
          issue-body: "Deploy ${{ github.sha }} to production?"
      
      - name: Tag release
        run: |
          VERSION=$(cat VERSION)
          git tag v$VERSION-${{ github.sha }}
          git push origin v$VERSION-${{ github.sha }}
      
      - name: Blue-Green Deploy
        run: ./scripts/blue-green-deploy.sh production ${{ github.sha }}
      
      - name: Run smoke tests against production
        run: |
          sleep 60
          ./scripts/smoke-test.sh https://app.amccloud.com
```

### 3.4 Build Caching Strategy

**Docker layer caching:**

```hcl
# docker-bake.hcl — Efficient multi-service builds
variable "REGISTRY" {
  default = "ghcr.io/aegis-marketing-cloud"
}

variable "TAG" {
  default = "latest"
}

group "default" {
  targets = [
    "api-gateway",
    "monolith",
    "frontend",
    "auth-service",
    "billing-service",
    "notification-service",
    "media-service",
    "ai-orchestrator",
    "ai-agent-runtime",
    "ai-memory",
    "analytics-service",
    "admin-service",
    "marketplace-service",
    "webhook-service",
  ]
}

target "api-gateway" {
  context = "."
  dockerfile = "deployment/Dockerfile.api-gateway"
  target = "production"
  tags = ["${REGISTRY}/api-gateway:${TAG}"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}
```

**npm/pip caching in CI:**

```yaml
# Shared caching configuration
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pip-audit
    key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements/*.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache npm packages
  uses: actions/cache@v4
  with:
    path: |
      frontend/node_modules
      ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('frontend/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-npm-
```

### 3.5 Multi-Stage Docker Builds

```dockerfile
# deployment/Dockerfile.monolith — Example multi-stage build
# ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cache Python dependencies as a layer
COPY backend/requirements/prod.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r prod.txt

# ── Stage 2: Runtime ──
FROM python:3.12-slim AS production

WORKDIR /app

# Create non-root user
RUN groupadd -r amc && useradd -r -g amc -u 1000 amc

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Copy application code
COPY backend/ .

# Security hardening
RUN chown -R amc:amc /app && \
    chmod -R 750 /app && \
    chmod 640 /app/.env

USER amc

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "monolith.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

### 3.6 Image Tagging Strategy

```yaml
# Image tagging policy
tags:
  - "<git-sha>"           # Unique, immutable — primary identifier
  - "v<semver>"            # Release version (e.g., v1.5.3)
  - "latest"               # Latest stable deploy
  - "staging-latest"       # Latest staging deploy
  - "pr-<number>"          # PR builds for testing
```

**Tag lifecycle:**

| Tag | Purpose | Retention |
|-----|---------|-----------|
| `git-sha` | Traceable deploy artifact | Permanent |
| `v<semver>` | Release tracking | Permanent |
| `latest` | Current production | Updated each deploy |
| `staging-latest` | Current staging | Updated each deploy |
| `pr-*` | PR test images | Deleted after PR merge |

### 3.7 Artifact Registry Configuration

AMC uses **GitHub Container Registry (ghcr.io)** as its primary artifact registry:

```bash
# Login
echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

# Push
docker push ghcr.io/aegis-marketing-cloud/api-gateway:abc123def
docker push ghcr.io/aegis-marketing-cloud/monolith:v1.5.3

# Pull with authentication
docker pull ghcr.io/aegis-marketing-cloud/api-gateway:abc123def
```

**Registry organization:**

```
ghcr.io/aegis-marketing-cloud/
  ├── api-gateway
  ├── monolith
  ├── frontend
  ├── auth-service
  ├── billing-service
  ├── notification-service
  ├── media-service
  ├── ai-orchestrator
  ├── ai-agent-runtime
  ├── ai-memory
  ├── analytics-service
  ├── admin-service
  ├── marketplace-service
  ├── webhook-service
  └── ...
```

**Retention policy:** Images older than 90 days are automatically pruned by a nightly GitHub Action, except for tagged releases (`v*`).

### 3.8 Environment Promotion Gates

```yaml
# .github/environments.yml
environments:
  development:
    approvals: 0
    required_checks:
      - lint
      - unit-tests
    deployment_branch: develop
  
  staging:
    approvals: 0
    required_checks:
      - lint
      - unit-tests
      - build-and-scan
      - integration-tests
    deployment_branch: develop
  
  production:
    approvals: 2
    required_approvers:
      - team-lead
      - qa-lead
      - on-call-engineer
    required_checks:
      - lint
      - unit-tests
      - build-and-scan
      - integration-tests
      - deploy-staging
    deployment_branch: main
    wait_timer: 5  # 5-minute cool-down before deployment
```

### 3.9 Blue-Green Deployment Workflow

```mermaid
flowchart TB
    subgraph Before[Before Deploy]
        LB[Load Balancer] --> GREEN["Green Stack (Active) v1.5.3"]
        GREEN --> DB[(Database)]
    end

    subgraph During[During Deploy]
        LB2[Load Balancer] --> GREEN2["Green Stack (Active) v1.5.3"]
        LB2 -.->|0% traffic| BLUE["Blue Stack (Standby) v1.6.0"]
        GREEN2 --> DB2[(Database)]
        BLUE --> DB2
    end

    subgraph After[After Deploy]
        LB3[Load Balancer] --> BLUE3["Blue Stack (Active) v1.6.0"]
        LB3 -.->|0% traffic| GREEN3["Green Stack (Standby) v1.5.3"]
        BLUE3 --> DB3[(Database)]
    end
```

**Implementation script:**

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh
set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <environment> <tag>}"
TAG="${2:?Usage: $0 <environment> <tag>}"
REGISTRY="ghcr.io/aegis-marketing-cloud"
STACK_PREFIX="amc-${ENVIRONMENT}"

echo "🔵 Starting blue-green deployment to ${ENVIRONMENT} with tag ${TAG}"

# Determine which stack is active
ACTIVE_STACK=$(docker stack ls --format '{{.Name}}' | grep "${STACK_PREFIX}-" | head -1)
if [[ "$ACTIVE_STACK" == *"blue"* ]]; then
  OLD_COLOR="blue"
  NEW_COLOR="green"
else
  OLD_COLOR="green"
  NEW_COLOR="blue"
fi

echo "  Active stack: ${OLD_COLOR}"
echo "  Deploying to: ${NEW_COLOR}"

export TAG

# Deploy the new stack
docker stack deploy \
  -c deployment/docker-stack.yml \
  -c "deployment/docker-stack.${ENVIRONMENT}.yml" \
  "${STACK_PREFIX}-${NEW_COLOR}"

# Wait for stack to stabilize
echo "⏳ Waiting for ${NEW_COLOR} stack to become healthy..."
sleep 60

# Run smoke tests against the new stack
echo "🧪 Running smoke tests against ${NEW_COLOR}..."
if ! ./scripts/smoke-test.sh "http://${STACK_PREFIX}-${NEW_COLOR}:8000"; then
  echo "❌ Smoke tests failed. Rolling back..."
  docker stack rm "${STACK_PREFIX}-${NEW_COLOR}"
  exit 1
fi

# Swap traffic
echo "🔄 Swapping traffic from ${OLD_COLOR} to ${NEW_COLOR}..."
./scripts/swap-traffic.sh "${ENVIRONMENT}" "${OLD_COLOR}" "${NEW_COLOR}"

# Observation period
echo "👀 Observation period: 5 minutes..."
sleep 300

# Check for errors in the observation period
if ./scripts/check-errors.sh "${ENVIRONMENT}" 5; then
  echo "✅ Deployment successful! Scaling down ${OLD_COLOR}..."
  docker stack rm "${STACK_PREFIX}-${OLD_COLOR}"
  echo "✅ Done! ${NEW_COLOR} is now active."
else
  echo "❌ Errors detected during observation. Rolling back..."
  ./scripts/swap-traffic.sh "${ENVIRONMENT}" "${NEW_COLOR}" "${OLD_COLOR}"
  docker stack rm "${STACK_PREFIX}-${NEW_COLOR}"
  exit 1
fi
```

### 3.10 Rollback Procedure

**Instant rollback** (within 5 minutes of deploy):

```bash
# scripts/rollback.sh
#!/bin/bash
set -euo pipefail

ENVIRONMENT="${1:?Usage: $0 <environment>}"

echo "🔄 Initiating rollback for ${ENVIRONMENT}..."

# Determine active and standby stacks
ACTIVE_STACK=$(docker stack ls --format '{{.Name}}' | grep "amc-${ENVIRONMENT}-" | head -1)
if [[ "$ACTIVE_STACK" == *"blue"* ]]; then
  NEW_COLOR="blue"
  OLD_COLOR="green"
else
  NEW_COLOR="green"
  OLD_COLOR="blue"
fi

echo "  Current active: ${NEW_COLOR}"
echo "  Restoring to: ${OLD_COLOR}"

# Swap traffic back to old stack
./scripts/swap-traffic.sh "${ENVIRONMENT}" "${NEW_COLOR}" "${OLD_COLOR}"

# Scale down the problematic stack
docker stack rm "amc-${ENVIRONMENT}-${NEW_COLOR}"

echo "✅ Rollback complete."
```

**Redeploy rollback** (after 5 minutes):

1. Identify the previous working image tag from the deployment history
2. Tag it as `latest` and push
3. Trigger a new deployment pipeline with the old tag

### 3.11 Migration Automation (Alembic)

Migrations run as part of the deploy step, not at application startup:

```yaml
# CI/CD deploy step: Alembic migration
- name: Run database migrations
  run: |
    docker run --rm \
      -e DATABASE_URL=postgresql://amc:***@pgbouncer:6432/amc \
      ghcr.io/aegis-marketing-cloud/api-gateway:${TAG} \
      alembic upgrade head
```

**Migration safety:** All migrations follow the expand-contract pattern (see §6.7).

---

## 4. Docker Strategy

### 4.1 Base Images

| Service | Base Image | Rationale |
|---------|-----------|-----------|
| Python services | `python:3.12-slim` | Small footprint (120 MB), security-focused |
| Frontend (build) | `node:20-alpine` | Minimal build environment |
| Frontend (runtime) | `nginx:alpine` | Static file serving, tiny (23 MB) |
| Workers / Background | `python:3.12-slim` | Consistent base across Python services |

### 4.2 Multi-Stage Build Examples

(Dockerfiles as shown in §3.5 above)

### 4.3 Docker Compose Override Files

(Refer to §2 for complete dev compose; production Swarm stacks in §5)

### 4.4 Healthcheck Configurations per Service

| Service | Endpoint | Interval | Timeout | Start Period | Retries |
|---------|----------|----------|---------|-------------|---------|
| `api-gateway` | `GET /health` | 15s | 5s | 30s | 3 |
| `monolith` | `GET /health` | 15s | 5s | 30s | 3 |
| `auth-service` | `GET /health` | 15s | 5s | 20s | 3 |
| `frontend` | `GET /api/health` | 15s | 5s | 10s | 3 |
| `postgres-primary` | `pg_isready -U amc` | 5s | 3s | 30s | 5 |
| `redis-*` | `redis-cli ping` | 5s | 3s | 10s | 5 |
| `rabbitmq` | `rabbitmq-diagnostics ping` | 10s | 10s | 30s | 5 |
| `minio` | `GET /minio/health/live` | 15s | 5s | 15s | 3 |
| `qdrant` | `GET /health` | 15s | 5s | 30s | 3 |
| `n8n` | `GET /healthz` | 15s | 5s | 30s | 3 |
| `prometheus` | `GET /-/healthy` | 15s | 5s | 15s | 3 |
| `grafana` | `GET /api/health` | 15s | 5s | 15s | 3 |
| `loki` | `GET /ready` | 15s | 5s | 15s | 3 |
| `ollama` | `GET /api/tags` | 30s | 10s | 120s | 10 |

### 4.5 Network Topology

```mermaid
flowchart TB
    subgraph External[External]
        INTERNET[Internet]
        CDN[CDN / Cloudflare]
    end

    subgraph Public[Public Network]
        LB[Load Balancer<br/>Traefik/ALB]
    end

    subgraph Frontend[Frontend Network]
        FE[Frontend Nginx]
        API[API Gateway]
    end

    subgraph Service[Service Network - Internal]
        MONO[Modular Monolith]
        AUTH[Auth Service]
        BILL[Billing Service]
        NOTIF[Notification Service]
        MEDIA[Media Service]
        AI_ORCH[AI Orchestrator]
        AI_AGENT[AI Agent Runtime]
        AI_MEM[AI Memory Service]
        ANAL[Analytics Service]
        ADMIN[Admin Service]
        MARKET[Marketplace Service]
        WEBHOOK[Webhook Service]
        N8N[n8n Workflow Engine]
    end

    subgraph Data[Data Network - Restricted]
        PG[PostgreSQL Cluster]
        PGB[PgBouncer]
        REDIS_CACHE[Redis Cache]
        REDIS_SESS[Redis Sessions]
        REDIS_QUEUE[Redis Queue]
        QDRANT[Qdrant Vector DB]
        MINIO[MinIO Object Store]
        RABBIT[RabbitMQ]
    end

    subgraph AI_GPU[GPU Network]
        OLLAMA[Ollama]
        NIM[NIM Inference]
    end

    subgraph Monitoring[Monitoring Network]
        PROM[Prometheus]
        GRAF[Grafana]
        LOKI[Loki]
        PROMTAIL[Promtail]
        TEMPO[Tempo]
    end

    INTERNET --> CDN
    CDN --> LB
    LB --> FE
    LB --> API
    
    FE --> API
    API --> AUTH
    API --> MONO
    API --> BILL
    API --> NOTIF
    API --> MEDIA
    API --> AI_ORCH
    
    MONO --> PGB
    MONO --> REDIS_CACHE
    MONO --> RABBIT
    AI_ORCH --> QDRANT
    AI_ORCH --> OLLAMA
    AI_ORCH --> NIM
    AI_AGENT --> AI_MEM
    AI_MEM --> QDRANT
    MEDIA --> MINIO
    ANAL --> PGB
    ANAL --> REDIS_CACHE
    N8N --> RABBIT
    
    PGB --> PG
    
    PROM --> API
    PROM --> MONO
    PROM --> PGB
    PROM --> REDIS_CACHE
    PROM --> RABBIT
    PROM --> QDRANT
    PROM --> MINIO
    PROM --> N8N
    
    PROMTAIL -->|logs| LOKI
    LOKI --> GRAF
    PROM --> GRAF
    TEMPO --> GRAF

    classDef public fill:#e1f5fe,stroke:#01579b
    classDef frontend fill:#f3e5f5,stroke:#7b1fa2
    classDef service fill:#e8f5e9,stroke:#2e7d32
    classDef data fill:#fff3e0,stroke:#e65100
    classDef gpu fill:#fce4ec,stroke:#c62828
    classDef monitor fill:#e0f7fa,stroke:#00695c
    classDef external fill:#f5f5f5,stroke:#616161

    class LB public
    class FE,API frontend
    class MONO,AUTH,BILL,NOTIF,MEDIA,AI_ORCH,AI_AGENT,AI_MEM,ANAL,ADMIN,MARKET,WEBHOOK,N8N service
    class PG,PGB,REDIS_CACHE,REDIS_SESS,REDIS_QUEUE,QDRANT,MINIO,RABBIT data
    class OLLAMA,NIM gpu
    class PROM,GRAF,LOKI,PROMTAIL,TEMPO monitor
    class INTERNET,CDN external
```

**Network segmentation rules:**

| Network | Services | Ingress | Egress |
|---------|----------|---------|--------|
| **Public** | Load balancer, CDN | Internet (443) | Frontend network |
| **Frontend** | Nginx, API Gateway | LB (443) | Service network |
| **Service** | All application services | Frontend network only | Data network, GPU network |
| **Data** | Databases, cache, queues | Service network only | None (no egress to internet) |
| **GPU** | AI inference servers | Service network only | None |
| **Monitoring** | Prometheus, Grafana, etc. | Service network (scrape), VPN (admin) | Internet (alert notifications) |

---

## 5. Production Deployment Architecture

### 5.1 Target: Docker Swarm (v1), Kubernetes (v2+)

**Phase 1 (Year 1): Docker Swarm** — Low operational overhead, built into Docker Engine.

**Phase 2 (Year 2–3): Kubernetes (K3s)** — Required for HPA, richer scheduling, service mesh, multi-region.

```yaml
# deployment/docker-stack.yml — Swarm stack definition
version: "3.9"

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"

services:
  api-gateway:
    image: ${REGISTRY:-ghcr.io/aegis-marketing-cloud}/api-gateway:${TAG:-latest}
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
        failure_action: rollback
        monitor: 60s
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
        window: 120s
      placement:
        constraints:
          - node.labels.type == stateless
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.api.rule=Host(`api.amccloud.com`) && PathPrefix(`/api`)"
        - "traefik.http.services.api.loadbalancer.server.port=8000"
        - "traefik.http.routers.api.entrypoints=websecure"
        - "traefik.http.routers.api.tls.certresolver=letsencrypt"
    networks:
      - frontend
      - service
    logging: *default-logging

  monolith:
    image: ${REGISTRY:-ghcr.io/aegis-marketing-cloud}/monolith:${TAG:-latest}
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      placement:
        constraints:
          - node.labels.type == stateless
    networks:
      - service
      - data
    logging: *default-logging

  # ... (all other services follow same pattern)

  traefik:
    image: traefik:v3.0
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == manager
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - traefik-data:/data
    command:
      - "--providers.docker=true"
      - "--providers.docker.swarmMode=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=ops@amccloud.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/data/acme.json"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
    networks:
      - frontend

networks:
  frontend:
    driver: overlay
    attachable: true
  service:
    driver: overlay
    internal: true
  data:
    driver: overlay
    internal: true

volumes:
  pg-data:
    driver: local
  traefik-data:
    driver: local
```

### 5.2 Node Types

| Node Label | Type | Services | CPU | Memory | Storage |
|------------|------|----------|-----|--------|---------|
| `type=control-plane` | Manager/Control | Traefik, Swarm management, monitoring | 4 vCPU | 8 GB | 100 GB |
| `type=stateless` | Worker | API gateway, monolith, auth, billing, notifications, n8n, frontend | 16 vCPU | 64 GB | 200 GB |
| `type=stateful` | Worker (data) | PostgreSQL, Redis, Qdrant, MinIO, RabbitMQ | 32 vCPU | 128 GB | 4 TB NVMe |
| `type=gpu` | Worker (AI) | NIM, Ollama, AI inference | 32 vCPU | 256 GB | 2 TB + A100/H100 |

### 5.3 Scaling Policies

```yaml
# Horizontal Pod Autoscaling (Kubernetes — Phase 2)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: amc_http_requests_per_second
        target:
          type: AverageValue
          averageValue: 1000
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 2
          periodSeconds: 120
```

### 5.4 Rolling Update Strategy

```yaml
update_config:
  parallelism: 1
  delay: 10s
  order: start-first
  failure_action: rollback
  monitor: 60s
  max_failure_ratio: 0.1
```

### 5.5 TLS Certificate Management

- **Staging/Dev:** Let's Encrypt via Traefik `acme.json`
- **Production:** EV certificate from commercial CA, stored as Docker secrets

### 5.6 DNS Architecture (White-Label)

```mermaid
flowchart LR
    ROOT[app.amccloud.com] --> CNAME[*.amccloud.com]
    ROOT --> TENANT_CNAME[*.customers.com]
    CNAME --> CF[Cloudflare Proxy]
    CF --> LB[Traefik Ingress]
    LB --> API[api-gateway]
    API --> TENANT_RESOLVE[Tenant resolution via X-Tenant-ID]
```

---

## 6. Database Operations

### 6.1 PostgreSQL Cluster (Primary + Read Replicas)

```ini
# deployment/postgres/postgresql.conf
listen_addresses = '*'
max_connections = 500
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 64MB
maintenance_work_mem = 1GB
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
wal_keep_size = 1024
hot_standby = on
hot_standby_feedback = on
random_page_cost = 1.1       # SSD optimization
effective_io_concurrency = 200
default_statistics_target = 500
track_io_timing = on
pg_stat_statements.track = all
```

### 6.2 PgBouncer Connection Pooling

```ini
[databases]
amc = host=postgres-primary port=5432 dbname=amc
amc_read = host=postgres-replica port=5432 dbname=amc

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
pool_mode = transaction
default_pool_size = 50
max_client_conn = 1000
reserve_pool_size = 10
reserve_pool_timeout = 5.0
server_idle_timeout = 300
query_timeout = 30
```

### 6.3 Automated Backups (pgBackRest)

```ini
[amc]
pg1-path=/var/lib/postgresql/data

[global]
repo1-type=s3
repo1-s3-bucket=amc-backups
repo1-s3-region=us-east-1
repo1-retention-full=30
repo1-retention-diff=14
repo1-retention-archive=60
compress-type=zst
compress-level=6
```

### 6.4 Backup Retention Policy

| Backup Type | Frequency | Retention |
|------------|-----------|-----------|
| WAL archive | Every 5 min | 60 days |
| Full backup | Daily | 30 days |
| Differential | Weekly (Sat) | 14 days |
| Monthly | 1st of month | 12 months |
| Yearly | Jan 1 | 7 years |

### 6.5 Point-in-Time Recovery (PITR)

```bash
# scripts/pitr-restore.sh
RESTORE_TARGET="${1}"

# Restore full backup with recovery target
pgbackrest --stanza=amc --type=full restore \
  --db-path=/tmp/pg_restore \
  --target-action=promote \
  --target-time="${RESTORE_TARGET}"

# Configure recovery
cat > /tmp/pg_restore/recovery.conf <<EOF
recovery_target_time = '${RESTORE_TARGET}'
recovery_target_action = 'promote'
restore_command = 'pgbackrest --stanza=amc archive-get %f %p'
EOF

# Start and verify
pg_ctl -D /tmp/pg_restore start
```

### 6.6 Read Replica Setup

Analytics service reads from the replica via connection string `DATABASE_URL_READ`:

```python
engines = {
    "write": create_async_engine(DATABASE_URL, pool_size=10),
    "read": create_async_engine(DATABASE_URL_READ, pool_size=20),
}

def get_engine(read_only=False):
    return engines["read" if read_only else "write"]
```

### 6.7 Migration Safety (Expand-Contract)

```mermaid
flowchart LR
    A1[Add nullable column] --> A2[Deploy app writing to both]
    A2 --> A3[Backfill old rows]
    A3 --> A4[Add NOT NULL]
    A4 --> B1[Read from new, stop reading old]
    B1 --> B2[Deploy app using only new]
    B2 --> C1[Drop old column]
    C1 --> C2[VACUUM FULL]
```

---

## 7. Redis Operations

### 7.1 Topology

- **Phase 1:** Redis Sentinel (3 nodes) — automatic failover
- **Phase 2:** Redis Cluster — sharding for data > 50 GB

### 7.2 Persistence Configuration

| Instance | AOF | Appendfsync | Max Memory | Eviction Policy |
|----------|-----|-------------|------------|-----------------|
| `redis-cache` | Yes | everysec | 2 GB | `allkeys-lru` |
| `redis-sessions` | Yes | always | 1 GB | `noeviction` |
| `redis-queue` | Yes | everysec | 4 GB | `noeviction` |

### 7.3 Backup/Restore

```bash
# Daily RDB backup
redis-cli -h redis-cache save
cp /data/redis/dump.rdb /backups/redis-cache-$(date +%Y%m%d).rdb
aws s3 cp /backups/redis-cache-*.rdb s3://amc-backups/redis/cache/
```

---

## 8. Qdrant Operations

### 8.1 Cluster Configuration

```yaml
cluster:
  enabled: true
  p2p:
    port: 6335
  consensus:
    tick_period_ms: 100
    
storage:
  optimizers:
    default_segment_number: 5
    indexing_threshold: 50000
  performance:
    max_search_threads: 8
    hnsw:
      m: 16
      ef_construct: 200
```

### 8.2 Sharding and Replication

```python
COLLECTION_CONFIG = {
    "shard_number": 4,
    "replication_factor": 2,
    "write_consistency_factor": 1,
    "on_disk_payload": True,
    "hnsw_config": {
        "m": 16,
        "ef_construct": 200,
        "max_indexing_threads": 4,
    },
}
```

### 8.3 Snapshot-Based Backups

```bash
# Create snapshot via API
curl -X POST "http://qdrant:6333/collections/{name}/snapshots"

# Download and upload to S3
curl -s "http://qdrant:6333/collections/{name}/snapshots/{snapshot}" \
  | aws s3 cp - "s3://amc-backups/qdrant/{name}/{date}.snapshot"
```

---

## 9. MinIO Operations

### 9.1 Distributed Mode

```yaml
command: server --console-address ":9001" http://minio{1...4}/data{1...4}
environment:
  MINIO_STORAGE_CLASS_STANDARD: EC:4
```

### 9.2 Bucket Policies (Per-Tenant)

Each tenant gets an isolated bucket with IAM-style policies:

```bash
mc mb amc/tenant-${TENANT_ID}
mc policy set-json bucket-policy.json amc/tenant-${TENANT_ID}
```

### 9.3 Lifecycle Policies

```yaml
rules:
  - id: expire-exports
    filter: { prefix: exports/temp/ }
    expiration: { days: 30 }
  - id: transition-uploads
    filter: { prefix: uploads/ }
    transitions: [{ days: 90, storage_class: GLACIER }]
```

---

## 10. RabbitMQ Operations

### 10.1 Cluster

```yaml
rabbitmq.conf:
  cluster_formation.peer_discovery_backend = rabbit_peer_discovery_classic_config
  cluster_formation.classic_config.nodes.1 = rabbit@rabbitmq1
  vm_memory_high_watermark.relative = 0.7
  disk_free_limit.absolute = 5GB
```

### 10.2 Queue Topology

Queues defined per domain: `amc.email.*`, `amc.sms.*`, `amc.webhook.*`, `amc.media.*`, `amc.ai.*`, `amc.analytics.*`. Each with a dedicated dead letter queue.

### 10.3 Dead Letter Exchange

All primary queues route to `amc.dlx` (fanout) → DLQ per domain → manual review or re-queue.

### 10.4 Backup

```bash
curl -s -u user:pass "http://rabbitmq:15672/api/definitions" \
  | jq '.' > definitions-$(date +%Y%m%d).json
aws s3 cp definitions-*.json s3://amc-backups/rabbitmq/
```

---

## 11. Monitoring Stack (Prometheus + Grafana + Loki)

### 11.1 Monitoring Architecture

```mermaid
flowchart TB
    subgraph Services[Application Services]
        API[API Gateway]
        MONO[Modular Monolith]
        AI[AI Services]
        N8N[n8n]
        DB[PostgreSQL]
        REDIS[Redis]
        RABBIT[RabbitMQ]
        QDRANT[Qdrant]
        MINIO[MinIO]
    end

    subgraph Metrics[Metrics Pipeline]
        PROM[Prometheus Server]
        ALERT[Alertmanager]
    end

    subgraph Logs[Log Pipeline]
        PROMTAIL[Promtail]
        LOKI[Loki]
    end

    subgraph Traces[Trace Pipeline]
        OTEL[OpenTelemetry]
        TEMPO[Tempo]
    end

    subgraph Viz[Visualization]
        GRAF[Grafana]
    end

    subgraph Notify[Notifications]
        SLACK[Slack]
        PAGER[PagerDuty]
        EMAIL[Email]
    end

    Services -->|/metrics| PROM
    Services -->|stdout| PROMTAIL
    Services -->|OTLP| OTEL
    DB -->|exporter| PROM
    REDIS -->|exporter| PROM
    RABBIT -->|exporter| PROM
    QDRANT -->|/metrics| PROM
    MINIO -->|/metrics| PROM
    PROMTAIL --> LOKI
    OTEL --> TEMPO
    PROM --> GRAF
    LOKI --> GRAF
    TEMPO --> GRAF
    PROM --> ALERT
    ALERT --> GRAF
    GRAF --> SLACK
    GRAF --> PAGER
    GRAF --> EMAIL
```

### 11.2 Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert-rules.yml"

scrape_configs:
  - job_name: 'api-gateway'
    metrics_path: /metrics
    static_configs:
      - targets: ['api-gateway:8000']
  
  - job_name: 'monolith'
    static_configs:
      - targets: ['monolith:8001']
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets:
          - 'redis-cache:9121'
          - 'redis-sessions:9121'
          - 'redis-queue:9121'
  
  - job_name: 'rabbitmq'
    metrics_path: /metrics
    static_configs:
      - targets: ['rabbitmq:15692']
  
  - job_name: 'qdrant'
    metrics_path: /metrics
    static_configs:
      - targets: ['qdrant:6333']
  
  - job_name: 'minio'
    metrics_path: /minio/v2/metrics/cluster
    static_configs:
      - targets: ['minio:9000']

storage:
  tsdb:
    retention:
      time: 30d
      size: 50GB
```

### 11.3 Alerting Rules by Severity

**Critical** (PagerDuty):
- `ServiceDown` — service `up == 0` for 1m
- `HighErrorRate` — 5xx rate > 5%
- `DatabaseDown` — `pg_up == 0`
- `DatabaseConnectionsExhausted` — active > 80
- `DiskSpaceCritical` — < 10% free on data mount

**Warning** (Slack):
- `HighErrorRateWarning` — 5xx rate > 1% for 10m
- `HighLatency` — P99 > 2s
- `CacheHitRatioDrop` — hit ratio < 0.7
- `AICostAnomaly` — cost > $50/hr
- `QueueBacklogWarning` — > 10K messages
- `CertificateExpiry` — < 7 days

**Info** (Slack digest):
- `NewDeployment`, `BackupCompleted`, `LowTrafficPeriod`

### 11.4 Grafana Dashboards

1. **Service Health Dashboard** — Uptime, error rate, latency P50/P95/P99, active DB connections, Redis hit ratio, queue depths
2. **Business Metrics Dashboard** — Active workspaces, campaigns dispatched, contacts processed, AI queries, signups, MRR
3. **AI Operations Dashboard** — Inference requests by provider, latency, cost, agent success rate, token usage, GPU utilization
4. **Database Performance Dashboard** — Active connections, QPS, query latency, cache hit ratio, replication lag, slow queries
5. **Infrastructure Overview Dashboard** — Node health, CPU/memory/disk utilization, network traffic
6. **Cost Dashboard** — Monthly infrastructure cost, AI inference cost by model, cost by service/tenant tier

### 11.5 Loki Log Aggregation

```yaml
ingester:
  chunk_idle_period: 15m
  max_chunk_age: 1h

storage_config:
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 2160h  # 90 days
  max_query_length: 721h   # 30d
```

### 11.6 Promtail Configuration

```yaml
scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    pipeline_stages:
      - docker: {}
      - json:
          expressions:
            level: level
            service: service
            trace_id: trace_id
      - labels:
          level:
          service:
```

### 11.7 Custom Metric Instrumentation

```python
# lib/metrics.py
HTTP_REQUESTS_TOTAL = Counter("amc_http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status", "tenant_tier"])
HTTP_REQUEST_DURATION = Histogram("amc_http_request_duration_seconds", "HTTP latency",
    ["method", "endpoint"], buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10])
CAMPAIGNS_DISPATCHED = Counter("amc_campaigns_dispatched_total", "Campaigns dispatched",
    ["channel", "status", "tenant_tier"])
AI_INFERENCE_DURATION = Histogram("amc_ai_inference_duration_seconds", "AI inference latency",
    ["model", "provider", "task_type"])
AI_INFERENCE_COST = Counter("amc_ai_inference_cost_total_usd", "AI inference cost",
    ["model", "provider", "tenant_tier"])
```

---

## 12. Logging Strategy

### 12.1 Structured JSON Logging

**Python (structlog):**

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger("amc.api-gateway")
logger.info("campaign_launched", campaign_id="camp-123", duration_ms=3420,
            trace_id=current_trace_id())
```

**Node.js (Pino):**

```javascript
const pino = require('pino');
const logger = pino({
  name: process.env.SERVICE_NAME || 'frontend',
  level: process.env.LOG_LEVEL || 'info',
  formatters: { level: (label) => ({ level: label }) },
  redact: { paths: ['req.headers.authorization', 'password'], censor: '***' },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

### 12.2 Correlation IDs

W3C `traceparent` header propagation across all service boundaries via OpenTelemetry.

### 12.3 Log Levels per Environment

| Environment | Default Level | Debug | Audit |
|-------------|--------------|-------|-------|
| local | DEBUG | All | Disabled |
| dev | INFO | On request | Enabled |
| staging | INFO | On request | Enabled |
| production | WARNING | Disabled | Enabled (immutable) |

### 12.4 Retention Policies

- Hot (Loki SSD): 30 days
- Warm (S3): 90 days
- Cold (S3 Glacier): 1 year

### 12.5 Audit Log Immutability

Audit logs use a hash chain with HMAC signatures:

```python
entry["prev_hash"] = last_hash
entry["hash"] = sha256(json.dumps(entry, sort_keys=True))
entry["signature"] = hmac.new(key, entry_hash_input, sha256).hexdigest()
```

---

## 13. Backup Strategy

### 13.1 Backup Architecture

```mermaid
flowchart TB
    PG[PostgreSQL Primary] --> WAL[WAL Archiver<br/>Every 5 min]
    PG --> FULL[pgBackRest Daily Full]
    WAL --> STORE[(Backup Store S3)]
    FULL --> STORE
    QDRANT[Qdrant] --> SNAPSHOT[Daily Snapshot]
    SNAPSHOT --> STORE
    MINIO[MinIO Primary] --> REPL[Cross-Region Replication<br/>Real-time]
    REDIS[Redis] --> RDB[Daily RDB Snapshot]
    RDB --> STORE
    RABBIT[RabbitMQ] --> DEF[Definitions Export]
    DEF --> STORE
    STORE --> VERIFY[Monthly Restore Drill]
```

### 13.2 PostgreSQL: Hourly WAL + Daily Full

```
0 2 * * * root pgbackrest --stanza=amc --type=full backup
30 6 * * * root pgbackrest --stanza=amc check
0 3 * * 6 root pgbackrest --stanza=amc --type=diff backup
```

### 13.3 Qdrant: Daily Snapshot

```bash
curl -X POST "http://qdrant:6333/collections/{name}/snapshots"
curl -s "http://qdrant:6333/collections/{name}/snapshots/{snap}" \
  | aws s3 cp - "s3://amc-backups/qdrant/{name}/$(date +%Y%m%d).snapshot"
```

### 13.4 MinIO: Cross-Region Replication

```bash
mc replicate add source/bucket \
  --remote-bucket bucket \
  --remote-endpoint https://s3-dr-region.amazonaws.com \
  --replicate "delete,delete-marker,existing-objects"
```

### 13.5 Redis: Daily RDB Snapshot

```bash
redis-cli -h redis-cache save
cp /data/redis/dump.rdb /backups/redis-cache-$(date +%Y%m%d).rdb
gzip /backups/redis-cache-*.rdb
aws s3 cp /backups/redis-cache-*.rdb.gz s3://amc-backups/redis/cache/
```

### 13.6 RabbitMQ: Definitions Export

```bash
curl -s -u user:pass "http://rabbitmq:15672/api/definitions" | jq '.' \
  > definitions-$(date +%Y%m%d).json
aws s3 cp definitions-*.json s3://amc-backups/rabbitmq/
```

### 13.7 Backup Retention Summary

| Type | Daily | Weekly | Monthly | Yearly |
|------|-------|--------|---------|--------|
| PostgreSQL | 30 days | 12 weeks | 12 months | 7 years |
| Qdrant | 30 days | 12 weeks | 12 months | — |
| Redis RDB | 30 days | 12 weeks | — | — |
| RabbitMQ defs | 30 days | — | — | — |
| MinIO replication | Real-time | Real-time | Real-time | Real-time |

### 13.8 Monthly Restore Drill

A full environment is provisioned and all backups are restored end-to-end, followed by smoke tests.

---

## 14. Disaster Recovery

### 14.1 RTO and RPO Targets

| Component | RTO | RPO |
|-----------|-----|-----|
| Application (stateless) | 5 minutes | N/A |
| Application (full stack) | 15 minutes | N/A |
| PostgreSQL | 1 hour | 5 minutes (WAL) |
| Qdrant | 2 hours | 24 hours |
| Redis (cache) | 15 minutes | 0 (rebuildable) |
| Redis (sessions/queue) | 15 minutes | 5 minutes |
| MinIO | 1 hour | Real-time (replication) |
| RabbitMQ | 30 minutes | 5 minutes |
| **Full platform** | **4 hours** | **5 minutes** |

### 14.2 DR Scenarios

#### Single Service Failure
Health check fails → orchestrator stops container → starts new container → added to LB pool → if > 3 restarts/min → PagerDuty alert.

#### Node Failure
Control plane detects heartbeat timeout (30s) → tasks rescheduled to healthy nodes → stateful services require manual recovery of data volumes.

#### AZ Failure
- Detect failure via cloud provider API or Prometheus `up == 0`
- Promote replica to primary if PostgreSQL is impacted
- Reschedule stateless workloads across remaining AZs

#### Full Region Failure

```mermaid
flowchart TB
    subgraph Normal[Normal]
        DNS[DNS: app.amccloud.com] --> PROD[Production Region]
        PROD -.->|Async Replication| DR[DR Region]
    end
    subgraph Failover[Failover]
        DNS2[DNS: switched] --> DR2[DR Region Promoted]
    end
```

### 14.3 DR Runbook (Summary)

1. Assess region health
2. Verify DR environment
3. Promote DR PostgreSQL (pgbackrest restore --target-action=promote)
4. Update PgBouncer config
5. Deploy application stack to DR
6. Wait for health checks
7. Switch DNS (Route53 CNAME update, TTL 60s)
8. Run end-to-end smoke tests
9. Notify team
10. Document incident

### 14.4 DR Testing Schedule

| Test | Frequency |
|------|-----------|
| Tabletop exercise | Quarterly |
| Database restore drill | Monthly |
| AZ failover test | Quarterly |
| Full DR drill | Annually |
| Backup integrity check | Daily automated |

---

## 15. Capacity Planning

### 15.1 Year 1 (500 Customers)

| Component | Spec | Count | Monthly Cost |
|-----------|------|-------|-------------|
| Control plane | 4 vCPU, 8 GB | 3 | $450 |
| Stateless workers | 16 vCPU, 64 GB | 3 | $2,400 |
| Stateful workers | 32 vCPU, 128 GB, 4 TB NVMe | 2 | $3,200 |
| GPU workers | 32 vCPU, 256 GB, A100 | 1 | $3,500 |
| Misc (LB, storage, network) | - | - | $450 |
| **Total** | | | **~$10,000/mo** |

### 15.2 Year 3 (8,000 Customers)

| Component | Count | Monthly Cost |
|-----------|-------|-------------|
| Control plane (8 vCPU) | 3 | $1,200 |
| Stateless (32 vCPU, 128 GB) | 8 | $12,800 |
| Stateful (64 vCPU, 256 GB, 8 TB) | 4 | $12,800 |
| GPU (64 vCPU, 2×A100) | 4 | $28,000 |
| Monitoring cluster | 3 | $1,200 |
| Misc | - | $2,900 |
| **Total** | | **~$58,900/mo** |

### 15.3 Year 5 (35,000 Customers)

| Component | Count | Monthly Cost |
|-----------|-------|-------------|
| Stateless (64 vCPU) | 20 | $64,000 |
| Stateful (128 vCPU, 16 TB) | 8 | $51,200 |
| GPU (8×H100) | 8 | $112,000 |
| Multi-region DR | - | $40,000 |
| CDN + misc | - | $24,300 |
| **Total** | | **~$291,500/mo** |

### 15.4 Cost per Tier

| Tier | Revenue | Infra Cost/Mo | AI Cost/Mo | Margin |
|------|---------|---------------|------------|--------|
| Starter ($29) | $29 | $0.50 | $0.20 | 97.6% |
| Growth ($99) | $99 | $2.00 | $1.00 | 97.0% |
| Enterprise ($299) | $299 | $8.00 | $5.00 | 95.7% |
| Enterprise Plus ($999) | $999 | $30.00 | $20.00 | 95.0% |

### 15.5 Auto-Scaling Thresholds

| Service | Min | Max | CPU | Memory | Queue Depth |
|---------|-----|-----|-----|--------|-------------|
| api-gateway | 3 | 20 | 70% | 80% | — |
| monolith | 3 | 15 | 75% | — | 100 |
| ai-orchestrator | 2 | 10 | 70% | — | 50 |
| notification-service | 2 | 10 | — | — | 500 |

### 15.6 Database Sizing

| Metric | Year 1 | Year 3 | Year 5 |
|--------|--------|--------|--------|
| PostgreSQL data | 50 GB | 500 GB | 3 TB |
| Connections | 200 | 500 | 1000 |
| Pool size | 50 | 100 | 200 |
| Redis cache | 10 GB | 50 GB | 200 GB |
| Qdrant vectors | 250M | 16B | 100B |
| Qdrant nodes | 3 | 6 | 12 |

---

## 16. Security Scanning Pipeline

### 16.1 Pipeline Overview

```mermaid
flowchart LR
    subgraph Pre[Pre-Commit]
        GITLEAKS[Gitleaks]
        FORMAT[ruff/prettier]
    end
    subgraph CI[CI]
        SAST[Semgrep/Bandit/ESLint]
        SCA[pip-audit/npm audit/Trivy]
        CONTAINER[Trivy on images]
    end
    subgraph Post[Post-Deploy]
        DAST[OWASP ZAP]
        BENCH[kube-bench]
    end
    Pre --> CI --> Post
```

### 16.2 SAST

```yaml
- name: Semgrep
  uses: returntocorp/semgrep-action@v3
  with:
    config: p/python, p/javascript, p/owasp-top-ten

- name: Bandit
  run: bandit -r backend/ --severity-level high --confidence-level high

- name: ESLint security
  run: npx eslint . --config .eslintrc.security.js
```

### 16.3 SCA

```yaml
- name: pip-audit
  run: pip-audit -r backend/requirements/prod.txt --desc on
- name: npm audit
  run: npm audit --audit-level=high
- name: Trivy filesystem
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: fs
    severity: CRITICAL,HIGH
```

### 16.4 Container Scanning

Every built image is scanned with Trivy. Pipeline blocks on CRITICAL or HIGH vulnerabilities.

### 16.5 DAST

Weekly OWASP ZAP scan against staging environment.

### 16.6 Secret Scanning

GitLeaks runs on every PR using `.gitleaks.toml` with custom AMC API key patterns.

### 16.7 Gate Configuration

| Severity | Action |
|----------|--------|
| CRITICAL | Block pipeline |
| HIGH | Warn, require review |
| LOW/INFO | Report in weekly digest |

---

## 17. Environment Matrix

| Attribute | `local` | `dev` | `staging` | `prod` |
|-----------|---------|-------|-----------|--------|
| **Purpose** | Individual dev | Team integration | Pre-production | Production |
| **DNS** | `localhost` | `dev.amc.dev` | `staging.amc.dev` | `app.amccloud.com` |
| **SSL** | Self-signed | Let's Encrypt | Let's Encrypt | EV / Paid |
| **Data** | Synthetic seed | Anonymized subset | Anonymized copy | Real customer data |
| **Access** | Dev team | Dev team | Internal (all employees) | Restricted (SRE + on-call) |
| **Auth** | Disabled | SSO | SSO + MFA | SSO + MFA + audit |
| **Monitoring** | Minimal | Full | Full + alerting | Full + PagerDuty |
| **Backups** | None | Daily (no retention) | Daily (7 day) | Full retention |
| **Log level** | DEBUG | INFO | INFO | WARNING |
| **Replicas** | 1 | 1 | 2 | 3+ |
| **Secrets** | `.env` (plaintext) | GitHub secrets | Vault | Vault + HSM |
| **Deploy** | `docker compose up` | Auto (develop) | Auto (staging) | Manual approval (main) |
| **Cost** | Dev machine | ~$500/mo | ~$2,000/mo | ~$10,000+/mo |

---

## Appendix A: Quick Reference

### A.1 Common Commands

```bash
# Development
docker compose -f deployment/docker-compose.yml up -d
docker compose exec api-gateway alembic upgrade head
./scripts/seed-dev.sh

# Testing
pytest backend/tests/ -v --cov
docker compose exec api-gateway pytest tests/integration/ -v

# Production
docker stack deploy -c deployment/docker-stack.yml amc-production
./scripts/blue-green-deploy.sh production v1.5.3
./scripts/rollback.sh production

# Monitoring
docker service ls
docker service logs --tail 100 amc-production_api-gateway

# Backups
pgbackrest --stanza=amc --type=full backup
pgbackrest --stanza=amc check

# Disaster Recovery
./runbooks/dr-failover.sh
```

### A.2 Directory Structure

```
amc/
├── .github/workflows/
│   ├── pr-checks.yml, deploy.yml, sast.yml
│   ├── dependency-scan.yml, container-scan.yml
│   ├── dast.yml, secret-scan.yml
├── deployment/
│   ├── docker-compose.yml, docker-stack.yml
│   ├── Dockerfile.* (per service)
│   ├── env/ (local/dev/staging/production)
│   ├── postgres/, redis/, qdrant/, rabbitmq/
│   ├── prometheus/, grafana/, loki/, tempo/, otel/
│   └── traefik/
├── scripts/
│   ├── seed-dev.sh, blue-green-deploy.sh, rollback.sh
│   ├── setup-replica.sh, pitr-restore.sh
│   ├── backup-redis.sh, backup-qdrant.sh, backup-rabbitmq.sh
│   ├── setup-bucket-replication.sh, setup-tenant-domain.sh
│   └── smoke-test.sh, wait-for-health.sh
├── runbooks/
│   ├── dr-failover.sh, dr-diagnose.sh
│   └── dr-monthly-restore-drill.sh
└── k8s/ (Phase 2)
```

---

> **Document History**
>
> | Version | Date | Author | Changes |
> |---------|------|--------|---------|
> | 1.0 | June 2026 | Platform Engineering Team | Initial release |
>
> **Related Documents**
>
> - Volume 4: System Architecture (§11 Deployment, §12 Observability)
> - Volume 10: Security Architecture and Compliance
> - Volume 12: Service Catalog and API Reference
> - Volume 13: Monitoring and Alerting Runbook
