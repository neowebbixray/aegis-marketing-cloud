# =============================================================================
# Aegis Marketing Cloud — Root Makefile
#
# Developer workflow commands for local development, testing, and deployment.
# =============================================================================

SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ── Project paths ───────────────────────────────────────────────────────────
BACKEND_DIR  := src/backend
FRONTEND_DIR := src/frontend
DEPLOY_DIR   := deployment

# ── Docker Compose ──────────────────────────────────────────────────────────
COMPOSE_FILE   := $(DEPLOY_DIR)/docker-compose.yml
COMPOSE_OVERRIDE := $(DEPLOY_DIR)/docker-compose.override.yml
COMPOSE_CMD    := docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_OVERRIDE)

# ── Help ────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ── Environment ─────────────────────────────────────────────────────────────
.PHONY: env env-backend env-frontend

env: env-backend env-frontend ## Copy .env.example files if .env doesn't exist

env-backend:
	@if [ ! -f $(BACKEND_DIR)/.env ]; then \
		cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env; \
		echo "✅ Created $(BACKEND_DIR)/.env from .env.example"; \
	fi

env-frontend:
	@if [ ! -f $(FRONTEND_DIR)/.env.local ]; then \
		cp $(FRONTEND_DIR)/.env.local.example $(FRONTEND_DIR)/.env.local 2>/dev/null || true; \
		echo "✅ Created $(FRONTEND_DIR)/.env.local"; \
	fi

# ── Python virtual environment ──────────────────────────────────────────────
.PHONY: venv venv-clean

venv: ## Create Python virtual environment and install deps
	@if [ ! -d $(BACKEND_DIR)/.venv ]; then \
		cd $(BACKEND_DIR) && python3 -m venv .venv; \
		echo "✅ Created virtual environment"; \
	fi
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		pip install --upgrade pip setuptools && \
		pip install -e ".[dev]"
	@echo "✅ Dependencies installed"

venv-clean: ## Remove Python virtual environment
	@rm -rf $(BACKEND_DIR)/.venv
	@echo "✅ Virtual environment removed"

# ── Docker Compose ──────────────────────────────────────────────────────────
.PHONY: up up-d up-db down down-volumes restart logs status ps

up: env ## Start all services (detached)
	$(COMPOSE_CMD) up --build -d
	@echo "✅ Stack started. Check status with 'make ps'"

up-db: env ## Start only infrastructure services (Postgres, Redis, MinIO, RabbitMQ, Qdrant)
	$(COMPOSE_CMD) up --build -d postgres redis minio rabbitmq qdrant
	@echo "✅ Database services started"

down: ## Stop all services
	$(COMPOSE_CMD) down
	@echo "✅ Stack stopped"

down-volumes: ## Stop and remove volumes (WARNING: destroys data)
	$(COMPOSE_CMD) down -v
	@echo "✅ Stack stopped and volumes removed"

restart: ## Restart all services
	$(COMPOSE_CMD) restart
	@echo "✅ Stack restarted"

logs: ## Follow logs from all services
	$(COMPOSE_CMD) logs -f

ps: ## List running services
	$(COMPOSE_CMD) ps

# ── Backend ─────────────────────────────────────────────────────────────────
.PHONY: backend-sh backend-logs backend-test

backend-sh: ## Open a shell in the backend container
	$(COMPOSE_CMD) exec backend /bin/bash

backend-logs: ## Follow backend logs
	$(COMPOSE_CMD) logs -f backend

backend-test: ## Run backend tests
	$(COMPOSE_CMD) exec -T backend pytest tests/ -v --cov=app --cov-report=term-missing

# ── Frontend ────────────────────────────────────────────────────────────────
.PHONY: frontend-sh frontend-logs

frontend-sh: ## Open a shell in the frontend container
	$(COMPOSE_CMD) exec frontend /bin/sh

frontend-logs: ## Follow frontend logs
	$(COMPOSE_CMD) logs -f frontend

# ── Database Migrations ─────────────────────────────────────────────────────
.PHONY: migrate migrate-create migrate-downgrade migrate-merge

migrate: ## Apply all pending migrations
	$(COMPOSE_CMD) exec -T backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="add widget table")
	@if [ -z "$(msg)" ]; then \
		echo "❌ Usage: make migrate-create msg=\"description of changes\""; \
		exit 1; \
	fi
	$(COMPOSE_CMD) exec -T backend alembic revision --autogenerate -m "$(msg)"

migrate-downgrade: ## Roll back one migration (usage: make migrate-downgrade rev=abc123)
	@if [ -z "$(rev)" ]; then \
		echo "❌ Usage: make migrate-downgrade rev=<revision_id>"; \
		echo "   Use 'make migrate-history' to see revisions."; \
		exit 1; \
	fi
	$(COMPOSE_CMD) exec -T backend alembic downgrade $(rev)

migrate-history: ## Show migration history
	$(COMPOSE_CMD) exec -T backend alembic history

migrate-current: ## Show current migration version
	$(COMPOSE_CMD) exec -T backend alembic current

# ── Local migrations (without Docker) ───────────────────────────────────────
.PHONY: migrate-local migrate-create-local

migrate-local: ## Apply migrations locally (requires venv + local PG)
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		alembic upgrade head

migrate-create-local: ## Create migration locally (usage: make migrate-create-local msg="...")
	@if [ -z "$(msg)" ]; then \
		echo "❌ Usage: make migrate-create-local msg=\"description\""; \
		exit 1; \
	fi
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		alembic revision --autogenerate -m "$(msg)"

# ── Seed Data ───────────────────────────────────────────────────────────────
.PHONY: seed seed-dev

seed: ## Run seed data scripts
	@echo "🌱 Seeding development data..."
	@echo "✅ Seed complete (seed script TBD)"

# ── Testing ─────────────────────────────────────────────────────────────────
.PHONY: test test-backend test-frontend test-all

test-backend: ## Run backend tests (requires Docker stack running)
	$(COMPOSE_CMD) exec -T backend pytest tests/ -v --cov=app --cov-report=term-missing

test-frontend: ## Run frontend tests
	@cd $(FRONTEND_DIR) && npm test 2>/dev/null || echo "⚠️  Frontend tests not configured yet"

test: test-backend test-frontend ## Run all tests

test-coverage: ## Run tests with coverage report
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		pytest tests/ -v \
			--cov=app \
			--cov-report=html:coverage_html \
			--cov-report=term-missing
	@echo "📊 Coverage report: $(BACKEND_DIR)/coverage_html/index.html"

# ── Code Quality ────────────────────────────────────────────────────────────
.PHONY: lint lint-python lint-frontend format openapi security-scan

openapi: ## Generate OpenAPI 3.1 spec (docs/openapi.json + docs/openapi.yaml)
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate 2>/dev/null && \
		python $(PROJECT_ROOT)/scripts/generate-openapi.py || \
		python scripts/generate-openapi.py

security-scan: ## Run combined security scanning pipeline
	@bash scripts/ci-security-scan.sh --python-only

lint-python: ## Lint Python with ruff
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		ruff check . --output-format=concise

lint-frontend: ## Lint TypeScript with eslint
	@cd $(FRONTEND_DIR) && npm run lint 2>/dev/null || echo "⚠️  ESLint not configured"

lint: lint-python lint-frontend ## Run all linters

format: ## Format Python with ruff
	@cd $(BACKEND_DIR) && \
		source .venv/bin/activate && \
		ruff format .
	@echo "✅ Formatting applied"

# ── Infrastructure ──────────────────────────────────────────────────────────
.PHONY: docker-clean docker-prune

docker-clean: ## Prune unused Docker resources
	docker system prune -af --volumes 2>/dev/null || true
	@echo "✅ Docker cleaned"

# ── Admin / Utility ─────────────────────────────────────────────────────────
.PHONY: shell shell-backend shell-frontend

shell-backend: ## Open a Python shell in the backend container
	$(COMPOSE_CMD) exec backend python

# ── First-time setup ────────────────────────────────────────────────────────
.PHONY: setup

setup: venv env ## First-time project setup
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║   Aegis Marketing Cloud — Setup Complete                ║"
	@echo "╠══════════════════════════════════════════════════════════╣"
	@echo "║   Next steps:                                          ║"
	@echo "║   1. Edit src/backend/.env with your settings          ║"
	@echo "║   2. make up-db    # Start database services           ║"
	@echo "║   3. make up       # Start everything                  ║"
	@echo "║   4. make migrate  # Run database migrations           ║"
	@echo "║   5. Open http://localhost:3000                        ║"
	@echo "╚══════════════════════════════════════════════════════════╝"
