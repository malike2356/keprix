#!/usr/bin/env bash
# Local deploy: start Fleetz Keprix sidecar on port 3354 and smoke health.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${FLEETZ_SIDECAR_PORT:-3354}"
HOST="${FLEETZ_SIDECAR_HOST:-127.0.0.1}"
PID_FILE="${ROOT}/.fleetz-sidecar.pid"
LOG_FILE="${ROOT}/.fleetz-sidecar.log"

export FLEETZ_USE_FIXTURES="${FLEETZ_USE_FIXTURES:-1}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

cd "$ROOT"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Fleetz sidecar already running pid=$(cat "$PID_FILE") on :${PORT}"
else
  # shellcheck disable=SC2086
  nohup python3 -m uvicorn http_app:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  echo "Started Fleetz sidecar pid=$(cat "$PID_FILE") log=$LOG_FILE"
  sleep 1
fi

code="$(curl -fsS -o /tmp/fleetz-health.json -w '%{http_code}' "http://${HOST}:${PORT}/health" || true)"
if [[ "$code" != "200" ]]; then
  echo "Health check failed http_code=${code}"
  tail -n 40 "$LOG_FILE" || true
  exit 1
fi

echo "Health OK:"
python3 - <<'PY'
import json
print(json.dumps(json.load(open("/tmp/fleetz-health.json")), indent=2))
PY

curl -fsS "http://${HOST}:${PORT}/v1/products/fleetz/capabilities" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("nodes", len(d.get("nodes",[])))'

echo "Local deploy ready: http://${HOST}:${PORT}/health"
