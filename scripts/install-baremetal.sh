#!/usr/bin/env bash
# Bare-metal install (no Docker). Requires sudo for system packages on Linux.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo "==> $*"; }

require_python() {
  if ! command -v python3.11 >/dev/null 2>&1 && ! python3 -c 'import sys; exit(0 if sys.version_info >= (3,11) else 1)'; then
    log "Python 3.11+ required. On Ubuntu: sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.11 python3.11-venv"
    exit 1
  fi
}

install_node() {
  if command -v node >/dev/null 2>&1 && node -v | grep -q '^v22'; then
    return 0
  fi
  echo "Install Node.js 22+ (recommended: nvm) https://nodejs.org/"
}

warn() { echo "WARNING: $*" >&2; }

install_postgres_redis() {
  log "Ensure PostgreSQL 16 and Redis 7 are installed and running"
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
}

main() {
  require_python
  install_node
  install_postgres_redis
  install_uv
  bash "$ROOT/scripts/install.sh"
  if command -v pnpm >/dev/null 2>&1; then
  (cd "$ROOT/frontend" && pnpm install && pnpm build) || warn "Frontend build skipped"
  fi
  log "Bare-metal bootstrap complete. Configure systemd units for production."
}

main "$@"
