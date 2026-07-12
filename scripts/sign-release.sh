#!/usr/bin/env bash
# Detach-sign dist/SHA256SUMS with GPG (operator key).
# Usage:
#   GPG_KEY_ID=... bash scripts/sign-release.sh
#   bash scripts/sign-release.sh --key-id ABCD1234
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
KEY_ID="${GPG_KEY_ID:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --key-id) KEY_ID="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: GPG_KEY_ID=... $0 [--key-id ID]"
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

[ -f "$DIST/SHA256SUMS" ] || {
  echo "Missing $DIST/SHA256SUMS; run build-release-artifact.sh first" >&2
  exit 1
}

if ! command -v gpg >/dev/null 2>&1; then
  echo "gpg is required" >&2
  exit 1
fi

ARGS=(--detach-sign --armor --output "$DIST/SHA256SUMS.asc")
if [ -n "$KEY_ID" ]; then
  ARGS+=(--local-user "$KEY_ID")
fi

gpg "${ARGS[@]}" "$DIST/SHA256SUMS"
echo "Signed: $DIST/SHA256SUMS.asc"
echo "Publish: tarball + SHA256SUMS + SHA256SUMS.asc (+ export pubkey to deploy/keys/)"
