#!/usr/bin/env bash
# Fail-closed VPS deploy helper for Keprix (used by deploy-keprix-production.sh).
#
# Primary production entrypoint:
#   bash scripts/deploy-keprix-production.sh
#
# This script is the low-level helper:
#   bash scripts/deploy-server.sh
#   bash scripts/deploy-server.sh --bootstrap --domain app.example.com
#   bash scripts/deploy-server.sh --ref v0.16.0 --profile compose
#   bash scripts/deploy-server.sh --profile systemd --skip-pull
#
# Exit non-zero on doctor / migrate / backup / restart / health failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BOOTSTRAP=0
SKIP_TESTS=0
SKIP_PULL=0
SKIP_MIGRATE=0
SKIP_BACKUP=0
PROFILE="${KEPRIX_DEPLOY_PROFILE:-compose}"  # compose | systemd
REF="${KEPRIX_DEPLOY_REF:-}"
DOMAIN="${KEPRIX_DOMAIN:-}"
PROXY="${KEPRIX_PROXY:-caddy}"  # caddy | nginx | none
KEPRIX_USER="${KEPRIX_DEPLOY_USER:-keprix}"
HEALTH_TIMEOUT="${KEPRIX_HEALTH_TIMEOUT:-120}"
BACKEND_PORT="${BACKEND_PORT:-3333}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

usage() {
  cat <<'EOF'
Usage: deploy-server.sh [options]

  --bootstrap          Install systemd unit, proxy config, firewall, timers
  --profile NAME       compose (default) | systemd
  --ref REF            git fetch + checkout tag/commit before deploy
  --domain HOST        Used for Caddy/nginx bootstrap substitution
  --proxy NAME         caddy | nginx | none (default: caddy)
  --skip-pull          Do not git fetch/checkout
  --skip-migrate       Skip Alembic (not recommended)
  --skip-backup        Skip pre-restart backup (not recommended)
  --skip-tests         Skip smoke tests
  -h, --help           Show help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --bootstrap) BOOTSTRAP=1; shift ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --proxy) PROXY="$2"; shift 2 ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    --skip-migrate) SKIP_MIGRATE=1; shift ;;
    --skip-backup) SKIP_BACKUP=1; shift ;;
    --skip-tests) SKIP_TESTS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ "$PROFILE" != "compose" ] && [ "$PROFILE" != "systemd" ]; then
  echo "Invalid --profile: $PROFILE (use compose|systemd)" >&2
  exit 2
fi

log() { printf '  %s\n' "$*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

py() {
  if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHONPATH="$ROOT/src" "$ROOT/.venv/bin/python" "$@"
  else
    PYTHONPATH="$ROOT/src" python3 "$@"
  fi
}

cli() {
  py -m keprix_cli.main "$@"
}

substitute_unit() {
  local src="$1" dest="$2"
  local home="${KEPRIX_HOME_OVERRIDE:-/home/${KEPRIX_USER}/.keprix}"
  sed \
    -e "s|@KEPRIX_ROOT@|$ROOT|g" \
    -e "s|@KEPRIX_USER@|$KEPRIX_USER|g" \
    -e "s|@KEPRIX_HOME@|$home|g" \
    "$src" >"$dest"
}

ensure_deploy_user() {
  if ! id -u "$KEPRIX_USER" >/dev/null 2>&1; then
    log "Creating system user $KEPRIX_USER"
    sudo useradd --system --create-home --home-dir "/home/$KEPRIX_USER" --shell /usr/sbin/nologin "$KEPRIX_USER" \
      || die "failed to create user $KEPRIX_USER"
  fi
  local home="/home/${KEPRIX_USER}/.keprix"
  sudo mkdir -p "$home/logs" "$ROOT/backups" "$ROOT/data"
  sudo chown -R "$KEPRIX_USER:$KEPRIX_USER" "$home" "$ROOT/backups" "$ROOT/data" || true
}

install_proxy() {
  [ -n "$DOMAIN" ] || die "--bootstrap with proxy requires --domain"
  case "$PROXY" in
    caddy)
      if ! command -v caddy >/dev/null 2>&1; then
        log "caddy not installed; writing /etc/caddy/Caddyfile for later"
      fi
      local tmp
      tmp="$(mktemp)"
      sed "s/app.example.com/$DOMAIN/g" "$ROOT/deploy/Caddyfile" >"$tmp"
      sudo mkdir -p /etc/caddy /var/log/caddy
      sudo cp "$tmp" /etc/caddy/Caddyfile
      rm -f "$tmp"
      if command -v caddy >/dev/null 2>&1; then
        sudo caddy validate --config /etc/caddy/Caddyfile || die "Caddyfile invalid"
        sudo systemctl enable --now caddy 2>/dev/null || true
        sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy || true
      fi
      ;;
    nginx)
      local tmp
      tmp="$(mktemp)"
      sed "s/app.example.com/$DOMAIN/g" "$ROOT/deploy/nginx.conf" >"$tmp"
      sudo cp "$tmp" /etc/nginx/sites-available/keprix
      sudo ln -sf /etc/nginx/sites-available/keprix /etc/nginx/sites-enabled/keprix
      rm -f "$tmp"
      if command -v nginx >/dev/null 2>&1; then
        sudo nginx -t || die "nginx config invalid"
        sudo systemctl reload nginx || die "nginx reload failed"
      fi
      ;;
    none) log "Skipping proxy install" ;;
    *) die "Unknown --proxy $PROXY" ;;
  esac
}

bootstrap() {
  log "[bootstrap] Installing VPS assets..."
  ensure_deploy_user
  if [ ! -f /etc/keprix.env ]; then
    local tmp
    tmp="$(mktemp)"
    sed "s/app.example.com/${DOMAIN:-app.example.com}/g" "$ROOT/deploy/keprix.env.example" >"$tmp"
    sudo cp "$tmp" /etc/keprix.env
    rm -f "$tmp"
    sudo chmod 0600 /etc/keprix.env
    sudo chown "root:$KEPRIX_USER" /etc/keprix.env
    log "Wrote /etc/keprix.env (fill secrets before go-live)"
  fi

  if [ "$PROFILE" = "systemd" ]; then
    local tmp_unit
    tmp_unit="$(mktemp)"
    substitute_unit "$ROOT/deploy/keprix.service" "$tmp_unit"
    sudo cp "$tmp_unit" /etc/systemd/system/keprix.service
    rm -f "$tmp_unit"
    sudo systemctl daemon-reload
    sudo systemctl enable keprix.service
    log "systemd unit keprix.service installed (binds 127.0.0.1:3333)"
  fi

  local tmp_backup tmp_timer tmp_logrotate
  tmp_backup="$(mktemp)"; tmp_timer="$(mktemp)"; tmp_logrotate="$(mktemp)"
  substitute_unit "$ROOT/deploy/keprix-backup.service" "$tmp_backup"
  cp "$ROOT/deploy/keprix-backup.timer" "$tmp_timer"
  substitute_unit "$ROOT/deploy/logrotate-keprix" "$tmp_logrotate"
  sudo cp "$tmp_backup" /etc/systemd/system/keprix-backup.service
  sudo cp "$tmp_timer" /etc/systemd/system/keprix-backup.timer
  sudo cp "$tmp_logrotate" /etc/logrotate.d/keprix
  sudo mkdir -p /etc/systemd/journald.conf.d
  sudo cp "$ROOT/deploy/journald-keprix.conf" /etc/systemd/journald.conf.d/keprix.conf
  rm -f "$tmp_backup" "$tmp_timer" "$tmp_logrotate"
  sudo systemctl daemon-reload
  sudo systemctl enable --now keprix-backup.timer
  sudo systemctl restart systemd-journald || true

  if [ "$PROXY" != "none" ]; then
    install_proxy
  fi

  if [ -x "$ROOT/scripts/configure-firewall.sh" ]; then
    bash "$ROOT/scripts/configure-firewall.sh" || die "firewall configure failed"
  fi
}

pull_release() {
  if [ "$SKIP_PULL" = "1" ]; then
    log "[1/7] Skipping pull"
    return 0
  fi
  log "[1/7] Updating source..."
  if [ ! -d "$ROOT/.git" ]; then
    log "Not a git checkout; skip pull (pin images/tags manually)"
    return 0
  fi
  git fetch --tags --prune origin
  if [ -n "$REF" ]; then
    git checkout --detach "$REF" || die "git checkout $REF failed"
    log "Checked out $REF"
  else
    local branch
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [ -n "$branch" ] && [ "$branch" != "HEAD" ]; then
      git pull --ff-only origin "$branch" || die "git pull failed"
    else
      log "Detached HEAD and no --ref; leave tree as-is"
    fi
  fi
  git rev-parse --short HEAD >"$ROOT/.deploy-revision" || true
}

doctor() {
  log "[2/7] Doctor..."
  cli doctor || die "doctor failed"
}

smoke() {
  if [ "$SKIP_TESTS" = "1" ]; then
    log "[3/7] Skipping smoke tests"
    return 0
  fi
  log "[3/7] Smoke tests..."
  if [ -f tests/agent_os/test_phase5_polish.py ]; then
    py -m pytest tests/agent_os/test_phase5_polish.py -q --tb=line \
      || die "smoke tests failed"
  else
    py -c "from keprix.agent_os.token_playbook import playbook_status; assert playbook_status()['technique_count']==10"
  fi
}

migrate() {
  if [ "$SKIP_MIGRATE" = "1" ]; then
    log "[migrate] Skipping migrations"
    return 0
  fi
  log "[migrate] Alembic upgrade head..."
  if [ "$PROFILE" = "compose" ] && command -v docker >/dev/null 2>&1; then
    # Ensure DB is up before migrating.
    (cd "$ROOT/docker" && docker compose -f docker-compose.yml up -d postgres redis) || die "failed to start postgres/redis"
    local deadline=$((SECONDS + 60))
    until docker compose -f "$ROOT/docker/docker-compose.yml" exec -T postgres pg_isready -U keprix -d keprix >/dev/null 2>&1; do
      [ "$SECONDS" -lt "$deadline" ] || die "postgres not ready for migrate"
      sleep 2
    done
    if docker compose -f "$ROOT/docker/docker-compose.yml" ps --status running 2>/dev/null | grep -q keprix-backend; then
      docker compose -f "$ROOT/docker/docker-compose.yml" exec -T keprix-backend \
        alembic upgrade head || die "alembic upgrade failed in container"
      return 0
    fi
    # Backend not running yet: run alembic from a one-shot container on the network.
    docker compose -f "$ROOT/docker/docker-compose.yml" run --rm --no-deps \
      -e KEPRIX_DATABASE_URL="postgresql+asyncpg://keprix:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}@postgres:5432/keprix" \
      keprix-backend alembic upgrade head || die "alembic one-shot migrate failed"
    return 0
  fi
  if [ -x "$ROOT/.venv/bin/alembic" ]; then
    (cd "$ROOT" && "$ROOT/.venv/bin/alembic" upgrade head) || die "alembic upgrade failed"
  else
    py -m alembic upgrade head || die "alembic upgrade failed"
  fi
}

backup() {
  if [ "$SKIP_BACKUP" = "1" ]; then
    log "[backup] Skipping backup"
    return 0
  fi
  log "[backup] Pre-restart backup..."
  mkdir -p "$ROOT/backups"
  if [ -x "$ROOT/scripts/keprix-backup" ]; then
    "$ROOT/scripts/keprix-backup" snapshot --out "$ROOT/backups" || die "keprix-backup failed"
  else
    cli backup --quick || die "backup failed"
  fi
}

restart_stack() {
  log "[restart] Restart ($PROFILE)..."
  if [ "$PROFILE" = "compose" ]; then
    local compose="$ROOT/docker/docker-compose.yml"
    local prod="$ROOT/docker/docker-compose.prod.yml"
    [ -f "$compose" ] || die "missing $compose"
    if [ -f "$prod" ]; then
      (cd "$ROOT/docker" && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build) \
        || die "docker compose up failed"
    else
      (cd "$ROOT/docker" && docker compose up -d --build) || die "docker compose up failed"
    fi
    return 0
  fi
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^keprix.service'; then
    sudo systemctl restart keprix.service || die "systemctl restart keprix failed"
  else
    die "keprix.service not installed; run with --bootstrap --profile systemd"
  fi
}

wait_healthy() {
  log "[7/7] Health gate (timeout ${HEALTH_TIMEOUT}s)..."
  local deadline=$((SECONDS + HEALTH_TIMEOUT))
  local ok=0
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 2
  done
  [ "$ok" = "1" ] || die "backend health failed on :${BACKEND_PORT}"

  if [ "$PROFILE" = "compose" ]; then
    if [ -x "$ROOT/scripts/check-health.sh" ]; then
      bash "$ROOT/scripts/check-health.sh" || die "check-health.sh failed"
    fi
    # Frontend optional but expected for compose profile
    if ! curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then
      log "WARNING: frontend :${FRONTEND_PORT} not responding yet (backend OK)"
    fi
  fi
  curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health"
  echo
}

echo "Keprix server deploy"
echo "  root: $ROOT"
echo "  profile: $PROFILE"
[ -n "$REF" ] && echo "  ref: $REF"

[ "$BOOTSTRAP" = "1" ] && bootstrap
pull_release
doctor
smoke
backup
# Compose: migrate after postgres is up (migrate brings postgres/redis up first).
# Then restart full stack so app containers pick up schema.
migrate
restart_stack
wait_healthy

echo "Done. Deploy succeeded."
echo "Rollback: checkout previous tag, then re-run this script --skip-pull (or pin KEPRIX_IMAGE_TAG)."
