#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Dev Environment Bootstrap
# Starts all infrastructure services and seeds development data.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Aegis Marketing Cloud — Development Bootstrap         ║"
echo "╚══════════════════════════════════════════════════════════╝"

# 1. Ensure .env files exist
echo ""
echo "📋 Checking environment files..."
if [ ! -f src/backend/.env ]; then
    cp src/backend/.env.example src/backend/.env
    echo "   ✅ Created src/backend/.env"
fi

# 2. Build and start all services
echo ""
echo "🐳 Starting Docker Compose stack..."
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.override.yml up --build -d

# 3. Wait for PostgreSQL to be ready
echo ""
echo "⏳ Waiting for PostgreSQL..."
until docker compose -f deployment/docker-compose.yml exec -T postgres pg_isready -U amc -d aegis_marketing_cloud 2>/dev/null; do
    sleep 2
done
echo "   ✅ PostgreSQL ready"

# 4. Wait for backend health
echo ""
echo "⏳ Waiting for backend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Backend ready"
        break
    fi
    sleep 2
done

# 5. Run database migrations
echo ""
echo "📦 Running database migrations..."
docker compose -f deployment/docker-compose.yml exec -T backend alembic upgrade head
echo "   ✅ Migrations applied"

# 6. Print summary
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   🚀  Aegis Marketing Cloud is running!                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║   Frontend:   http://localhost:3000                     ║"
echo "║   Backend:    http://localhost:8000                     ║"
echo "║   API Docs:   http://localhost:8000/docs                ║"
echo "║   MinIO:      http://localhost:9001                     ║"
echo "║   RabbitMQ:   http://localhost:15672                    ║"
echo "║   MailHog:    http://localhost:8025                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
