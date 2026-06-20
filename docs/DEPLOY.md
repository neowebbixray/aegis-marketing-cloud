# Aegis Marketing Cloud — Deployment Guide

> **Version:** v1.0.0  
> **Last Updated:** 2026-06-19  
> **Author:** Aegis DevOps Team

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (Development)](#2-quick-start-development)
3. [Production Deployment](#3-production-deployment)
4. [Environment Variable Reference](#4-environment-variable-reference)
5. [Database Migration Steps](#5-database-migration-steps)
6. [Backup and Restore Procedures](#6-backup-and-restore-procedures)
7. [Monitoring and Alerting Setup](#7-monitoring-and-alerting-setup)
8. [Troubleshooting Guide](#8-troubleshooting-guide)

---

## 1. Prerequisites

### Hardware Requirements

| Environment | CPU | RAM | Storage | Notes |
|-------------|-----|-----|---------|-------|
| Development | 2 cores | 4 GB | 20 GB | Docker Desktop or Rancher Desktop |
| Staging | 4 cores | 8 GB | 50 GB | SSD recommended |
| Production (small) | 4 cores | 16 GB | 100 GB | 50 concurrent users |
| Production (medium) | 8 cores | 32 GB | 250 GB | 200 concurrent users |
| Production (large) | 16 cores | 64 GB | 500 GB | 1000+ concurrent users |

### Software Requirements

- **Docker Engine** ≥ 24.0
- **Docker Compose Plugin** ≥ 2.24
- **Git** ≥ 2.40
- **Make** (optional, for Makefile convenience targets)

### Domain & DNS Setup (Production)

| Record | Type | Value | TTL |
|--------|------|-------|-----|
| `app.aegismc.io` | A | `<server-ip>` | 300 |
| `api.aegismc.io` | A | `<server-ip>` | 300 |
| `grafana.aegismc.io` | CNAME | `app.aegismc.io` | 300 |
| `n8n.aegismc.io` | CNAME | `app.aegismc.io` | 300 |

### Required Secrets (Production)

| Secret | Source | Purpose |
|--------|--------|---------|
| `STAGING_SSH_KEY` | Admin-generated | SSH access to staging server |
| `STAGING_API_KEY` | Admin-generated | Integration test auth |
| `PRODUCTION_SSH_KEY` | Admin-generated | SSH access to production server |
| `SLACK_WEBHOOK_URL` | Slack App config | Deployment notifications |
| `GITHUB_TOKEN` | GitHub Actions | Container registry access |
| `SAFETY_API_KEY` | pyup.io | Python vulnerability database |
| `GITLEAKS_LICENSE` | Gitleaks license | Secret scanning |

### Port Reference

| Service | Port | Protocol | Required | Notes |
|---------|------|----------|----------|-------|
| Frontend | 3000 | HTTP | Yes | Next.js app |
| Backend API | 8000 | HTTP | Yes | FastAPI + GraphQL |
| PostgreSQL | 5432 | TCP | Yes | Internal (not exposed) |
| Redis | 6379 | TCP | Yes | Internal (not exposed) |
| MinIO API | 9000 | HTTP | Yes | Object storage API |
| MinIO Console | 9001 | HTTP | Optional | Admin UI |
| RabbitMQ AMQP | 5672 | TCP | Yes | Message broker |
| RabbitMQ Admin | 15672 | HTTP | Optional | Management UI |
| Qdrant gRPC | 6334 | TCP | Yes | Vector DB |
| Qdrant HTTP | 6333 | HTTP | Yes | Vector DB REST |
| n8n | 5678 | HTTP | Yes | Workflow engine |
| Prometheus | 9090 | HTTP | Optional | Metrics |
| Grafana | 3000 | HTTP | Optional | Dashboards |
| Loki | 3100 | HTTP | Optional | Log aggregation |
| Mailpit SMTP | 1025 | TCP | Dev only | Email testing |
| Mailpit UI | 8025 | HTTP | Dev only | Email testing |

---

## 2. Quick Start (Development)

### 2.1 Clone and Configure

```bash
git clone https://github.com/nousresearch/aegis-marketing-cloud.git
cd aegis-marketing-cloud

# Copy environment files
cp .env.example .env
cp src/backend/.env.example src/backend/.env
cp src/frontend/.env.local.example src/frontend/.env.local 2>/dev/null || true
```

### 2.2 Start the Development Stack

```bash
# Using the root docker-compose.yml (development infra)
docker compose up -d

# Or using Makefile convenience targets
make up
```

### 2.3 Run Database Migrations

```bash
docker compose exec backend alembic upgrade head
# Alternative: make migrate
```

### 2.4 Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Frontend | http://localhost:3000 | — |
| Backend API | http://localhost:8000/docs | — |
| MinIO Console | http://localhost:9001 | `aegis_minio` / `aegis_minio_secret` |
| RabbitMQ Admin | http://localhost:15672 | `aegis` / `aegis_rabbit` |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Mailpit | http://localhost:8025 | — |
| n8n | http://localhost:5678 | Configure on first run |

### 2.5 Stop the Stack

```bash
docker compose down
# With volume removal (destroys data):
# docker compose down -v
```

---

## 3. Production Deployment

### 3.1 Server Preparation

```bash
# Install Docker on Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Create deploy user
sudo useradd -r -m -d /opt/aegis -s /bin/bash aegis
sudo usermod -aG docker aegis
```

### 3.2 Clone on Server

```bash
sudo -u aegis git clone https://github.com/nousresearch/aegis-marketing-cloud.git /opt/aegis-marketing-cloud
cd /opt/aegis-marketing-cloud
```

### 3.3 Configure Production Environment

```bash
# Create production .env
cp .env.example .env
# Edit .env with production values
#   - Set ENVIRONMENT=production
#   - Set DEBUG=false
#   - Generate strong SECRET_KEY, ENCRYPTION_KEY, N8N_ENCRYPTION_KEY
#   - Set production database credentials
#   - Configure SMTP for production email relay
#   - Set SENTRY_DSN for error tracking
```

### 3.4 Deploy with Docker Compose (Production File)

```bash
# Use the deployment-specific compose file
docker compose -f deployment/docker-compose.yml up -d

# Run migrations
docker compose -f deployment/docker-compose.yml exec -T backend alembic upgrade head
```

### 3.5 Automated CI/CD Deployment

The included CD pipeline (`.github/workflows/cd.yml`) handles:

1. **Build & Push** — Docker images built and pushed to GHCR
2. **Deploy to Staging** — SSH into staging server, pull images, restart
3. **Integration Tests** — Run against staging environment
4. **Manual Gate** — GitHub Environments approval required for production
5. **Deploy to Production** — SSH into production server, pull, restart, migrate
6. **Notifications** — Slack alerts on success/failure

To configure, set these GitHub secrets:

| Secret | Description |
|--------|-------------|
| `STAGING_SSH_KEY` | Private SSH key for staging server |
| `STAGING_USER` | SSH username for staging |
| `STAGING_HOST` | Staging server hostname/IP |
| `STAGING_API_KEY` | API key for integration tests |
| `PRODUCTION_SSH_KEY` | Private SSH key for production server |
| `PRODUCTION_USER` | SSH username for production |
| `PRODUCTION_HOST` | Production server hostname/IP |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for deploy notifications |

### 3.6 Production Hardening Checklist

- [ ] All default passwords changed (PostgreSQL, Redis, MinIO, RabbitMQ)
- [ ] `SECRET_KEY` generated with `openssl rand -hex 64`
- [ ] `ENCRYPTION_KEY` generated with `openssl rand -hex 32`
- [ ] `N8N_ENCRYPTION_KEY` set to 32+ character random string
- [ ] `DEBUG=false` in production environment
- [ ] `CORS_ORIGINS` restricted to production domain
- [ ] `TRUSTED_HOSTS` set to production domain
- [ ] SSL/TLS termination configured (reverse proxy)
- [ ] Database passwords rotated from defaults
- [ ] MinIO TLS enabled (`MINIO_USE_SSL=true`)
- [ ] PostgreSQL exposed ports restricted (`127.0.0.1:5432:5432`)
- [ ] Regular backup schedule configured
- [ ] Sentry DSN configured for error tracking
- [ ] Prometheus metrics enabled
- [ ] Rate limiting enabled

---

## 4. Environment Variable Reference

All environment variables are organized by category. Variables marked with **\*** are **required**.

### 4.1 Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Aegis Marketing Cloud` | Application display name |
| `ENVIRONMENT`* | `development` | Runtime environment: `development`, `staging`, `production` |
| `DEBUG` | `true` | Enable debug mode (`true`/`false`) |
| `LOG_LEVEL` | `DEBUG` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `SECRET_KEY`* | — | 64+ character random string for cryptographic signing |
| `API_V1_PREFIX` | `/api/v1` | Base path for API v1 endpoints |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Comma-separated allowed CORS origins |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hostnames |

### 4.2 Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL`* | `postgresql+asyncpg://aegis:aegis_secret@localhost:5432/aegis` | Async PostgreSQL connection string |
| `DATABASE_SYNC_URL` | `postgresql://aegis:***@localhost:5432/aegis` | Synchronous PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `20` | Maximum database connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Maximum overflow connections beyond pool size |

### 4.3 Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL`* | `redis://:aegis_redis@localhost:6379/0` | Primary Redis connection (caching, pub/sub) |
| `REDIS_SESSION_URL` | `redis://:aegis_redis@localhost:6379/1` | Session store Redis connection |
| `REDIS_CACHE_URL` | `redis://:aegis_redis@localhost:6379/2` | Application cache Redis connection |

### 4.4 Qdrant (Vector Store)

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server hostname |
| `QDRANT_PORT` | `6333` | Qdrant REST API port |
| `QDRANT_API_KEY` | — | Qdrant API key (empty = no auth) |
| `QDRANT_PREFER_GRPC` | `false` | Prefer gRPC over REST |
| `QDRANT_HTTPS` | `false` | Use HTTPS for Qdrant connection |

### 4.5 MinIO / S3 Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT`* | `localhost:9000` | MinIO server hostname and port |
| `MINIO_ACCESS_KEY` | `aegis_minio` | MinIO access key (username) |
| `MINIO_SECRET_KEY` | `aegis_minio_secret` | MinIO secret key (password) |
| `MINIO_USE_SSL` | `false` | Enable TLS for MinIO connections |
| `MINIO_BUCKET_ASSETS` | `aegis-assets` | Bucket for static assets |
| `MINIO_BUCKET_MEDIA` | `aegis-media` | Bucket for media uploads |
| `MINIO_BUCKET_BACKUPS` | `aegis-backups` | Bucket for backups |

### 4.6 RabbitMQ

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_URL`* | `amqp://aegis:***@localhost:5672/` | RabbitMQ AMQP connection string |
| `RABBITMQ_WORKFLOW_QUEUE` | `amc-workflows` | Queue name for workflow tasks |
| `RABBITMQ_NOTIFICATION_QUEUE` | `amc-notifications` | Queue name for notifications |

### 4.7 Auth / JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ALGORITHM` | `RS256` | JWT signing algorithm (RS256 recommended for production) |
| `JWT_KEY_ID` | `default` | Key identifier for JWKS rotation |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL in days |
| `MFA_ISSUER_NAME` | `Aegis Marketing Cloud` | TOTP issuer name for authenticator apps |

### 4.8 Encryption

| Variable | Default | Description |
|----------|---------|-------------|
| `ENCRYPTION_KEY`* | — | 32-byte hex string for pgcrypto field-level encryption |

### 4.9 SSO / OAuth

| Variable | Default | Description |
|----------|---------|-------------|
| `SSO_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/sso/callback` | OAuth callback URL |
| `GOOGLE_OAUTH_CLIENT_ID` | — | Google OAuth 2.0 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | — | Google OAuth 2.0 client secret |
| `MICROSOFT_OAUTH_CLIENT_ID` | — | Microsoft Entra ID client ID |
| `MICROSOFT_OAUTH_CLIENT_SECRET` | — | Microsoft Entra ID client secret |
| `MICROSOFT_OAUTH_TENANT` | `common` | Microsoft Entra ID tenant (`common`, `organizations`, or tenant ID) |
| `GITHUB_OAUTH_CLIENT_ID` | — | GitHub OAuth App client ID |
| `GITHUB_OAUTH_CLIENT_SECRET` | — | GitHub OAuth App client secret |

### 4.10 SAML

| Variable | Default | Description |
|----------|---------|-------------|
| `SAML_IDP_METADATA_URL` | — | IdP metadata XML URL |
| `SAML_IDP_ENTITY_ID` | — | IdP entity ID (issuer) |
| `SAML_SP_ENTITY_ID` | — | Service provider entity ID |
| `SAML_SP_ACS_URL` | — | Assertion Consumer Service URL |
| `SAML_SP_X509_CERT` | — | SP X.509 certificate (base64) |
| `SAML_SP_PRIVATE_KEY` | — | SP private key (base64) |

### 4.11 Stripe / Billing

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_API_KEY` | — | Stripe secret key (sk_live_*) |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret (whsec_*) |
| `STRIPE_PRICE_ID_FREE` | — | Stripe Price ID for free tier |
| `STRIPE_PRICE_ID_PRO` | — | Stripe Price ID for pro tier |
| `STRIPE_PRICE_ID_ENTERPRISE` | — | Stripe Price ID for enterprise tier |

### 4.12 AI / LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `nvidia-nim` | AI provider: `nvidia-nim`, `openai`, `anthropic`, `ollama` |
| `AI_MODEL` | `meta/llama-3.1-70b-instruct` | Default model identifier |
| `NVIDIA_NIM_API_KEY` | — | NVIDIA NIM API key |
| `NVIDIA_NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM API base URL |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

### 4.13 Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model name |
| `EMBEDDING_ENDPOINT` | — | Custom embedding endpoint URL |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension |
| `EMBEDDING_API_KEY` | — | Embedding service API key |

### 4.14 Knowledge / Chunking

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | `512` | Document chunk size (tokens) |
| `CHUNK_OVERLAP` | `50` | Chunk overlap (tokens) |

### 4.15 Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://:aegis_redis@localhost:6379/0` | Celery message broker URL |

### 4.16 n8n Workflow Engine

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_URL` | `http://localhost:5678` | n8n server URL |
| `N8N_API_KEY` | — | n8n API key for programmatic access |
| `N8N_WEBHOOK_URL` | `http://localhost:5678/webhook` | n8n webhook base URL |

### 4.17 Email / SMTP

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | `localhost` | SMTP server hostname |
| `SMTP_PORT` | `1025` | SMTP server port |
| `SMTP_USER` | — | SMTP authentication username |
| `SMTP_PASSWORD` | — | SMTP authentication password |
| `SMTP_FROM` | `noreply@aegismc.com` | Default sender email address |
| `SMTP_TLS` | `false` | Enable TLS for SMTP |

### 4.18 Monitoring / Error Tracking

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | — | Sentry DSN for error tracking |
| `SENTRY_ENVIRONMENT` | `development` | Sentry environment tag |
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics endpoint |
| `PROMETHEUS_MULTIPROC_DIR` | `/tmp/prometheus` | Prometheus multiprocess temp directory |
| `OTEL_SERVICE_NAME` | `aegis-marketing-cloud` | OpenTelemetry service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | OpenTelemetry collector endpoint |

### 4.19 Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `MEDIA_LIBRARY_ROOT` | `media-library` | Root directory for the media library |
| `UPLOAD_DIR` | `./uploads` | Temporary upload directory |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size in MB |
| `STORAGE_BACKEND` | `local` | Storage backend: `local` or `s3` |

### 4.20 Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Maximum requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |

### 4.21 Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_AI_AGENTS` | `true` | Enable AI agent features |
| `FEATURE_MARKETPLACE` | `false` | Enable plugin marketplace |
| `FEATURE_WHITE_LABEL` | `false` | Enable white-label branding |
| `FEATURE_BILLING_ENABLED` | `false` | Enable Stripe billing integration |

---

## 5. Database Migration Steps

### 5.1 Running Migrations

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Check current migration version
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history
```

### 5.2 Creating New Migrations

```bash
# Auto-generate migration from model changes
docker compose exec backend alembic revision --autogenerate -m "description of changes"

# Manually create an empty migration
docker compose exec backend alembic revision -m "description"
```

### 5.3 Rolling Back Migrations

```bash
# Roll back one step
docker compose exec backend alembic downgrade -1

# Roll back to a specific revision
docker compose exec backend alembic downgrade <revision_id>

# View downgrade targets
docker compose exec backend alembic history
```

### 5.4 Migration Best Practices

1. **Always preview changes**: Review auto-generated migrations before applying
2. **Test on staging first**: Run migrations against staging database before production
3. **Back up before migrating**: Take a database snapshot before production migrations
4. **Use transactions safely**: Alembic wraps migrations in transactions by default
5. **Avoid long-running locks**: For large tables, consider batch processing
6. **Rollback plan**: Always know the downgrade revision before upgrading
7. **Zero-downtime migrations**: For production, use PostgreSQL `CONCURRENTLY` for index creation:

```sql
-- Example: Create index concurrently (manual migration step)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_table_column ON table_name (column);
```

### 5.5 Migration File Locations

```
src/backend/alembic/
├── alembic.ini              # Alembic configuration
├── env.py                   # Environment configuration
├── script.py.mako           # Migration template
└── versions/                # Migration files
    ├── 0001_initial_schema.py
    ├── 0002_rls_and_encryption.py
    ├── 0003_billing_media_webhooks.py
    └── 0004_fulltext_search.py
```

---

## 6. Backup and Restore Procedures

### 6.1 Database Backup

```bash
# Manual PostgreSQL dump
docker compose exec -T postgres pg_dump -U aegis aegis > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose exec -T postgres pg_dump -U aegis aegis | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Custom format (parallel restore capable)
docker compose exec -T postgres pg_dump -U aegis -Fc aegis > backup_$(date +%Y%m%d_%H%M%S).dump
```

### 6.2 Database Restore

```bash
# Restore from plain SQL
cat backup_20260619_120000.sql | docker compose exec -T postgres psql -U aegis -d aegis

# Restore from compressed backup
gunzip -c backup_20260619_120000.sql.gz | docker compose exec -T postgres psql -U aegis -d aegis

# Restore from custom format
docker compose exec -T postgres pg_restore -U aegis -d aegis -Fc < backup_20260619_120000.dump
```

### 6.3 MinIO Backup

```bash
# Using MinIO Client
docker compose exec minio mc alias set local http://localhost:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

# Backup all buckets
for bucket in assets media backups temp; do
  docker compose exec minio mc mirror local/$bucket backup/$bucket/
done

# Or rsync the data volume
docker run --rm -v minio-data:/source -v $(pwd)/backups:/backup alpine tar czf /backup/minio-$(date +%Y%m%d).tar.gz -C /source .
```

### 6.4 Qdrant Backup

```bash
# Use Qdrant snapshot API
curl -X POST 'http://localhost:6333/collections/{collection_name}/snapshots'

# Snapshots are stored in qdrant-snapshots volume
docker run --rm -v qdrant-snapshots:/source -v $(pwd)/backups:/backup alpine tar czf /backup/qdrant-$(date +%Y%m%d).tar.gz -C /source .
```

### 6.5 Redis Backup

Redis append-only file (AOF) is enabled. The AOF file is stored at `/data/appendonly.aof` on the `redis-data` volume.

```bash
# Manual Redis save (creates dump.rdb)
docker compose exec redis redis-cli SAVE

# Backup AOF file
docker run --rm -v redis-data:/source -v $(pwd)/backups:/backup alpine tar czf /backup/redis-$(date +%Y%m%d).tar.gz -C /source .
```

### 6.6 Automated Backup Script

Create a cron job on the host:

```bash
# /etc/cron.d/aegis-backup
0 2 * * * root /opt/aegis-marketing-cloud/scripts/backup.sh
```

Example `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/opt/aegis/backups
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR/{postgres,minio,redis}

# PostgreSQL
cd /opt/aegis-marketing-cloud
docker compose exec -T postgres pg_dump -U aegis -Fc aegis > $BACKUP_DIR/postgres/aegis_$DATE.dump

# MinIO
docker compose exec -T minio mc mirror --overwrite local /tmp/minio-backup

# Redis
docker compose exec -T redis redis-cli SAVE

# Prune old backups
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete
```

### 6.7 Disaster Recovery Plan

| Severity | Scenario | RTO | RPO | Recovery Action |
|----------|----------|-----|-----|-----------------|
| Critical | Database corruption | 1 hour | 1 hour | Restore from latest pg_dump |
| Critical | Full server failure | 4 hours | 1 hour | Provision new server, restore all volumes |
| High | MinIO data loss | 2 hours | 1 day | Restore from MinIO backup |
| Medium | Redis data loss | 30 min | 5 min | Rebuild from AOF or DB re-cache |
| Low | Qdrant data loss | 2 hours | 1 day | Restore from snapshot, re-embed documents |

---

## 7. Monitoring and Alerting Setup

### 7.1 Monitoring Stack Components

| Component | Purpose | Port | Image |
|-----------|---------|------|-------|
| Prometheus | Metrics collection & storage | 9090 | `prom/prometheus:v2.54.0` |
| Grafana | Dashboard visualization | 3000 | `grafana/grafana:11.2.0` |
| Loki | Log aggregation | 3100 | `grafana/loki:3.1.0` |
| Promtail | Log shipping | — | `grafana/promtail:3.1.0` |

### 7.2 Prometheus Configuration

Prometheus config is at `infra/compose/prometheus/prometheus.yml`. It scrapes:

- Backend metrics (`/metrics` endpoint)
- n8n metrics (if enabled)
- Node exporter (if running on host)

Default scrape interval: 15s
Retention: 30 days

### 7.3 Grafana Dashboards

Provisioned dashboards are at `infra/compose/grafana/dashboards/`:

| Dashboard | Description |
|-----------|-------------|
| Aegis — Application Overview | HTTP request rate, latency, error rate |
| Aegis — Database | Connection pool, query duration, transaction rate |
| Aegis — Redis | Cache hit ratio, memory usage, command rate |
| Aegis — RabbitMQ | Queue depth, message rate, consumer count |
| Aegis — MinIO | Bucket size, object count, request rate |
| Aegis — System | CPU, memory, disk, network per container |

### 7.4 Loki Log Aggregation

Loki config is at `infra/compose/loki/loki-config.yml`. Logs are collected from all Docker containers via Promtail.

```bash
# Query logs for a specific service
docker compose logs backend -f

# Via Grafana Explore
# Query: {container_name="amc-backend"} |= "ERROR"
```

### 7.5 Setting Up Alerts

**Prometheus Alertmanager** (add to docker-compose.yml for production):

```yaml
alertmanager:
  image: prom/alertmanager:v0.27.0
  container_name: amc-alertmanager
  volumes:
    - ./infra/compose/prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  ports:
    - "9093:9093"
  command:
    - "--config.file=/etc/alertmanager/alertmanager.yml"
```

**Alert Rules** (`infra/compose/prometheus/alerts.yml`):

```yaml
groups:
  - name: aegis
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High HTTP 5xx error rate ({{ $value | humanizePercentage }})"

      - alert: DatabaseConnectionHigh
        expr: pg_stat_activity_count > 50
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connections exceeded 50"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage > 80%"

      - alert: QueueDepthGrowing
        expr: rabbitmq_queue_messages > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RabbitMQ queue depth > 1000"
```

### 7.6 Sentry Error Tracking

Configure `SENTRY_DSN` in production environment to enable error tracking:

```bash
# Example Sentry DSN
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
SENTRY_ENVIRONMENT=production
```

### 7.7 Health Check Endpoints

| Endpoint | Response | Description |
|----------|----------|-------------|
| `GET /health/live` | `{"status":"ok"}` | Liveness probe (always 200 if server is running) |
| `GET /health/ready` | `{"status":"ok"}` | Readiness probe (checks all service connections) |
| `GET /health` | Full report | Detailed health of all dependent services |

---

## 8. Troubleshooting Guide

### 8.1 Common Issues

#### Issue: Backend won't start — database connection failed

**Symptoms:**
- Backend container exits with `could not translate host name "postgres" to address`
- `psycopg2.OperationalError: connection to server at "postgres" ... failed`

**Solutions:**
1. Verify PostgreSQL is healthy: `docker compose ps postgres`
2. Check PostgreSQL logs: `docker compose logs postgres`
3. Ensure `depends_on` condition is `service_healthy` (not just `service_started`)
4. Verify `DATABASE_URL` has correct credentials

#### Issue: Redis AUTH failed

**Symptoms:**
- `redis.exceptions.AuthenticationError: AUTH failed`
- Worker tasks fail with Redis connection errors

**Solutions:**
1. Check that `REDIS_URL` matches the `--requirepass` in docker-compose.yml
2. Verify Redis is healthy: `docker compose exec redis redis-cli ping`
3. Check Redis logs: `docker compose logs redis`

#### Issue: MinIO bucket not found

**Symptoms:**
- `S3Error: The specified bucket does not exist`
- Uploads fail with 404

**Solutions:**
1. Check the `createbuckets` container ran successfully: `docker compose logs createbuckets`
2. Manually create buckets:
   ```
   docker compose exec minio mc alias set local http://localhost:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
   docker compose exec minio mc mb local/aegis-assets
   ```
3. Verify bucket names match `MINIO_BUCKET_*` env vars

#### Issue: n8n encryption key invalid

**Symptoms:**
- n8n container fails to start with `ENCRYPTION_KEY` related error
- Workflow credentials can't be decrypted

**Solutions:**
1. Set `N8N_ENCRYPTION_KEY` to a 32+ character random string
2. If changing the key, existing encrypted credentials will be lost
3. Back up n8n data before changing: `docker compose exec n8n cp -r /home/node/.n8n /home/node/.n8n-backup`

#### Issue: Port already in use

**Symptoms:**
- `Error starting userland proxy: listen tcp4 0.0.0.0:3000: bind: address already in use`

**Solutions:**
1. Find the conflicting process: `lsof -i :3000`
2. Stop the process or change the host port mapping in docker-compose.yml
3. Or change the compose override to bind to a different host port

#### Issue: Docker build fails

**Symptoms:**
- `ERROR: failed to solve: ...`
- pip install fails in Docker build

**Solutions:**
1. Check Dockerfile syntax
2. Verify `pyproject.toml` exists in build context
3. Clear Docker build cache: `docker buildx prune`
4. For Python dependency issues, try: `docker compose build --no-cache backend`

### 8.2 Docker Diagnostic Commands

```bash
# Check all container statuses
docker compose ps

# View logs for a specific service
docker compose logs backend -f --tail=100

# Inspect a container
docker inspect amc-backend

# Check resource usage
docker stats

# Test network connectivity between containers
docker compose exec backend ping -c 3 postgres

# Check database connection directly
docker compose exec backend python -c "
import psycopg2
conn = psycopg2.connect('postgresql://aegis:aegis_secret@postgres:5432/aegis')
print(conn.execute('SELECT 1').fetchone())
"
```

### 8.3 Recovery Commands

```bash
# Restart a single service
docker compose restart backend

# Rebuild and restart a service
docker compose up -d --build backend

# Force re-create containers
docker compose up -d --force-recreate

# Complete reset (WARNING: destroys all data)
docker compose down -v
docker compose up -d
```

### 8.4 Getting Help

- **GitHub Issues**: https://github.com/nousresearch/aegis-marketing-cloud/issues
- **Documentation**: See `docs/` directory for all 15 volumes
- **Architecture Decisions**: See `docs/volume-4/01-system-architecture.md`

---

> **"Documentation-first is not about writing more — it's about building smarter."**
