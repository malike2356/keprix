#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PETRACLUS_PLATFORM_MODE="${PETRACLUS_PLATFORM_MODE:-FULL}"
export PETRACLUS_SHARED_TOKEN="${PETRACLUS_SHARED_TOKEN:-}"
PORT="${PETRACLUS_SIDECAR_PORT:-3362}"
HOST="${PETRACLUS_SIDECAR_HOST:-127.0.0.1}"
echo "Starting Petraclus Keprix sidecar on ${HOST}:${PORT}"
exec python3 -m uvicorn http_app:app --host "$HOST" --port "$PORT"
