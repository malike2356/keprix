#!/usr/bin/env bash
# check-public-gtm-gate.sh: Fail closed before calling Keprix "public GTM ready".
#
# Checks (stop on first failure unless noted):
#   1. Anonymous GitHub reachable (repo or raw README HTTP 200)
#   2. No forbidden public strings (workspace abs path, keprixai.uk)
#   3. Installer syntax: bash -n scripts/install.sh
#   4. PyPI / pipx docs honesty (scripts/check-pypi-docs-honesty.sh)
#   5. Private quality gates (check-private-ship-gate.sh) unless skipped
#   6. Marketing / README curl or https clone one-liner
#   7. Optional keprixai.com HTTP 200 (skip with KEPRIX_SKIP_DOMAIN_CHECK=1)
#
# Env:
#   KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1  Skip private ship gate (surface-only; CI preview)
#   KEPRIX_SKIP_DOMAIN_CHECK=1        Soft-skip marketing origin until 427 ships
#   KEPRIX_PYPI_PUBLISHED=1           Passed through to pypi honesty script
#
# Usage:
#   bash scripts/check-public-gtm-gate.sh
#   KEPRIX_SKIP_DOMAIN_CHECK=1 KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1 bash scripts/check-public-gtm-gate.sh
#
# Exit 0 = public GTM surface (and private gates unless skipped) green.
# Do not print secrets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

GITHUB_REPO_URL="${KEPRIX_GITHUB_REPO_URL:-https://github.com/malike2356/keprix}"
GITHUB_RAW_README_URL="${KEPRIX_GITHUB_RAW_README_URL:-https://raw.githubusercontent.com/malike2356/keprix/main/README.md}"
MARKETING_URL="${KEPRIX_MARKETING_URL:-https://keprixai.com/}"

pass() {
  echo -e "${GREEN}PASS${NC}: $1"
}

fail() {
  echo -e "${RED}FAIL${NC}: $1" >&2
  exit 1
}

warn() {
  echo -e "${YELLOW}WARN${NC}: $1"
}

step() {
  echo ""
  echo "=========================================="
  echo "  $1"
  echo "=========================================="
}

http_code() {
  # Do not use curl -f: 404 still prints %{http_code} then fails, which would
  # append "000" via || echo and produce "404000".
  local url="$1"
  local code
  code="$(curl -sSIL -o /dev/null -w '%{http_code}' --max-time 20 "$url" 2>/dev/null || true)"
  if [[ -z "$code" ]]; then
    echo "000"
  else
    echo "$code"
  fi
}

http_code_get() {
  local url="$1"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$url" 2>/dev/null || true)"
  if [[ -z "$code" ]]; then
    echo "000"
  else
    echo "$code"
  fi
}

# ---------------------------------------------------------------------------
step "1/7 Anonymous GitHub reachable"

repo_code="$(http_code "$GITHUB_REPO_URL")"
raw_code="$(http_code "$GITHUB_RAW_README_URL")"
echo "  repo  $GITHUB_REPO_URL -> HTTP $repo_code"
echo "  raw   $GITHUB_RAW_README_URL -> HTTP $raw_code"

if [[ "$repo_code" != "200" && "$raw_code" != "200" ]]; then
  fail "Anonymous GitHub not reachable (repo=$repo_code raw=$raw_code). Publicize the repo (or mirror) before public GTM. See docs/operations/public-github-checklist.md"
fi
pass "Anonymous GitHub reachable (repo=$repo_code raw=$raw_code)"

# ---------------------------------------------------------------------------
step "2/7 Forbidden public strings"

forbidden_hits=0

# Absolute Verlox workspace path must not appear in stranger install docs.
if grep -RIn --exclude-dir=node_modules '/opt/lampp/htdocs/verlox' README.md docs/getting-started 2>/dev/null | head -20; then
  echo "  pattern: /opt/lampp/htdocs/verlox in README or docs/getting-started" >&2
  forbidden_hits=$((forbidden_hits + 1))
fi

# Wrong marketing domain (historical placeholder).
uk_paths=(README.md docs frontend/src/app/\(marketing\) frontend/src/components/marketing)
uk_found=0
for p in "${uk_paths[@]}"; do
  if [[ -e "$p" ]] && grep -RIn --exclude-dir=node_modules --exclude-dir=.next 'keprixai\.uk' "$p" 2>/dev/null | head -20; then
    uk_found=1
  fi
done
if [[ "$uk_found" -eq 1 ]]; then
  echo "  pattern: keprixai.uk in product/docs/marketing face" >&2
  forbidden_hits=$((forbidden_hits + 1))
fi

if [[ "$forbidden_hits" -gt 0 ]]; then
  fail "Forbidden public strings present ($forbidden_hits group(s)). Remove workspace abs paths and keprixai.uk from the ship face."
fi
pass "No forbidden public strings in README / getting-started / marketing docs face"

# ---------------------------------------------------------------------------
step "3/7 Installer script syntax"

if [[ ! -f scripts/install.sh ]]; then
  fail "scripts/install.sh missing"
fi
bash -n scripts/install.sh
pass "bash -n scripts/install.sh"

if [[ -f scripts/install-curl.sh ]]; then
  bash -n scripts/install-curl.sh
  pass "bash -n scripts/install-curl.sh"
fi

# ---------------------------------------------------------------------------
step "4/7 Install docs honesty (PyPI / pipx)"

bash scripts/check-pypi-docs-honesty.sh
pass "PyPI / pipx docs honesty"

# ---------------------------------------------------------------------------
step "5/7 Private quality gates"

if [[ "${KEPRIX_PUBLIC_GTM_SKIP_PRIVATE:-0}" == "1" ]]; then
  warn "Skipping private ship gate (KEPRIX_PUBLIC_GTM_SKIP_PRIVATE=1). Re-run without this flag before public GTM sign-off."
else
  if [[ ! -f scripts/check-private-ship-gate.sh ]]; then
    fail "scripts/check-private-ship-gate.sh missing"
  fi
  bash scripts/check-private-ship-gate.sh
  pass "Private ship gate"
fi

# ---------------------------------------------------------------------------
step "6/7 Marketing / README install snippet"

snippet_ok=0
if grep -qE 'curl -fsSL https://raw\.githubusercontent\.com/malike2356/keprix/.+/scripts/install\.sh' README.md 2>/dev/null; then
  snippet_ok=1
fi
if grep -qE 'git clone https://github\.com/malike2356/keprix\.git' README.md 2>/dev/null; then
  snippet_ok=1
fi
how="frontend/src/components/marketing/HowItWorks.tsx"
if [[ -f "$how" ]] && grep -qE 'curl -fsSL https://raw\.githubusercontent\.com/malike2356/keprix/.+/scripts/install\.sh|git clone https://github\.com/malike2356/keprix\.git' "$how" 2>/dev/null; then
  snippet_ok=1
fi

if [[ "$snippet_ok" -ne 1 ]]; then
  fail "README / HowItWorks missing https curl install one-liner or https git clone URL"
fi
pass "Marketing / README contain curl or https clone install snippet"

# ---------------------------------------------------------------------------
step "7/7 Marketing domain (keprixai.com)"

if [[ "${KEPRIX_SKIP_DOMAIN_CHECK:-0}" == "1" ]]; then
  warn "Skipping keprixai.com check (KEPRIX_SKIP_DOMAIN_CHECK=1). Enable after Contabo origin (427)."
else
  site_code="$(http_code_get "$MARKETING_URL")"
  echo "  $MARKETING_URL -> HTTP $site_code"
  if [[ "$site_code" != "200" ]]; then
    fail "keprixai.com expected HTTP 200, got $site_code. Fix origin (427) or set KEPRIX_SKIP_DOMAIN_CHECK=1 until live."
  fi
  pass "keprixai.com HTTP 200"
fi

echo ""
echo "=========================================="
echo -e "  ${GREEN}Public GTM gate: ALL CHECKS PASSED${NC}"
echo "=========================================="
echo "Note: stranger curl install still needs a public raw install.sh URL (covered by step 1)."
exit 0
