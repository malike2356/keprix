#!/usr/bin/env bash
# Optional CRM funnel E2E notes + local API smoke (prompt 450).
# Does not require Contabo. Prefer GUI paths over curl for operator sign-off.
#
# GUI path (Must):
#   1. /crm/discover  - run fake or companies_house adapter
#   2. /crm/jobs/{id} - Soft Wall materialize list
#   3. /crm/lists/{id} - preflight + Soft Wall enroll
#   4. /crm/inbox     - reply / takeover fixture
#   Soft Wall panel on /crm for pending approvals.
#
# Usage:
#   KEPRIX_BASE_URL=http://127.0.0.1:3333 bash scripts/e2e-crm-funnel.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${KEPRIX_BASE_URL:-http://127.0.0.1:3333}"
WS="${KEPRIX_CRM_WORKSPACE:-default}"

echo "CRM funnel E2E helper (API notes only; GUI is the Must path)"
echo "Base: $BASE workspace: $WS"
echo "Docs: docs/features/agentic-crm.md"
echo "Sign-off: docs/architecture/agentic-crm-signoff.md"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl missing; skip API probe"
  exit 0
fi

code="$(curl -fsS -o /dev/null -w '%{http_code}' "${BASE}/api/health" 2>/dev/null || true)"
if [[ "$code" != "200" ]]; then
  echo "API health not 200 (got ${code:-none}). Start Keprix locally before API probe."
  echo "GUI checklist still applies when the stack is up."
  exit 0
fi

echo "Health OK. Probe CRM status..."
curl -fsS "${BASE}/api/crm/status?workspace_id=${WS}" | head -c 400 || true
echo
echo "Discovery adapters..."
curl -fsS "${BASE}/api/crm/discovery/adapters?workspace_id=${WS}" | head -c 400 || true
echo
echo "Done. Complete Soft Wall enroll and inbox claim from /crm GUI, not only curl."
