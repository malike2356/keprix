#!/usr/bin/env bash
# Optional managed-hosting helpers (not the primary production path).
# Primary: scripts/deploy-keprix-production.sh (Compose + Caddy).
#
#   bash scripts/deploy-managed.sh fly
#   bash scripts/deploy-managed.sh droplet --domain example.com --email you@example.com --ssh-key mykey
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-}"
shift || true

case "$MODE" in
  fly|flyio)
    cat <<'EOF'
Fly is an optional helper, not one-click production.

Fullstack (frontend + backend + volume): fly.fullstack.toml / fly.toml
Requires BEFORE deploy:
  fly apps create keprix
  fly postgres create && fly postgres attach ...
  fly redis create  (or set KEPRIX_REDIS_URL)
  fly volumes create keprix_data --size 10
  fly secrets set KEPRIX_JWT_SECRET=... KEPRIX_SESSION_SECRET=... KEPRIX_VAULT_KEY=...

Backend-only sketch (no persistence): fly.backend-only.toml

Prefer VPS: bash scripts/deploy-keprix-production.sh
EOF
    if ! command -v flyctl >/dev/null 2>&1 && ! command -v fly >/dev/null 2>&1; then
      echo "Install flyctl first: https://fly.io/docs/hands-on/install-flyctl/" >&2
      exit 1
    fi
    FLY="$(command -v flyctl || command -v fly)"
    CONFIG="${KEPRIX_FLY_CONFIG:-fly.fullstack.toml}"
    echo "Deploying with $CONFIG ..."
    "$FLY" deploy -c "$CONFIG"
    ;;
  droplet|do)
    # Delegate to real bootstrap (SSH keys, UFW, Caddy; no curl|bash install).
    exec bash "$ROOT/scripts/bootstrap-do-droplet.sh" "$@"
    ;;
  *)
    echo "Usage: $0 {fly|droplet} [options]" >&2
    echo "Primary production path: bash scripts/deploy-keprix-production.sh" >&2
    exit 2
    ;;
esac
