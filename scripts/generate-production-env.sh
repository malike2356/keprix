#!/usr/bin/env bash
# Generate production secrets into .env (or a target file). Never prints secret values.
# Usage:
#   bash scripts/generate-production-env.sh
#   bash scripts/generate-production-env.sh --env-file /path/to/.env --domain https://app.example.com
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
DOMAIN=""
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--env-file PATH] [--domain https://app.example.com] [--force]"
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

rand() { openssl rand -base64 "$1" | tr -d '\n'; }

if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ROOT/.env.example" ]; then
    cp "$ROOT/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
  else
    echo "Missing $ENV_FILE and .env.example" >&2
    exit 1
  fi
fi

set_kv() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    local current
    current="$(grep "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2-)"
    if [ "$FORCE" != "1" ] && [ -n "$current" ] \
      && [ "$current" != "changeme" ] \
      && [[ "$current" != GENERATE_RANDOM_* ]] \
      && [[ "$current" != REPLACE_ME* ]] \
      && [[ "$current" != change_me* ]]; then
      return 0
    fi
    # portable in-place replace
    local tmp
    tmp="$(mktemp)"
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k{$0=k"="v} {print}' "$ENV_FILE" >"$tmp"
    mv "$tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
  fi
}

POSTGRES_PW="$(rand 24)"
REDIS_PW="$(rand 24)"
JWT="$(rand 64)"
SESSION="$(rand 64)"
VAULT="$(rand 32)"
HANDOFF="$(rand 32)"
ADMIN_PW="$(rand 24)"

set_kv POSTGRES_PASSWORD "$POSTGRES_PW"
set_kv REDIS_PASSWORD "$REDIS_PW"
set_kv KEPRIX_JWT_SECRET "$JWT"
set_kv KEPRIX_SESSION_SECRET "$SESSION"
set_kv KEPRIX_VAULT_KEY "$VAULT"
set_kv KEPRIX_HANDOFF_SECRET "$HANDOFF"
set_kv KEPRIX_DATABASE_URL "postgresql+asyncpg://keprix:${POSTGRES_PW}@postgres:5432/keprix"
set_kv KEPRIX_REDIS_URL "redis://:${REDIS_PW}@redis:6379"
set_kv KEPRIX_SHOW_ADMIN_PASSWORD "0"
set_kv KEPRIX_TRUSTED_PROXIES "127.0.0.1,::1"
set_kv KEPRIX_ADMIN_PASSWORD "$ADMIN_PW"

if [ -n "$DOMAIN" ]; then
  set_kv KEPRIX_INSTANCE_URL "$DOMAIN"
  set_kv KEPRIX_ALLOWED_ORIGINS "$DOMAIN"
  set_kv KEPRIX_FRONTEND_URL "$DOMAIN"
fi

chmod 600 "$ENV_FILE"
echo "Updated $ENV_FILE with strong secrets (values not printed)."
echo "Set KEPRIX_ADMIN_PASSWORD via your secret store if you need to rotate the generated admin password."
echo "Next: review KEPRIX_ALLOWED_ORIGINS / KEPRIX_INSTANCE_URL, then deploy."
