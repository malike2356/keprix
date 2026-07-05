#!/usr/bin/env bash
# keprix marketing site deploy script
# Deploys marketing/sites/keprix/ to the configured target via rsync over SSH.
#
# Usage:
#   ./scripts/deploy.sh
#
# Required environment variables (set in .env or export before running):
#   KEPRIX_DEPLOY_HOST   - SSH host (e.g., user@203.0.113.10)
#   KEPRIX_DEPLOY_PATH   - Absolute path on server (e.g., /var/www/keprixai.uk)
#   KEPRIX_SSH_KEY       - Path to SSH private key (optional; uses ssh-agent if not set)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [[ -f "${SITE_DIR}/../.env" ]]; then
  # shellcheck disable=SC1091
  source "${SITE_DIR}/../.env"
fi

DEPLOY_HOST="${KEPRIX_DEPLOY_HOST:-}"
DEPLOY_PATH="${KEPRIX_DEPLOY_PATH:-}"
SSH_KEY="${KEPRIX_SSH_KEY:-}"

if [[ -z "${DEPLOY_HOST}" ]]; then
  echo "ERROR: KEPRIX_DEPLOY_HOST is not set."
  exit 1
fi

if [[ -z "${DEPLOY_PATH}" ]]; then
  echo "ERROR: KEPRIX_DEPLOY_PATH is not set."
  exit 1
fi

# Run validation before deploying
echo "Running pre-deploy validation..."
"${SCRIPT_DIR}/validate-site.sh"

echo "Deploying keprix marketing site to ${DEPLOY_HOST}:${DEPLOY_PATH} ..."

SSH_OPTS="-o StrictHostKeyChecking=accept-new"
if [[ -n "${SSH_KEY}" ]]; then
  SSH_OPTS="${SSH_OPTS} -i ${SSH_KEY}"
fi

rsync \
  --archive \
  --compress \
  --delete \
  --verbose \
  --exclude="scripts/" \
  --exclude="*.sh" \
  --exclude=".DS_Store" \
  --exclude="*.bak" \
  -e "ssh ${SSH_OPTS}" \
  "${SITE_DIR}/" \
  "${DEPLOY_HOST}:${DEPLOY_PATH}/"

echo "Deploy complete."
