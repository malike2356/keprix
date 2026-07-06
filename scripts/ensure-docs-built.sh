#!/usr/bin/env bash
# Build MkDocs into frontend/public/guide when missing (fast no-op when already built).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUIDE_INDEX="$ROOT/frontend/public/guide/index.html"

if [[ -f "$GUIDE_INDEX" ]]; then
  exit 0
fi

echo "Documentation site not found at frontend/public/guide; building..."
bash "$ROOT/scripts/build-docs.sh"
