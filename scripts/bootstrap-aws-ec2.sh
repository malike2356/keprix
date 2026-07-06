#!/usr/bin/env bash
# Bootstrap Keprix on AWS EC2 (requires AWS CLI configured)
set -euo pipefail

DOMAIN=""
EMAIL=""
SIZE="t3.medium"

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

echo "Launching Ubuntu 22.04 instance ($SIZE)..."
INSTANCE_ID="$(aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --instance-type "$SIZE" \
  --count 1 \
  --query 'Instances[0].InstanceId' \
  --output text)"

echo "Instance: $INSTANCE_ID (waiting for running state)"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

echo "Run on the instance:"
echo "  curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash"
if [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  echo "  sudo apt-get update && sudo apt-get install -y certbot"
  echo "  sudo certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos"
fi
echo "Public IP: $PUBLIC_IP"
