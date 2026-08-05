#!/usr/bin/env bash
# check-agent-parity.sh: Run the agent parity regression gate.
#
# Covers: architecture boundaries, parity evals, TUI, agent core, tools,
# memory, product hooks, prompt layers, migration, and security.
# Does NOT require API keys. Safe for CI and local pre-commit.
#
# Usage:
#   bash scripts/check-agent-parity.sh
#
# Exit 0 = all parity gates pass.  Exit 1 = one or more suites failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate the virtualenv if it exists.
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASSED=0
FAILED=0
TOTAL=0

run_suite() {
    local label="$1"
    local logfile
    shift
    TOTAL=$((TOTAL + 1))
    printf "  %-55s " "${label}..."
    logfile="$(mktemp)"
    if python -m pytest "$@" -q --tb=line > "$logfile" 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        PASSED=$((PASSED + 1))
        rm -f "$logfile"
    else
        echo -e "${RED}FAIL${NC}"
        echo ""
        echo "Failure output for ${label}:"
        sed -n '1,220p' "$logfile"
        rm -f "$logfile"
        FAILED=$((FAILED + 1))
    fi
}

echo ""
echo "=========================================="
echo "  Keprix Agent Parity Gate"
echo "=========================================="
echo ""

# Architecture boundary tests
run_suite "Architecture boundary tests" \
    tests/architecture/

# Parity eval suite
run_suite "Parity eval suite (34 deterministic tests)" \
    tests/parity/

# TUI tests
run_suite "TUI tests" \
    tests/tui/

# Agent core tests
run_suite "Agent core tests" \
    tests/agent/

# Tool tests
run_suite "Tool tests" \
    tests/tools/

# Memory tests
run_suite "Memory tests" \
    tests/memory/

# Migration tests
run_suite "Migration and state rename tests" \
    tests/migration/

# Security tests
run_suite "Security tests" \
    tests/security/

# Billing tests
run_suite "Billing tests" \
    tests/billing/

# Provider tests
run_suite "Provider tests" \
    tests/providers/

echo ""
echo "=========================================="
echo "  Results: ${PASSED}/${TOTAL} passed"

if [ "$FAILED" -gt 0 ]; then
    echo -e "  ${RED}${FAILED} suite(s) FAILED${NC}"
    echo "=========================================="
    echo ""
    echo "Run individual suites with:"
    echo "  python -m pytest tests/<suite>/ -v"
    exit 1
else
    echo -e "  ${GREEN}All parity gates pass${NC}"
    echo "=========================================="
    echo ""
fi
