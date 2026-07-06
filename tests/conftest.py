"""Shared pytest configuration for top-level tests/."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SRC_KEPRIX = SRC / "keprix"

os.environ.setdefault("KEPRIX_DATA_DIR", str(ROOT / ".pytest-data"))
os.environ.setdefault("KEPRIX_USE_MEMORY_STORE", "1")
os.environ.setdefault("KEPRIX_DATABASE_URL", "")
Path(os.environ["KEPRIX_DATA_DIR"]).mkdir(parents=True, exist_ok=True)

for path in (str(SRC), str(SRC_KEPRIX)):
    if path not in sys.path:
        sys.path.insert(0, path)
