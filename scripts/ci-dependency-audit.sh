#!/usr/bin/env bash
# =============================================================================
# Aegis Marketing Cloud — Dependency Audit Script
# =============================================================================
# Runs pip-audit (Python) and npm audit (Node.js) on the project's declared
# dependencies.  Exits non-zero if any vulnerabilities are found.
#
# Usage:
#   ./scripts/ci-dependency-audit.sh              # Audit all
#   ./scripts/ci-dependency-audit.sh --python-only # Python only
#   ./scripts/ci-dependency-audit.sh --npm-only    # npm only
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/src/backend"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"
REPORT_DIR="$PROJECT_ROOT/reports/dependency-audit"

MODE="${1:-all}"   # all | python-only | npm-only
FAILED=0

mkdir -p "$REPORT_DIR"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Aegis Marketing Cloud — Dependency Audit             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Python: pip-audit ────────────────────────────────────────────────────────
if [[ "$MODE" == "all" || "$MODE" == "python-only" ]]; then
    echo -e "${YELLOW}[*] pip-audit (Python dependencies)${NC}"

    if command -v pip-audit &>/dev/null || python -m pip_audit --help &>/dev/null 2>&1; then
        AUDIT_CMD="python -m pip_audit"

        # pip-audit supports --requirement for requirements.txt or -r for pyproject.toml via pip
        if [[ -f "$BACKEND_DIR/requirements.txt" ]]; then
            AUDIT_CMD="$AUDIT_CMD --requirement $BACKEND_DIR/requirements.txt"
        elif [[ -f "$BACKEND_DIR/pyproject.toml" ]]; then
            # Use pip-audit with pip: export deps then audit
            AUDIT_CMD="cd '$BACKEND_DIR' && pip-audit"
        else
            AUDIT_CMD="$AUDIT_CMD -r /dev/null"
        fi

        REPORT_FILE="$REPORT_DIR/pip-audit.txt"
        if eval "$AUDIT_CMD" > "$REPORT_FILE" 2>&1; then
            echo -e "  ${GREEN}✅ No vulnerabilities found${NC}"
        else
            echo -e "  ${RED}❌ Vulnerabilities detected (see $REPORT_FILE)${NC}"
            cat "$REPORT_FILE"
            FAILED=1
        fi
    else
        echo -e "  ${YELLOW}⚠️  pip-audit not installed — skipping${NC}"
        echo "  Install: pip install pip-audit"
    fi
    echo ""
fi

# ── Node.js: npm audit ───────────────────────────────────────────────────────
if [[ "$MODE" == "all" || "$MODE" == "npm-only" ]]; then
    echo -e "${YELLOW}[*] npm audit (Node.js dependencies)${NC}"

    if [[ -d "$FRONTEND_DIR" ]]; then
        REPORT_FILE="$REPORT_DIR/npm-audit.txt"
        if npm audit --prefix "$FRONTEND_DIR" --audit-level=high > "$REPORT_FILE" 2>&1; then
            echo -e "  ${GREEN}✅ No high/critical vulnerabilities found${NC}"
        else
            echo -e "  ${RED}❌ High/critical vulnerabilities detected (see $REPORT_FILE)${NC}"
            # Print summary lines only
            grep -E "^(#|[A-Z ]|found|audited)" "$REPORT_FILE" || true
            FAILED=1
        fi
    else
        echo -e "  ${YELLOW}⚠️  Frontend directory not found — skipping npm audit${NC}"
    fi
    echo ""
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Dependency Audit Summary                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
if [[ "$FAILED" -eq 0 ]]; then
    echo -e "║  ${GREEN}✅ All checks passed${NC}                                ║"
else
    echo -e "║  ${RED}❌ Some checks failed (review reports)${NC}               ║"
fi
echo "║  Reports: $REPORT_DIR                      ║"
echo "╚══════════════════════════════════════════════════════════╝"

exit "$FAILED"
