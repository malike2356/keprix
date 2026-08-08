#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
PORT="${ABBIS_SIDECAR_PORT:-3360}"
HOST="${ABBIS_SIDECAR_HOST:-127.0.0.1}"
echo "Starting ABBIS Keprix sidecar on ${HOST}:${PORT}"
exec python3 -m uvicorn http_app:app --host "$HOST" --port "$PORT"
