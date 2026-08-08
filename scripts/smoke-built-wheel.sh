#!/usr/bin/env bash
set -euo pipefail

dist_dir="${1:-dist}"
PYTHON="${PYTHON:-python3}"
wheel_count="$(find "$dist_dir" -maxdepth 1 -type f -name 'keprix-*.whl' | wc -l)"
[[ "$wheel_count" == 1 ]] || {
  echo "Expected exactly one Keprix wheel under $dist_dir, found $wheel_count" >&2
  exit 1
}
wheel="$(find "$dist_dir" -maxdepth 1 -type f -name 'keprix-*.whl' -print -quit)"
"$PYTHON" scripts/check-python-artifact.py "$wheel"
venv_dir="$(mktemp -d)"
trap 'rm -rf -- "$venv_dir"' EXIT
"$PYTHON" -m venv "$venv_dir/venv"
"$venv_dir/venv/bin/python" -m pip install --disable-pip-version-check "${wheel}[tui]"
"$venv_dir/venv/bin/python" -m pip check
"$venv_dir/venv/bin/python" -m keprix version --json
"$venv_dir/venv/bin/keprix" tui --help >/dev/null
echo "Built wheel smoke passed"
