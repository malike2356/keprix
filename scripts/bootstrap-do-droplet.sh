#!/usr/bin/env bash
# Real DigitalOcean droplet bootstrap for Keprix.
# Requires: doctl authenticated, SSH key registered with DO.
#
# Does NOT use curl|bash install. Cloud-init:
#   apt packages (docker, caddy, ufw) → git clone pinned ref →
#   generate secrets → firewall → compose production deploy.
#
# Usage:
#   bash scripts/bootstrap-do-droplet.sh \
#     --domain app.example.com \
#     --email you@example.com \
#     --ssh-key "my-laptop" \
#     --ref v0.16.0
set -euo pipefail

DOMAIN=""
EMAIL=""
SIZE="s-2vcpu-4gb"
REGION="lon1"
SSH_KEY=""
REF="main"
REPO_URL="${KEPRIX_REPO_URL:-https://github.com/malike2356/keprix.git}"
DROPLET_NAME=""

usage() {
  cat <<'EOF'
Usage: bootstrap-do-droplet.sh --domain HOST --email EMAIL --ssh-key NAME_OR_ID [options]

Required:
  --domain HOST          Public hostname (DNS must point here after create)
  --email EMAIL          ACME / operator contact for Caddy
  --ssh-key NAME_OR_ID   DigitalOcean SSH key name or ID (doctl compute ssh-key list)

Optional:
  --ref REF              Git tag/branch to clone (default: main)
  --size SIZE            Droplet size (default: s-2vcpu-4gb)
  --region REGION        DO region (default: lon1)
  --name NAME            Droplet name (default: keprix-<domain>)
  --repo-url URL         Git remote (default: official keprix repo)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --ssh-key) SSH_KEY="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --name) DROPLET_NAME="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$DOMAIN" ] || { echo "--domain is required" >&2; exit 2; }
[ -n "$EMAIL" ] || { echo "--email is required" >&2; exit 2; }
[ -n "$SSH_KEY" ] || { echo "--ssh-key is required (doctl compute ssh-key list)" >&2; exit 2; }

if ! command -v doctl >/dev/null 2>&1; then
  echo "doctl is required" >&2
  exit 1
fi

DROPLET_NAME="${DROPLET_NAME:-keprix-${DOMAIN//./-}}"

USER_DATA="$(mktemp)"
trap 'rm -f "$USER_DATA"' EXIT

cat >"$USER_DATA" <<EOF
#!/bin/bash
set -euo pipefail
FLAG=/var/lib/keprix-bootstrap.done
if [ -f "\$FLAG" ]; then exit 0; fi
export DEBIAN_FRONTEND=noninteractive
export KEPRIX_SHOW_ADMIN_PASSWORD=0

apt-get update -y
apt-get install -y apt-transport-https ca-certificates curl gnupg git ufw \\
  python3 python3-venv python3-pip debian-keyring debian-archive-keyring

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o /etc/apt/keyrings/caddy.asc
chmod a+r /etc/apt/keyrings/caddy.asc
echo "deb [signed-by=/etc/apt/keyrings/caddy.asc] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y
apt-get install -y caddy

mkdir -p /opt/keprix
if [ ! -d /opt/keprix/.git ]; then
  git clone --depth 1 --branch "${REF}" "${REPO_URL}" /opt/keprix
fi
cd /opt/keprix
git fetch --tags origin || true
git checkout "${REF}" || git checkout -B "${REF}" "origin/${REF}" || true

bash scripts/generate-production-env.sh --domain "https://${DOMAIN}" --force
grep -q '^KEPRIX_ACME_EMAIL=' .env || echo "KEPRIX_ACME_EMAIL=${EMAIL}" >> .env

bash scripts/configure-firewall.sh
bash scripts/deploy-server.sh --bootstrap --domain "${DOMAIN}" --profile compose --proxy caddy --skip-tests

systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy

touch "\$FLAG"
echo "Keprix bootstrap complete for ${DOMAIN}" | tee /var/log/keprix-bootstrap.log
EOF

echo "Creating droplet ${DROPLET_NAME} (ssh-key=${SSH_KEY}, ref=${REF})..."
DROPLET_ID="$(doctl compute droplet create "$DROPLET_NAME" \
  --size "$SIZE" \
  --image ubuntu-22-04-x64 \
  --region "$REGION" \
  --ssh-keys "$SSH_KEY" \
  --user-data-file "$USER_DATA" \
  --wait \
  --format ID --no-header)"

IP="$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)"

cat <<MSG
Droplet $DROPLET_ID ready at $IP

Next:
  1. Point DNS A record for ${DOMAIN} → ${IP}
  2. Wait for cloud-init (ssh root@${IP} 'tail -f /var/log/keprix-bootstrap.log')
  3. Confirm: curl -fsS https://${DOMAIN}/api/health

Caddy obtains certificates automatically once DNS resolves.
ACME contact: ${EMAIL}
Pinned ref: ${REF}

Ongoing deploys on host: bash scripts/deploy-keprix-production.sh
MSG
