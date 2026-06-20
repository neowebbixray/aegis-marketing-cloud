# Aegis Marketing Cloud

> **AI-Native Digital Marketing Operating System**  
> v1.0.0 — Enterprise-grade platform for intelligent marketing automation

[![CI](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/ci.yml/badge.svg)](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/ci.yml)
[![Docker Build](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/docker-ci.yml)
[![Security Scan](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/security.yml/badge.svg)](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/security.yml)
[![CD](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/cd.yml/badge.svg)](https://github.com/nousresearch/aegis-marketing-cloud/actions/workflows/cd.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Architecture Overview

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│   Frontend  │   │   Backend    │   │   Worker    │
│  Next.js 14 │──▶│  FastAPI     │──▶│  Celery     │
│  React 18   │   │  GraphQL     │   │  Async Jobs │
└─────────────┘   └──────┬───────┘   └─────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │PostgreSQL│    │  Redis   │    │  MinIO   │
    │   16     │    │    7     │    │ S3-compat│
    └─────────┘    └──────────┘    └──────────┘
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │  Qdrant │    │ RabbitMQ │    │  n8n     │
    │Vector DB│    │  Broker  │    │Workflows │
    └─────────┘    └──────────┘    └──────────┘
```

## Quick Start

```bash
# Prerequisites: Docker + Docker Compose

# Clone & enter
git clone https://github.com/nousresearch/aegis-marketing-cloud.git
cd aegis-marketing-cloud

# Configure environment
cp .env.example .env

# Windows test runner (optional on Windows CI)
./scripts/run_tests_windows.sh

# Start the full stack
docker compose -f deployment/docker-compose.yml up -d

# Run database migrations
docker compose -f deployment/docker-compose.yml exec backend alembic upgrade head

# Open in browser
open http://localhost:3000

# (Optional) Start Vault for secret management:
# docker compose -f infra/compose/vault/docker-compose.yml up -d
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | `3000` | Next.js 14 application |
| Backend API | `8000` | FastAPI + GraphQL |
| PostgreSQL | `5432` | Primary database |
| Redis | `6379` | Cache & session store |
| RabbitMQ | `5672` / `15672` | Message broker |
| Qdrant | `6333` / `6334` | Vector database |
| MinIO | `9000` / `9001` | S3-compatible storage |
| n8n | `5678` | Workflow automation |
| Prometheus | `9090` | Metrics collection |
| Grafana | `3000` | Monitoring dashboards |
| Loki | `3100` | Log aggregation |
| Mailpit | `1025` / `8025` | Dev email catcher |

## Documentation

Full documentation is available in the [`docs/`](./docs/) directory, organized into 15 volumes covering business requirements through operations.

- [Deployment Guide](./docs/DEPLOY.md)
- [System Architecture](./docs/volume-4/01-system-architecture.md)
- [API Reference](./docs/volume-6/01-api-overview.md)
- [Security Architecture](./docs/volume-10/01-security-architecture.md)

## CI/CD Pipeline

| Workflow | Trigger | Description |
|----------|---------|-------------|
| [CI](.github/workflows/ci.yml) | Push/PR to `main` | Lint, test, Docker build |
| [Backend CI](.github/workflows/backend-ci.yml) | Push/PR touching `src/backend` | Python lint + pytest |
| [Frontend CI](.github/workflows/frontend-ci.yml) | Push/PR touching `src/frontend` | ESLint, typecheck, build |
| [Docker CI](.github/workflows/docker-ci.yml) | Push/PR touching Dockerfiles | Build images + smoke test |
| [Security](.github/workflows/security.yml) | Weekly schedule + push | Dependency scan, SAST, secret scan |
| [CD](.github/workflows/cd.yml) | Push to `main` / tags | Build → staging → manual gate → production |

## License

MIT — see [LICENSE](LICENSE) for details.
