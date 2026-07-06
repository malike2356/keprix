#!/usr/bin/env bash
# Bootstrap Keprix on DigitalOcean (requires doctl configured)
set -euo pipefail

DOMAIN=""
EMAIL=""
SIZE="s-2vcpu-4gb"

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if ! command -v doctl >/dev/null 2>&1; then
  echo "doctl is required" >&2
  exit 1
fi

DROPLET_ID="$(doctl compute droplet create keprix \
  --size "$SIZE" \
  --image ubuntu-22-04-x64 \
  --region lon1 \
  --wait \
  --format ID --no-header)"

IP="$(doctl compute droplet get "$DROPLET_ID" --format PublicIPv4 --no-header)"
echo "Droplet $DROPLET_ID at $IP"
echo "SSH in and run:"
echo "  curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash"
if [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  echo "Then configure SSL for $DOMAIN with certbot using $EMAIL"
fi
