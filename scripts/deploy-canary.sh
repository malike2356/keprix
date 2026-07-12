#!/usr/bin/env bash
# Canary deploy: build/start side stack → health-check → flip Caddy → promote.
#
#   bash scripts/deploy-canary.sh --domain app.example.com --tag v0.16.1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOMAIN="${KEPRIX_DOMAIN:-}"
TAG="${KEPRIX_IMAGE_TAG:-canary}"
PROMOTE=1
CANARY_BACKEND_PORT="${CANARY_BACKEND_PORT:-3334}"
CANARY_FRONTEND_PORT="${CANARY_FRONTEND_PORT:-3001}"
LIVE_FRONTEND="127.0.0.1:3000"
CANARY_FRONTEND="127.0.0.1:${CANARY_FRONTEND_PORT}"
HEALTH_TIMEOUT="${KEPRIX_HEALTH_TIMEOUT:-120}"
STATE_DIR="${KEPRIX_CANARY_STATE:-/etc/keprix}"
SKIP_BUILD=0
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.canary.yml)

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --promote) PROMOTE=1; shift ;;
    --no-promote) PROMOTE=0; shift ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    -h|--help)
      echo "Usage: $0 --domain HOST [--tag TAG] [--promote|--no-promote] [--skip-build]"
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

[ -n "$DOMAIN" ] || { echo "--domain is required" >&2; exit 2; }

die() { echo "ERROR: $*" >&2; exit 1; }
log() { printf '  %s\n' "$*"; }

render_caddy() {
  local upstream="$1"
  local tmp
  tmp="$(mktemp)"
  sed -e "s|@DOMAIN@|$DOMAIN|g" -e "s|@FRONTEND_UPSTREAM@|$upstream|g" \
    "$ROOT/deploy/Caddyfile.template" >"$tmp"
  sudo mkdir -p /etc/caddy /var/log/caddy
  sudo cp "$tmp" /etc/caddy/Caddyfile
  rm -f "$tmp"
  if command -v caddy >/dev/null 2>&1; then
    sudo caddy validate --config /etc/caddy/Caddyfile || die "Caddyfile invalid"
    sudo systemctl reload caddy || sudo systemctl restart caddy || die "caddy reload failed"
  fi
}

wait_url() {
  local url="$1" deadline=$((SECONDS + HEALTH_TIMEOUT))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

export KEPRIX_IMAGE_TAG="$TAG"
export CANARY_BACKEND_PORT CANARY_FRONTEND_PORT

log "Starting canary stack (tag=$TAG) on :${CANARY_FRONTEND_PORT}/:${CANARY_BACKEND_PORT}..."
cd "$ROOT/docker"
if [ "$SKIP_BUILD" != "1" ]; then
  "${COMPOSE[@]}" build keprix-backend keprix-frontend || die "canary build failed"
fi
"${COMPOSE[@]}" up -d keprix-backend keprix-frontend || die "canary up failed"
cd "$ROOT"

log "Health-checking canary..."
wait_url "http://127.0.0.1:${CANARY_BACKEND_PORT}/api/health" || die "canary backend unhealthy"
wait_url "http://127.0.0.1:${CANARY_FRONTEND_PORT}/" || die "canary frontend unhealthy"
log "Canary healthy"

if [ "$PROMOTE" != "1" ]; then
  log "Leaving canary running without flip (--no-promote)."
  exit 0
fi

log "Flipping Caddy → canary (${CANARY_FRONTEND})..."
render_caddy "$CANARY_FRONTEND"
sleep 3

log "Promoting images to live compose (ports 3000/3333)..."
(
  cd "$ROOT/docker"
  KEPRIX_IMAGE_TAG="$TAG" docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    up -d --build keprix-backend keprix-frontend
) || die "live promote failed"

wait_url "http://127.0.0.1:3333/api/health" || die "live backend unhealthy after promote"
wait_url "http://127.0.0.1:3000/" || die "live frontend unhealthy after promote"

log "Flipping Caddy → live (${LIVE_FRONTEND})..."
render_caddy "$LIVE_FRONTEND"

log "Stopping canary project..."
(cd "$ROOT/docker" && "${COMPOSE[@]}" stop) || true

sudo mkdir -p "$STATE_DIR"
echo "$TAG" | sudo tee "$STATE_DIR/active-image-tag" >/dev/null

log "Canary deploy complete. Active tag: $TAG"
