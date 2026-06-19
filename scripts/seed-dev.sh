#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Seed Development Data
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🌱 Seeding development data..."

# Wait for backend
echo "⏳ Waiting for backend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Backend ready"
        break
    fi
    sleep 2
done

# Run seed scripts (to be implemented)
# docker compose -f deployment/docker-compose.yml exec -T backend python scripts/seed_tenants.py --count 5
# docker compose -f deployment/docker-compose.yml exec -T backend python scripts/seed_users.py --count 50

# Set up MinIO buckets
echo "🪣 Setting up MinIO buckets..."
docker compose -f deployment/docker-compose.yml exec -T minio sh -c '
    mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null
    for bucket in amc-assets amc-uploads amc-exports; do
        mc mb local/$bucket --ignore-existing 2>/dev/null
    done
    mc policy set public local/amc-assets 2>/dev/null
    echo "   ✅ MinIO buckets created"
'

# Set up RabbitMQ queues
echo "🔧 Setting up RabbitMQ queues..."
docker compose -f deployment/docker-compose.yml exec -T rabbitmq sh -c '
    for queue in amc.email.trigger amc.sms.trigger amc.webhook.deliver amc.media.process amc.ai.inference amc.analytics.ingest; do
        rabbitmqadmin declare queue name=$queue durable=true 2>/dev/null || true
    done
    echo "   ✅ RabbitMQ queues created"
'

echo ""
echo "✅ Dev environment seeded successfully!"
