#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Validate Environment Variables
# =============================================================================
set -euo pipefail

required_vars=(
    "SECRET_KEY"
    "DATABASE_URL"
    "REDIS_URL"
)

missing=0
for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "❌ Missing required env var: $var"
        missing=1
    else
        echo "✅ $var is set"
    fi
done

if [ "$missing" -eq 1 ]; then
    echo ""
    echo "Some required environment variables are missing."
    echo "Check your .env file or export them before running."
    exit 1
fi

echo ""
echo "✅ All required environment variables are set"
