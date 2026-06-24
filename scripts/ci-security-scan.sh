#!/usr/bin/env bash

set -eu -o pipefail

# Python security scanning script for CI

echo "🔍 Running Python security scan..."

# Install Bandit if not present
python -m pip install --quiet bandit || true

echo "🔍 Running Bandit scan (optimized)"

cd src/backend || exit 1

# Create reports directory if missing
mkdir -p ../reports

echo "🔍 Bandit scan started"

# Run Bandit scan with optimizations for speed
bandit -r . --format=xml --output=../reports/bandit-report.xml \
  --tests=B101,B102 \
  --skip=tests,venv \
  --confidence-level=high \
  --severity-level=high \
  --jobs=2

echo "🔍 Bandit scan completed"

# Continue with other scans...
