#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Reset Development Database
# Drops all tables, re-runs migrations, and seeds fresh data.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "⚠️  WARNING: This will DESTROY all data in the development database!"
read -p "Are you sure? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🗑️  Dropping all tables..."
docker compose -f deployment/docker-compose.yml exec -T postgres psql -U amc -d aegis_marketing_cloud -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO amc;
"

echo ""
echo "📦 Running migrations..."
docker compose -f deployment/docker-compose.yml exec -T backend alembic upgrade head

echo ""
echo "🌱 Seeding data..."
bash "$SCRIPT_DIR/seed-dev.sh"

echo ""
echo "✅ Database reset complete!"
