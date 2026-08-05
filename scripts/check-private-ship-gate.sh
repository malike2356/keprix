#!/usr/bin/env bash
# check-private-ship-gate.sh: Focused pre-release gate for private/internal ship checks.
#
# Runs, in order, and stops on the first failure:
#   1. Community file validation (if present)
#   2. Architecture boundary tests
#   3. Auth + billing focused tests
#   4. TUI parity gate
#   5. TUI surpass-Hermes gate
#   6. Agent parity gate
#   7. Frontend TypeScript typecheck (tsc --noEmit)
#   8. Optional pipx install smoke test (skipped by default; too slow for a
#      fast local/CI gate, see SHIP_GATE_SMOKE_PIPX below)
#
# Usage:
#   bash scripts/check-private-ship-gate.sh
#   SHIP_GATE_SMOKE_PIPX=1 bash scripts/check-private-ship-gate.sh
#
# Exit 0 = every gate passed. Any failing step aborts the script immediately
# (set -euo pipefail) with a non-zero exit code.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Prefer the project virtualenv (Python 3.11); fall back to python3 on PATH.
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

step() {
    echo ""
    echo "=========================================="
    echo "  $1"
    echo "=========================================="
}

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
}

step "1/8 Community file validation"
if [ -f scripts/validate-community-files.sh ]; then
    bash scripts/validate-community-files.sh
    pass "Community file validation"
else
    echo -e "${YELLOW}SKIP${NC}: scripts/validate-community-files.sh not found"
fi

step "2/8 Architecture tests"
"$PYTHON" -m pytest tests/architecture -q
pass "Architecture tests"

step "3/8 Auth + billing focused tests"
"$PYTHON" -m pytest tests/auth tests/billing -q
pass "Auth + billing tests"

step "4/8 TUI parity gate"
bash scripts/check-tui-parity.sh
pass "TUI parity gate"

step "5/8 TUI surpass-Hermes gate"
bash scripts/check-tui-surpass-hermes.sh
pass "TUI surpass-Hermes gate"

step "6/8 Agent parity gate"
bash scripts/check-agent-parity.sh
pass "Agent parity gate"

step "7/8 Frontend TypeScript typecheck"
if [ -d frontend ]; then
    (cd frontend && npx tsc --noEmit)
    pass "Frontend tsc --noEmit"
else
    echo -e "${YELLOW}SKIP${NC}: frontend/ not found"
fi

step "8/8 pipx install smoke test"
if [ "${SHIP_GATE_SMOKE_PIPX:-0}" = "1" ]; then
    if [ -f scripts/smoke-pipx-install.sh ]; then
        bash scripts/smoke-pipx-install.sh
        pass "pipx install smoke test"
    else
        echo -e "${YELLOW}SKIP${NC}: scripts/smoke-pipx-install.sh not found"
    fi
else
    echo -e "${YELLOW}SKIP${NC}: pipx install smoke test skipped by default (builds a fresh"
    echo "  package and virtualenv, too slow for a fast gate). Re-run with"
    echo "  SHIP_GATE_SMOKE_PIPX=1 bash scripts/check-private-ship-gate.sh to include it."
fi

echo ""
echo "=========================================="
echo -e "  ${GREEN}Private ship gate: ALL CHECKS PASSED${NC}"
echo "=========================================="
