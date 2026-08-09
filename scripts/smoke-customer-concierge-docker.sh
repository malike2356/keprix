#!/usr/bin/env bash
# Customer Concierge local smoke (Prompt 635).
# Runs hermetic pytest suite. Optional compose health when DOCKER_SMOKE=1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Customer Concierge hermetic suite =="
python -m pytest tests/customer_concierge/ -q --tb=line

echo "== Fixture manifest present =="
test -f contracts/customer-concierge-v1/fixtures/synthetic/MANIFEST.json

echo "== Desktop packaging tree present =="
test -f src/keprix/apps/desktop/package.json

if [[ "${DOCKER_SMOKE:-0}" == "1" ]]; then
  echo "== Docker compose health (optional) =="
  docker compose -f docker/docker-compose.yml ps || true
  curl -fsS -o /dev/null -w 'local_health %{http_code}\n' http://127.0.0.1:3333/api/health || {
    echo "WARNING: local API health not reachable; hermetic suite already passed"
  }
fi

echo "OK customer-concierge smoke"
