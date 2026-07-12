#!/usr/bin/env bash
# Build a releasable source artifact + SHA256SUMS (no secrets).
# Usage:
#   bash scripts/build-release-artifact.sh
#   bash scripts/build-release-artifact.sh --version v0.16.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
if [ "${1:-}" = "--version" ]; then
  VERSION="$2"
fi
if [ -z "$VERSION" ]; then
  if [ -d .git ]; then
    VERSION="$(git describe --tags --always --dirty 2>/dev/null || true)"
  fi
  VERSION="${VERSION:-dev}"
fi
VERSION="${VERSION#v}"
NAME="keprix-v${VERSION}"
DIST="$ROOT/dist"
OUT="$DIST/${NAME}.tar.gz"

mkdir -p "$DIST"
rm -f "$OUT" "$DIST/SHA256SUMS" "$DIST/SHA256SUMS.asc"

# Exclude bulky / secret paths
tar --exclude='.git' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/.next' \
  --exclude='dist' \
  --exclude='backups' \
  --exclude='data' \
  --exclude='.env' \
  --exclude='**/__pycache__' \
  --exclude='1st-plan/competitor-research' \
  -czf "$OUT" \
  -C "$ROOT" \
  --transform "s,^,${NAME}/," \
  src frontend docker deploy scripts docs migrations pyproject.toml \
  fly.toml fly.fullstack.toml fly.backend-only.toml \
  README.md LICENSE CHANGELOG.md 2>/dev/null \
  || tar --exclude='.git' --exclude='.venv' --exclude='node_modules' \
       --exclude='frontend/node_modules' --exclude='frontend/.next' \
       --exclude='dist' --exclude='.env' --exclude='**/__pycache__' \
       -czf "$OUT" -C "$ROOT" \
       --transform "s,^,${NAME}/," \
       src frontend docker deploy scripts docs migrations pyproject.toml fly.toml

(
  cd "$DIST"
  sha256sum "$(basename "$OUT")" > SHA256SUMS
)

echo "Built $OUT"
echo "Checksums: $DIST/SHA256SUMS"
echo "Next: bash scripts/sign-release.sh"
