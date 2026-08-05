#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if ! command -v pipx >/dev/null 2>&1; then
  echo "pipx is required for this smoke test."
  echo "Install pipx, then rerun: scripts/smoke-pipx-install.sh"
  exit 2
fi

PYTHON_BIN=""
for candidate in python3.12 python3.11; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.11 or 3.12 is required for Keprix."
  exit 2
fi

export PIPX_HOME="$TMP_DIR/pipx-home"
export PIPX_BIN_DIR="$TMP_DIR/pipx-bin"
mkdir -p "$PIPX_HOME" "$PIPX_BIN_DIR"

pipx install --python "$PYTHON_BIN" "$ROOT_DIR[tui]" --force

"$PIPX_BIN_DIR/keprix" --version
"$PIPX_BIN_DIR/keprix" tui --help

VENV_PY="$PIPX_HOME/venvs/keprix/bin/python"
"$VENV_PY" - <<'PY'
import importlib

for module in ("keprix", "keprix.tui.app", "textual"):
    importlib.import_module(module)

print("pipx smoke import checks passed")
PY

echo "pipx smoke install passed"
