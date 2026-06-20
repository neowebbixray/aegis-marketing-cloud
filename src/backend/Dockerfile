# =============================================================================
# Aegis Marketing Cloud — Backend Dockerfile
# Multi-stage build: dev, test, production
# =============================================================================

# ── Base stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps (build-essential, libpq for psycopg/asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata first for layer caching
COPY pyproject.toml ./

# ── Development target ──────────────────────────────────────────────────────
FROM base AS development

# Install project in editable mode with dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Install watchfiles for hot-reload
RUN pip install --no-cache-dir watchfiles

# Copy source (will be overridden by volume mount in dev)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--reload-dir", "/app"]

# ── Test target ─────────────────────────────────────────────────────────────
FROM base AS test

# Install project in editable mode with dev dependencies (for testing)
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["pytest", "tests/", "-v", "--cov=app", "--cov-report=term-missing"]

# ── Production target ───────────────────────────────────────────────────────
FROM base AS production

# Install project in editable mode (runtime only)
RUN pip install --no-cache-dir -e "."

COPY . .

# Create non-root user
RUN groupadd -r amc && useradd -r -g amc -u 1000 amc \
    && chown -R amc:amc /app
USER amc

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]