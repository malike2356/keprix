#!/usr/bin/env bash
# Optional AWS EC2 bootstrap helper (not the primary production path).
# Prints a hardened remote procedure; does not curl|bash install.sh.
set -euo pipefail

DOMAIN=""
EMAIL=""
SIZE="t3.medium"
KEY_NAME=""
REF="main"

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    --key-name) KEY_NAME="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

[ -n "$KEY_NAME" ] || { echo "--key-name (EC2 key pair) is required" >&2; exit 2; }
[ -n "$DOMAIN" ] || { echo "--domain is required" >&2; exit 2; }
[ -n "$EMAIL" ] || { echo "--email is required" >&2; exit 2; }

echo "Launching Ubuntu 22.04 instance ($SIZE) with key $KEY_NAME..."
INSTANCE_ID="$(aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --instance-type "$SIZE" \
  --key-name "$KEY_NAME" \
  --count 1 \
  --query 'Instances[0].InstanceId' \
  --output text)"

echo "Instance: $INSTANCE_ID (waiting for running state)"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

cat <<MSG
Public IP: $PUBLIC_IP

On the instance (SSH with your key), run a verified local install; do not curl|bash:

  sudo apt-get update && sudo apt-get install -y git
  git clone --branch ${REF} https://github.com/malike2356/keprix.git /opt/keprix
  cd /opt/keprix
  bash scripts/generate-production-env.sh --domain https://${DOMAIN} --force
  bash scripts/configure-firewall.sh
  bash scripts/deploy-keprix-production.sh --bootstrap --domain ${DOMAIN} --skip-scout

Point DNS ${DOMAIN} → ${PUBLIC_IP}. ACME email: ${EMAIL}
Primary docs: docs/operations/vps-deploy.md
MSG
