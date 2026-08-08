#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
PORT="${XECLONE_SIDECAR_PORT:-3361}"
HOST="${XECLONE_SIDECAR_HOST:-127.0.0.1}"
echo "Starting Xeclone Keprix sidecar on ${HOST}:${PORT}"
exec python3 -m uvicorn http_app:app --host "$HOST" --port "$PORT"
