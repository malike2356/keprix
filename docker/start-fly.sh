#!/usr/bin/env bash
# Start API + Next standalone on one Fly machine.
set -euo pipefail

mkdir -p "${KEPRIX_HOME:-/data/keprix}/logs"

export PYTHONPATH="${PYTHONPATH:-}:/app/src"
uvicorn keprix.api.main:app --host 127.0.0.1 --port "${BACKEND_PORT:-3333}" &
API_PID=$!

cd /app/frontend
export PORT="${PORT:-3000}"
export HOSTNAME="${HOSTNAME:-0.0.0.0}"
node server.js &
WEB_PID=$!

term() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap term TERM INT

# Exit if either child dies
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 2
done
term
exit 1
