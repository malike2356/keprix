#!/usr/bin/env bash
# `next build --output standalone` does not copy static assets into the
# standalone server's own directory tree, and it never touches CHANGELOG.md.
# Docker's Dockerfile.frontend papers over this with explicit COPY steps in
# the image build; this is the equivalent for running the frontend directly
# (no Docker) via `npm run build` / `npm run start:standalone`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
cd "$FRONTEND_DIR"

STANDALONE_DIR=".next/standalone"
SERVER_JS="$(find "$STANDALONE_DIR" -maxdepth 3 -name server.js 2>/dev/null | head -1)"
if [[ -z "$SERVER_JS" ]]; then
  echo "sync-next-standalone-assets: no server.js found under $STANDALONE_DIR — run 'next build' first" >&2
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
cp "../CHANGELOG.md" "$SERVER_DIR/../CHANGELOG.md"

echo "sync-next-standalone-assets: synced static/, public/, and CHANGELOG.md into $SERVER_DIR"
