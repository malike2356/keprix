"""Active capability preset state (which pack is applied)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


def _state_path() -> Path:
    try:
        from keprix_constants import get_keprix_home

        base = Path(get_keprix_home())
    except Exception:
        base = Path.home() / ".keprix"
    return base / "capability_presets" / "active.json"


_LOCK = threading.RLock()
_OVERRIDE: Path | None = None


def set_state_path_for_tests(path: Path | None) -> None:
    global _OVERRIDE
    with _LOCK:
        _OVERRIDE = path


def get_active_state() -> dict[str, Any]:
    path = _OVERRIDE or _state_path()
    with _LOCK:
        if not path.exists():
            return {"active": None, "mounted_plugins": [], "declared_tools": []}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"active": None, "mounted_plugins": [], "declared_tools": []}
            return data
        except Exception:
            return {"active": None, "mounted_plugins": [], "declared_tools": []}


def save_active_state(state: dict[str, Any]) -> None:
    path = _OVERRIDE or _state_path()
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
