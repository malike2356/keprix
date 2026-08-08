#!/usr/bin/env python3
"""Fail when public Keprix components disagree on the release version."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


with (ROOT / "pyproject.toml").open("rb") as handle:
    canonical = str(tomllib.load(handle)["project"]["version"])

sources = {
    "frontend/package.json": str(
        json.loads((ROOT / "frontend/package.json").read_text())["version"]
    ),
    "desktop/package.json": str(
        json.loads((ROOT / "src/keprix/apps/desktop/package.json").read_text())["version"]
    ),
    ".release-please-manifest.json": str(
        json.loads((ROOT / ".release-please-manifest.json").read_text())["."]
    ),
}
cli_text = (ROOT / "src/keprix/keprix_cli/__init__.py").read_text(encoding="utf-8")
match = re.search(r'^__version__\s*=\s*"([^"]+)"', cli_text, re.MULTILINE)
if not match:
    fail("could not read keprix_cli __version__")
sources["src/keprix/keprix_cli/__init__.py"] = match.group(1)

mismatches = [f"{path}={version}" for path, version in sources.items() if version != canonical]
if mismatches:
    fail(f"canonical pyproject version is {canonical}; mismatches: {', '.join(mismatches)}")

print(f"PASS: all release components use {canonical}")
