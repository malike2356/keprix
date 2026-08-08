#!/usr/bin/env python3
"""Validate that a public Python artifact contains no bundled workspace debris."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

MAX_WHEEL_BYTES = 20 * 1024 * 1024
FORBIDDEN = (
    "/node_modules/",
    "/apps/desktop/",
    "/.git/",
    "/.env",
    "/1st-plan/",
    "/pending-prompts/",
)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: check-python-artifact.py PATH.whl", file=sys.stderr)
        return 2
    wheel = Path(argv[0])
    if not wheel.is_file() or wheel.suffix != ".whl":
        print(f"FAIL: not a wheel: {wheel}", file=sys.stderr)
        return 1
    if wheel.stat().st_size > MAX_WHEEL_BYTES:
        print(f"FAIL: wheel exceeds {MAX_WHEEL_BYTES} bytes", file=sys.stderr)
        return 1
    with zipfile.ZipFile(wheel) as archive:
        names = [f"/{name}" for name in archive.namelist()]
    hits = sorted(name for name in names if any(marker in name for marker in FORBIDDEN))
    if hits:
        print("FAIL: forbidden public wheel members:", file=sys.stderr)
        for name in hits[:30]:
            print(f"  {name}", file=sys.stderr)
        return 1
    print(f"PASS: {wheel.name} contains {len(names)} clean entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
