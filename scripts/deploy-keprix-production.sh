#!/usr/bin/env bash
# Canonical production deploy: Docker Compose + Caddy (+ optional canary + Scout).
#
# Optional helpers (not the primary path):
#   scripts/deploy-server.sh          low-level fail-closed steps
#   scripts/deploy-managed.sh         Fly / droplet wrappers
#   scripts/bootstrap-do-droplet.sh   DO provisioning
#
# Usage:
#   bash scripts/deploy-keprix-production.sh --domain app.example.com
#   bash scripts/deploy-keprix-production.sh --domain app.example.com --canary --tag v0.16.1
#   bash scripts/deploy-keprix-production.sh --skip-scout
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOMAIN="${KEPRIX_DOMAIN:-}"
TAG="${KEPRIX_IMAGE_TAG:-}"
CANARY=0
SKIP_SCOUT=0
BOOTSTRAP=0
REF=""
EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --canary) CANARY=1; shift ;;
    --bootstrap) BOOTSTRAP=1; shift ;;
    --skip-scout) SKIP_SCOUT=1; shift ;;
    --skip-tests|--skip-pull|--skip-migrate|--skip-backup)
      EXTRA+=("$1"); shift ;;
    --proxy|--profile)
      EXTRA+=("$1" "$2"); shift 2 ;;
    -h|--help)
      cat <<'EOF'
Usage: deploy-keprix-production.sh [options]
  --domain HOST     Public hostname (required for --bootstrap / --canary)
  --bootstrap       Install Caddy/firewall/timers then deploy
  --canary          Canary then flip proxy (requires --tag)
  --tag TAG         Image tag / canary tag
  --ref REF         Git ref for deploy-server pull
  --skip-scout      Skip Scout audit/tests/ping
EOF
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

echo "Keprix production deploy (Compose + Caddy)"
echo "  root: $ROOT"

if [ ! -f "$ROOT/.env" ]; then
  echo "ERROR: missing .env; run scripts/generate-production-env.sh first" >&2
  exit 1
fi
if grep -Eq 'changeme|GENERATE_RANDOM_|REPLACE_ME' "$ROOT/.env"; then
  echo "ERROR: .env still contains placeholder secrets" >&2
  exit 1
fi

export KEPRIX_DEPLOY_PROFILE=compose
if [ -n "$TAG" ]; then
  export KEPRIX_IMAGE_TAG="$TAG"
fi
if [ -n "$DOMAIN" ]; then
  export KEPRIX_DOMAIN="$DOMAIN"
fi

SERVER_ARGS=(--profile compose "${EXTRA[@]}")
[ -n "$REF" ] && SERVER_ARGS+=(--ref "$REF")
[ -n "$TAG" ] && [ "$CANARY" != "1" ] && SERVER_ARGS+=(--skip-pull)

if [ "$BOOTSTRAP" = "1" ]; then
  [ -n "$DOMAIN" ] || { echo "--bootstrap requires --domain" >&2; exit 2; }
  bash "$ROOT/scripts/deploy-server.sh" --bootstrap --domain "$DOMAIN" --profile compose --proxy caddy "${EXTRA[@]}"
fi

if [ "$CANARY" = "1" ]; then
  [ -n "$DOMAIN" ] || { echo "--canary requires --domain" >&2; exit 2; }
  [ -n "$TAG" ] || { echo "--canary requires --tag" >&2; exit 2; }
  echo "  mode: canary"
  bash "$ROOT/scripts/deploy-canary.sh" --domain "$DOMAIN" --tag "$TAG"
else
  echo "  mode: rolling"
  bash "$ROOT/scripts/deploy-server.sh" "${SERVER_ARGS[@]}"
fi

if [ "$SKIP_SCOUT" != "1" ]; then
  echo "  Security audit..."
  PYTHONPATH=src python3 -m keprix_cli.main security audit || {
    echo "Security audit failed"
    exit 1
  }
  if [ -f tests/security/test_scout_integration.py ]; then
    echo "  Scout tests..."
    PYTHONPATH=src python3 -m pytest \
      tests/security/test_scout_integration.py \
      tests/integration/test_scout_signals.py \
      tests/integration/test_scout_commands.py -q || {
      echo "Core Scout tests failed"
      exit 1
    }
  fi
  PYTHONPATH=src python3 -m keprix_cli.main scout ping || {
    echo "Scout ping failed (set --skip-scout if Scout is not configured)"
    exit 1
  }
fi

curl -fsS "http://127.0.0.1:${BACKEND_PORT:-3333}/api/health" || exit 1
echo
echo "Done: production deploy completed."
echo "Optional helpers: deploy-server.sh, deploy-managed.sh, bootstrap-do-droplet.sh"
