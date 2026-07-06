#!/usr/bin/env bash
# Keprix installer (Docker recommended). Idempotent: re-run shows status / upgrade.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_HOME="${KEPRIX_INSTALL_HOME:-$HOME/keprix}"
ENV_FILE="${KEPRIX_ENV_FILE:-$ROOT/.env}"
COMPOSE_FILE="${KEPRIX_COMPOSE_FILE:-$ROOT/docker/docker-compose.yml}"
PYTHON="${PYTHON:-python3}"
VENV="${KEPRIX_VENV:-$ROOT/.venv}"
STATE_FILE="$INSTALL_HOME/install-state.json"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

log() { echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }

detect_os() {
  case "$(uname -s)" in
    Linux) echo "linux" ;;
    Darwin) echo "macos" ;;
    *) echo "unknown" ;;
  esac
}

check_resources() {
  local mem_kb disk_kb cpus
  mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
  disk_kb="$(df -k "$INSTALL_HOME" 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
  cpus="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)"
  if [ "$mem_kb" -gt 0 ] && [ "$mem_kb" -lt 2000000 ]; then
    warn "Less than 2 GB RAM detected"
  fi
  if [ "$disk_kb" -gt 0 ] && [ "$disk_kb" -lt 10485760 ]; then
    warn "Less than 10 GB free disk detected"
  fi
  if [ "$cpus" -lt 2 ]; then
    warn "Less than 2 CPU cores detected"
  fi
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    return 0
  fi
  warn "Docker or Docker Compose not found."
  echo "Install Docker: https://docs.docker.com/engine/install/"
  if [ "${KEPRIX_AUTO_INSTALL_DOCKER:-}" = "1" ]; then
    curl -fsSL https://get.docker.com | sh
  else
    read -r -p "Attempt automatic Docker install? [y/N] " answer || answer="n"
    if [[ "$answer" =~ ^[Yy] ]]; then
      curl -fsSL https://get.docker.com | sh
    else
      exit 1
    fi
  fi
}

bootstrap_files() {
  mkdir -p "$INSTALL_HOME"
  if [ ! -f "$COMPOSE_FILE" ]; then
    log "Downloading docker-compose.yml into $INSTALL_HOME"
    mkdir -p "$INSTALL_HOME/docker"
    curl -fsSL "https://raw.githubusercontent.com/malike2356/keprix/main/docker/docker-compose.yml" \
      -o "$INSTALL_HOME/docker/docker-compose.yml"
    COMPOSE_FILE="$INSTALL_HOME/docker/docker-compose.yml"
  fi
  if [ ! -f "$ENV_FILE" ] && [ -f "$ROOT/.env.example" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
  elif [ ! -f "$ENV_FILE" ]; then
    curl -fsSL "https://raw.githubusercontent.com/malike2356/keprix/main/.env.example" -o "$ENV_FILE"
  fi
}

run_wizard_if_needed() {
  if [ -f "$STATE_FILE" ] && [ -f "$ENV_FILE" ] && [ "${KEPRIX_FORCE_WIZARD:-}" != "1" ]; then
    log "Existing install detected at $INSTALL_HOME"
    return 0
  fi
  log "Running setup wizard"
  if [ -x "$VENV/bin/python" ]; then
    KEPRIX_ENV_FILE="$ENV_FILE" "$VENV/bin/python" "$ROOT/scripts/wizard.py"
  else
    KEPRIX_ENV_FILE="$ENV_FILE" "$PYTHON" "$ROOT/scripts/wizard.py"
  fi
}

ensure_venv() {
  if [ ! -d "$VENV" ]; then
    log "Creating virtualenv at $VENV"
    "$PYTHON" -m venv "$VENV"
  fi
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -q -U pip wheel
  pip install -q -e "$ROOT"
}

start_stack() {
  if [ -f "$COMPOSE_FILE" ]; then
    log "Starting Docker Compose stack"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
  else
    warn "No compose file; start API manually with: keprix start"
  fi
}

wait_health() {
  log "Waiting for health checks (up to 120s)"
  if [ -x "$VENV/bin/python" ]; then
    KEPRIX_ENV_FILE="$ENV_FILE" "$VENV/bin/python" -c "
from keprix.installer.health import wait_for_healthy
raise SystemExit(0 if wait_for_healthy(timeout_seconds=120) else 1)
"
    return $?
  fi
  bash "$ROOT/scripts/check-health.sh"
}

print_success() {
  local admin_pass=""
  if [ -f "$ENV_FILE" ]; then
    admin_pass="$(grep '^KEPRIX_ADMIN_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)"
  fi
  echo ""
  echo "Keprix is ready at http://localhost:${FRONTEND_PORT}"
  if [ -n "$admin_pass" ] && [ "${KEPRIX_SHOW_ADMIN_PASSWORD:-1}" = "1" ]; then
    echo "Admin password (shown once): $admin_pass"
  fi
  echo "CLI: keprix status | keprix health | keprix update"
}

main() {
  log "Keprix installer (OS: $(detect_os))"
  check_resources
  ensure_docker
  bootstrap_files
  ensure_venv
  run_wizard_if_needed
  start_stack

  if wait_health; then
    print_success
    exit 0
  fi

  warn "Health checks did not all pass within timeout"
  print_success
  exit 1
}

main "$@"
