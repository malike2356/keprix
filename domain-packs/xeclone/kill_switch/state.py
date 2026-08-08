"""Operator kill switch for queued publish and media jobs."""

from __future__ import annotations

import threading
import time
from typing import Any

_LOCK = threading.RLock()
_STATE: dict[str, Any] = {
    "active": False,
    "scopes": set(),
    "reason": "",
    "updated_at": None,
}


def reset_kill_switch() -> None:
    with _LOCK:
        _STATE["active"] = False
        _STATE["scopes"] = set()
        _STATE["reason"] = ""
        _STATE["updated_at"] = None


def set_kill_switch(*, active: bool, scopes: list[str] | None = None, reason: str = "") -> dict[str, Any]:
    with _LOCK:
        _STATE["active"] = bool(active)
        _STATE["scopes"] = set(scopes or ["publish", "media"])
        _STATE["reason"] = reason
        _STATE["updated_at"] = time.time()
        return status()


def is_blocked(scope: str) -> bool:
    with _LOCK:
        if not _STATE["active"]:
            return False
        scopes = _STATE["scopes"]
        return scope in scopes or "all" in scopes


def status() -> dict[str, Any]:
    with _LOCK:
        return {
            "active": bool(_STATE["active"]),
            "scopes": sorted(_STATE["scopes"]),
            "reason": _STATE["reason"],
            "updated_at": _STATE["updated_at"],
        }
