#!/usr/bin/env bash
# Verified install: artifact + checksum (+ GPG) then local install.sh.
# Does not use curl|bash as the only trust boundary.
#
#   bash scripts/install-verified.sh --version v0.16.0
#   bash scripts/install-verified.sh --artifact /path/keprix-v0.16.0.tar.gz
#   bash scripts/install-verified.sh --from-git --ref v0.16.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION=""
ARTIFACT=""
ARTIFACT_DIR=""
FROM_GIT=0
REF=""
BASE_URL="${KEPRIX_RELEASE_BASE_URL:-https://github.com/malike2356/keprix/releases/download}"
REPO_URL="${KEPRIX_REPO_URL:-https://github.com/malike2356/keprix.git}"
WORKDIR="${TMPDIR:-/tmp}/keprix-verified-$$"

usage() {
  cat <<'EOF'
Usage:
  install-verified.sh --version vX.Y.Z
  install-verified.sh --artifact path/to/keprix-vX.Y.Z.tar.gz
  install-verified.sh --from-git --ref vX.Y.Z
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --artifact) ARTIFACT="$2"; shift 2 ;;
    --from-git) FROM_GIT=1; shift ;;
    --ref) REF="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT
mkdir -p "$WORKDIR"

if [ "$FROM_GIT" = "1" ]; then
  REF="${REF:-$VERSION}"
  [ -n "$REF" ] || { echo "--ref or --version required with --from-git" >&2; exit 2; }
  echo "Cloning pinned ref $REF..."
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$WORKDIR/src"
  git -C "$WORKDIR/src" verify-tag "$REF" 2>/dev/null \
    || echo "NOTE: tag $REF is not GPG-verified (unsigned or key missing); pinned ref still used"
  exec bash "$WORKDIR/src/scripts/install.sh"
fi

if [ -n "$ARTIFACT" ]; then
  [ -f "$ARTIFACT" ] || { echo "Missing artifact: $ARTIFACT" >&2; exit 1; }
  ARTIFACT_DIR="$(cd "$(dirname "$ARTIFACT")" && pwd)"
  NAME="$(basename "$ARTIFACT")"
  cp "$ARTIFACT" "$WORKDIR/$NAME"
  [ -f "$ARTIFACT_DIR/SHA256SUMS" ] && cp "$ARTIFACT_DIR/SHA256SUMS" "$WORKDIR/"
  [ -f "$ARTIFACT_DIR/SHA256SUMS.asc" ] && cp "$ARTIFACT_DIR/SHA256SUMS.asc" "$WORKDIR/"
  ARTIFACT="$WORKDIR/$NAME"
else
  [ -n "$VERSION" ] || { echo "--version or --artifact required" >&2; exit 2; }
  VER="${VERSION#v}"
  NAME="keprix-v${VER}"
  echo "Downloading $NAME ..."
  curl -fsSL "$BASE_URL/v${VER}/${NAME}.tar.gz" -o "$WORKDIR/${NAME}.tar.gz"
  curl -fsSL "$BASE_URL/v${VER}/SHA256SUMS" -o "$WORKDIR/SHA256SUMS"
  curl -fsSL "$BASE_URL/v${VER}/SHA256SUMS.asc" -o "$WORKDIR/SHA256SUMS.asc" || true
  ARTIFACT="$WORKDIR/${NAME}.tar.gz"
fi

bash "$ROOT/scripts/verify-release.sh" "$ARTIFACT"

mkdir -p "$WORKDIR/extract"
tar -xzf "$ARTIFACT" -C "$WORKDIR/extract"
SRC="$(find "$WORKDIR/extract" -maxdepth 1 -type d -name 'keprix-v*' | head -1)"
[ -d "$SRC" ] || { echo "Extracted tree not found" >&2; exit 1; }
exec bash "$SRC/scripts/install.sh"
