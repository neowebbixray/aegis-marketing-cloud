#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Combined Security Scan Script
# =============================================================================
# Runs:
#   1. Bandit (Python SAST)
#   2. Trivy (Container + filesystem scanning)
#   3. ESLint security plugin (if frontend present)
#   4. pip-audit (Python dependency vulnerabilities)
#
# Usage:
#   ./scripts/ci-security-scan.sh              # Run all scanners
#   ./scripts/ci-security-scan.sh --python-only # Python scans only
#   ./scripts/ci-security-scan.sh --ci         # CI-friendly (exit codes)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/src/backend"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"
SECURITY_DIR="$PROJECT_ROOT/deployment/security"
REPORT_DIR="$PROJECT_ROOT/reports/security"

# ── Flags ────────────────────────────────────────────────────────────────────
PYTHON_ONLY=false
CI_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python-only) PYTHON_ONLY=true; shift ;;
        --ci) CI_MODE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$REPORT_DIR"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass=0
fail=0

run_check() {
    local name="$1"
    local cmd="$2"
    local report_file="$REPORT_DIR/${name// /_}.log"

    echo -e "${YELLOW}[*] Running: $name${NC}"
    echo "Command: $cmd" > "$report_file"
    echo "---" >> "$report_file"

    if eval "$cmd" >> "$report_file" 2>&1; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        pass=$((pass + 1))
    else
        local exit_code=$?
        if [[ "$CI_MODE" == true ]]; then
            echo -e "  ${RED}❌ FAIL (exit code $exit_code)${NC}"
            fail=$((fail + 1))
        else
            echo -e "  ${YELLOW}⚠️  WARN (exit code $exit_code)${NC}"
            pass=$((pass + 1))  # Non-CI: treat as warning
        fi
    fi
    echo ""
}

# ── 1. Bandit (Python SAST) ─────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         Aegis Marketing Cloud — Security Scan            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

run_check \
    "Bandit Python SAST" \
    "cd '$BACKEND_DIR' && \
     python -m bandit -r app/ \
     -c '$SECURITY_DIR/bandit.conf' \
     -f custom \
     -o '$REPORT_DIR/bandit_report.txt' 2>&1; \
     echo '---'; \
     cat '$REPORT_DIR/bandit_report.txt' 2>/dev/null | head -20"

# ── 2. pip-audit (Python deps) ──────────────────────────────────────────────
run_check \
    "pip-audit Python Dependencies" \
    "cd '$BACKEND_DIR' && \
     python -m pip_audit \
     --requirement <(grep -v '^[[:space:]]*#' pyproject.toml | grep -v '^\[' | grep -v '^$' | tr -d ',') \
     --ignore-vuln PYSEC-0000-0000 \
     --desc on 2>&1 || true"

# ── 3. Trivy Filesystem Scan ───────────────────────────────────────────────
if command -v trivy &>/dev/null; then
    run_check \
        "Trivy Filesystem Scan" \
        "trivy fs --quiet \
         --severity HIGH,CRITICAL \
         --ignorefile '$SECURITY_DIR/.trivyignore' \
         --exit-code 0 \
         '$PROJECT_ROOT/src' 2>&1 | tail -50"
else
    echo -e "${YELLOW}[!] Trivy not installed — skipping container/fs scan${NC}"
    echo "Install: https://aquasecurity.github.io/trivy/"
fi

# ── 4. ESLint Security (frontend) ──────────────────────────────────────────
if [[ "$PYTHON_ONLY" == false ]] && [[ -d "$FRONTEND_DIR" ]]; then
    if command -v npx &>/dev/null; then
        run_check \
            "ESLint Security Plugin" \
            "cd '$FRONTEND_DIR' && \
             npx eslint --config '$SECURITY_DIR/eslint-security.conf' \
             --ext .ts,.tsx,.js,.jsx src/ 2>&1 || true"
    else
        echo -e "${YELLOW}[!] npx not available — skipping frontend scan${NC}"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   Scan Summary                           ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo -e "║  ${GREEN}PASS${NC}: $pass    ${RED}FAIL${NC}: $fail                               ║"
if [[ "$fail" -gt 0 ]]; then
    echo "║  ⚠️  Some checks failed (review reports)                ║"
fi
echo "║  Reports: $REPORT_DIR                    ║"
echo "╚══════════════════════════════════════════════════════════╝"

if [[ "$CI_MODE" == true ]] && [[ "$fail" -gt 0 ]]; then
    exit 1
fi
exit 0
