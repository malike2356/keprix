#!/usr/bin/env bash
# Verify a release artifact against SHA256SUMS (+ optional GPG signature).
# Usage:
#   bash scripts/verify-release.sh dist/keprix-v0.16.0.tar.gz
#   bash scripts/verify-release.sh --dir dist
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=""
DIR=""
PUBKEY="${KEPRIX_RELEASE_PUBKEY:-$ROOT/deploy/keys/keprix-release.gpg.asc}"
REQUIRE_SIG="${KEPRIX_REQUIRE_RELEASE_SIG:-1}"

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --pubkey) PUBKEY="$2"; shift 2 ;;
    --allow-unsigned) REQUIRE_SIG=0; shift ;;
    -h|--help)
      echo "Usage: $0 PATH.tar.gz | --dir dist [--pubkey FILE] [--allow-unsigned]"
      exit 0
      ;;
    *) TARGET="$1"; shift ;;
  esac
done

if [ -n "$DIR" ]; then
  TARGET="$(ls -1 "$DIR"/keprix-v*.tar.gz 2>/dev/null | head -1 || true)"
  SUMS="$DIR/SHA256SUMS"
  SIG="$DIR/SHA256SUMS.asc"
else
  [ -n "$TARGET" ] || { echo "artifact path required" >&2; exit 2; }
  DIR="$(cd "$(dirname "$TARGET")" && pwd)"
  TARGET="$DIR/$(basename "$TARGET")"
  SUMS="$DIR/SHA256SUMS"
  SIG="$DIR/SHA256SUMS.asc"
fi

[ -f "$TARGET" ] || { echo "Missing artifact: $TARGET" >&2; exit 1; }
[ -f "$SUMS" ] || { echo "Missing $SUMS" >&2; exit 1; }

echo "Verifying checksum for $(basename "$TARGET")..."
(
  cd "$DIR"
  sha256sum -c SHA256SUMS --ignore-missing
)

if [ -f "$SIG" ]; then
  if ! command -v gpg >/dev/null 2>&1; then
    echo "gpg required to verify signature" >&2
    exit 1
  fi
  if [ -f "$PUBKEY" ]; then
    GNUPGHOME="$(mktemp -d)"
    export GNUPGHOME
    trap 'rm -rf "$GNUPGHOME"' EXIT
    gpg --import "$PUBKEY" >/dev/null 2>&1
  fi
  gpg --verify "$SIG" "$SUMS"
  echo "GPG signature OK"
elif [ "$REQUIRE_SIG" = "1" ]; then
  echo "Missing $SIG and KEPRIX_REQUIRE_RELEASE_SIG=1" >&2
  exit 1
else
  echo "WARNING: unsigned release accepted (--allow-unsigned)"
fi

echo "Verified: $TARGET"
