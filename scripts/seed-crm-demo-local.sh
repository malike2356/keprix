#!/usr/bin/env bash
# Seed CRM demo data for LOCAL Keprix only (never live / Contabo / production).
#
# Usage:
#   bash scripts/seed-crm-demo-local.sh
#   bash scripts/seed-crm-demo-local.sh --workspace default --json
#
# Prefer seeding inside running keprix-backend so UI at localhost:3000 sees data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export KEPRIX_ALLOW_CRM_DEMO_SEED=1
export KEPRIX_DEMO_SEED_CONFIRM=local-only

# Refuse if caller already set a live/prod marker
for var in KEPRIX_ENV APP_ENV KEPRIX_DEPLOYMENT KEPRIX_RUNTIME; do
  val="${!var:-}"
  case "$(echo "$val" | tr '[:upper:]' '[:lower:]')" in
    production|prod|staging|live|canary)
      echo "Refusing: $var=$val (local demo seed only)" >&2
      exit 2
      ;;
  esac
done

ARGS=("$@")

run_host() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY="$ROOT/.venv/bin/python"
  else
    PY="python3"
  fi
  echo "Seeding via host Python ($PY) ..."
  KEPRIX_ALLOW_CRM_DEMO_SEED=1 KEPRIX_DEMO_SEED_CONFIRM=local-only \
    "$PY" -m keprix.crm.demo_seed "${ARGS[@]}"
}

run_docker() {
  echo "Seeding via docker exec keprix-backend (UI data volume) ..."
  # Ensure latest seed module is in the container
  docker cp "$ROOT/src/keprix/crm/demo_seed.py" keprix-backend:/app/src/keprix/crm/demo_seed.py
  docker exec \
    -e KEPRIX_ALLOW_CRM_DEMO_SEED=1 \
    -e KEPRIX_DEMO_SEED_CONFIRM=local-only \
    -e KEPRIX_ENV=local \
    keprix-backend \
    python -m keprix.crm.demo_seed "${ARGS[@]}"
}

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'keprix-backend'; then
  health="$(docker inspect keprix-backend --format '{{.State.Health.Status}}' 2>/dev/null || echo unknown)"
  if [[ "$health" == "healthy" || "$health" == "unknown" ]]; then
    run_docker
    exit 0
  fi
  echo "keprix-backend present but health=$health; falling back to host seed" >&2
fi

run_host
