#!/bin/sh
set -eu

DATA_DIR="${KEPRIX_DATA_DIR:-/data/keprix}"
HOME_DIR="${KEPRIX_HOME:-/home/keprix/.keprix}"

# Accept PUID/PGID aliases (LinuxServer / NAS convention). See stage2-hook.sh.
KEPRIX_UID="${KEPRIX_UID:-${PUID:-}}"
KEPRIX_GID="${KEPRIX_GID:-${PGID:-}}"

validate_uid_gid() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) [ "$1" -ge 0 ] && [ "$1" -le 65535 ]
  esac
}

# Remap container keprix to the host bind-mount owner. Without this, a host
# ~/.keprix at mode 0700 (UID 1000) is unreadable by image user keprix (999)
# and Brain / workspace APIs fail with [Errno 13] Permission denied.
if [ -n "${KEPRIX_UID}" ] && validate_uid_gid "$KEPRIX_UID"; then
  current_uid="$(id -u keprix 2>/dev/null || echo "")"
  if [ -n "$current_uid" ] && [ "$KEPRIX_UID" != "$current_uid" ]; then
    echo "[entrypoint] Changing keprix UID to $KEPRIX_UID"
    usermod -u "$KEPRIX_UID" keprix
  fi
fi
if [ -n "${KEPRIX_GID}" ] && validate_uid_gid "$KEPRIX_GID"; then
  current_gid="$(id -g keprix 2>/dev/null || echo "")"
  if [ -n "$current_gid" ] && [ "$KEPRIX_GID" != "$current_gid" ]; then
    echo "[entrypoint] Changing keprix GID to $KEPRIX_GID"
    groupmod -o -g "$KEPRIX_GID" keprix 2>/dev/null || true
  fi
fi

mkdir -p "$DATA_DIR" "$HOME_DIR"
# DATA_DIR is container-local; safe to own.
chown -R keprix:keprix "$DATA_DIR" 2>/dev/null || true

# Never chown a host bind-mounted KEPRIX_HOME. Doing so flips ~/.keprix to the
# container uid and breaks the desktop app (EACCES mkdir .../logs).
if mountpoint -q "$HOME_DIR" 2>/dev/null; then
  :
else
  chown -R keprix:keprix "$HOME_DIR" 2>/dev/null || true
fi

# Ensure the non-mounted home dir itself is reachable after UID remap.
chown keprix:keprix /home/keprix 2>/dev/null || true

# Apply the versioned database schema before starting the API. The Contabo
# application compose has one backend replica, so startup migration is the
# authoritative release gate and prevents background jobs from querying tables
# that have not been created yet. Operators can disable this only for a
# deliberate external migration workflow.
if [ "${KEPRIX_RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] Applying database migrations"
  gosu keprix alembic upgrade head
fi

exec gosu keprix "$@"
