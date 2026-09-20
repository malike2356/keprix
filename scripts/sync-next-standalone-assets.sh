#!/usr/bin/env bash
# Assemble Next.js standalone assets for both local run paths:
#
# 1. In-place sync into frontend/.next/standalone/ (static/, public/,
#    CHANGELOG.md) so `pnpm start:standalone` / `node .next/standalone/server.js`
#    works the same way Dockerfile.frontend's runner-stage COPY steps do.
# 2. Copy + heal into src/keprix/keprix_cli/frontend_dist/ via Python
#    (frontend_standalone.assemble_standalone_dist) so `keprix dashboard`
#    gets a runnable sibling Node process. That step also works around a
#    confirmed Next.js standalone + pnpm tracing gap (missing styled-jsx /
#    @swc/helpers / @next/env / client-only at runtime).
#
# Invoked as `bash ../scripts/sync-next-standalone-assets.sh` from
# frontend/ (see frontend/package.json's "build" script).
#
# Optional: set BACKEND_REWRITE_URL before `pnpm build` / this script so the
# assembled frontend_dist records which backend the Next rewrites were baked for.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
cd "$FRONTEND_DIR"

STANDALONE_DIR=".next/standalone"
SERVER_JS="$(find "$STANDALONE_DIR" -maxdepth 3 -name server.js 2>/dev/null | head -1 || true)"
if [[ -z "$SERVER_JS" ]]; then
  echo "sync-next-standalone-assets: no server.js found under $STANDALONE_DIR; run 'next build' first" >&2
  exit 1
fi
SERVER_DIR="$(dirname "$SERVER_JS")"

rm -rf "$SERVER_DIR/.next/static"
cp -r ".next/static" "$SERVER_DIR/.next/static"

rm -rf "$SERVER_DIR/public"
cp -r "public" "$SERVER_DIR/public"

# server.js calls process.chdir(__dirname) on startup, so runtime code that
# resolves paths off process.cwd() (src/lib/changelog.ts reads
# "<cwd>/../CHANGELOG.md") looks one directory above the server.js dir.
if [[ -f "../CHANGELOG.md" ]]; then
  cp "../CHANGELOG.md" "$SERVER_DIR/../CHANGELOG.md"
fi

echo "sync-next-standalone-assets: synced static/, public/, and CHANGELOG.md into $SERVER_DIR"

# Dashboard path: assemble + heal into keprix_cli/frontend_dist (optional if
# the keprix editable install / venv is not active; Docker and start:standalone
# do not need this step).
BACKEND_REWRITE_URL="${BACKEND_REWRITE_URL:-http://127.0.0.1:9119}"
export BACKEND_REWRITE_URL

if command -v python3 >/dev/null 2>&1; then
  if python3 -c "from keprix_cli import frontend_standalone" 2>/dev/null; then
    python3 -c "
import os
from keprix_cli import frontend_standalone as fe
backend_url = os.environ.get('BACKEND_REWRITE_URL', 'http://127.0.0.1:9119')
fe.assemble_standalone_dist(backend_url=backend_url)
print(f'sync-next-standalone-assets: dashboard dist at {fe.FRONTEND_DIST} (rewrite -> {backend_url})')
"
  else
    echo "sync-next-standalone-assets: keprix_cli not importable; skipped frontend_dist assemble (ok for Docker / start:standalone)" >&2
  fi
else
  echo "sync-next-standalone-assets: python3 not on PATH; skipped frontend_dist assemble" >&2
fi
