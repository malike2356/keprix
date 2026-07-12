#!/usr/bin/env bash
# Configure host firewall for a public Keprix VPS.
# Allows: SSH (current port), HTTP, HTTPS. Denies other inbound by default.
set -euo pipefail

SSH_PORT="${SSH_PORT:-22}"

if ! command -v ufw >/dev/null 2>&1; then
  echo "ufw not installed; installing..." >&2
  if command -v apt-get >/dev/null 2>&1; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ufw
  else
    echo "Install ufw manually, then re-run." >&2
    exit 1
  fi
fi

echo "Configuring UFW (SSH ${SSH_PORT}, 80, 443)..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow "${SSH_PORT}/tcp" comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
# Never expose Postgres/Redis/backend/frontend publicly when behind Caddy/nginx.
sudo ufw --force enable
sudo ufw status verbose
echo "Firewall enabled. Keep app binds on 127.0.0.1."
