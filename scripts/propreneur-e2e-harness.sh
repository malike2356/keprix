#!/usr/bin/env bash
# Two-process Propreneur + Keprix e2e harness (prompt 642).
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROPRENEUR="$WORKSPACE/propreneur"
KEPRIX="$WORKSPACE/keprix"
PORT="${PROPRENEUR_E2E_PORT:-8765}"
FIXTURES="${KEPRIX_E2E_PROPRENEUR_FIXTURES:-/tmp/propreneur-e2e-fixtures.json}"
EVIDENCE_DIR="$KEPRIX/docs/architecture"
EVIDENCE_JSON="$EVIDENCE_DIR/propreneur-e2e-evidence.v1.json"
LOG_DIR="${TMPDIR:-/tmp}/propreneur-keprix-e2e-$$"
mkdir -p "$LOG_DIR" "$EVIDENCE_DIR"

export DB_DATABASE="${DB_DATABASE:-propreneur_testing_agent}"
export CENTRAL_DB_DATABASE="${CENTRAL_DB_DATABASE:-propreneur_testing_agent}"
export TENANCY_MAINTENANCE_DB="${TENANCY_MAINTENANCE_DB:-propreneur_testing_agent}"
export APP_ENV=testing
export PROPRENEUR_PRODUCT_API_URL="http://127.0.0.1:${PORT}"
export KEPRIX_E2E_PROPRENEUR=1
export KEPRIX_E2E_PROPRENEUR_FIXTURES="$FIXTURES"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "==> Preflight DB"
bash "$PROPRENEUR/scripts/bootstrap-testing-postgres.sh"
bash "$PROPRENEUR/scripts/preflight-testing-db.sh"

echo "==> Pest Aiva e2e + security (real Propreneur controllers/DB)"
cd "$PROPRENEUR"
php artisan test \
  tests/Feature/Aiva/AivaV1ApiTest.php \
  tests/Feature/Aiva/AivaV1E2eCrudMatrixTest.php \
  tests/Feature/Aiva/AivaV1SecurityFailClosedTest.php \
  | tee "$LOG_DIR/pest.log"

echo "==> Mint fixtures + start Propreneur HTTP server on :${PORT}"
cd "$PROPRENEUR"
php scripts/aiva-v1-e2e-mint-fixtures.php "$FIXTURES"
# RefreshDatabase from Pest wiped central; mint recreates tenants for live HTTP.
php artisan serve --host=127.0.0.1 --port="$PORT" >"$LOG_DIR/artisan-serve.log" 2>&1 &
SERVER_PID=$!

ready=0
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/" | grep -Eq '^[0-9]{3}$'; then
    ready=1
    break
  fi
  sleep 0.25
done
if [[ "$ready" != "1" ]]; then
  echo "PREFLIGHT FAILED: Propreneur artisan serve did not start on :${PORT}" >&2
  tail -n 40 "$LOG_DIR/artisan-serve.log" >&2 || true
  exit 1
fi

echo "==> Keprix regression (sidecar unit) + real boundary e2e"
cd "$KEPRIX"
# Prefer venv if present
PY=python3
if [[ -x "$KEPRIX/.venv/bin/python" ]]; then
  PY="$KEPRIX/.venv/bin/python"
elif [[ -x "$KEPRIX/src/.venv/bin/python" ]]; then
  PY="$KEPRIX/src/.venv/bin/python"
fi

export PYTHONPATH="${KEPRIX}/src:${PYTHONPATH:-}"
"$PY" -m pytest \
  tests/product_sidecar/test_propreneur_pack_handlers.py \
  tests/product_sidecar/test_propreneur_approvals_idempotency_events.py \
  tests/e2e_propreneur/test_real_propreneur_boundary.py \
  -q --tb=short | tee "$LOG_DIR/pytest.log"

echo "==> Write evidence report"
"$PY" "$KEPRIX/scripts/propreneur-e2e-evidence-report.py" \
  --fixtures "$FIXTURES" \
  --pest-log "$LOG_DIR/pest.log" \
  --pytest-log "$LOG_DIR/pytest.log" \
  --out "$EVIDENCE_JSON"

echo "OK: harness green. Evidence: $EVIDENCE_JSON"
echo "Logs: $LOG_DIR"
exit 0
