"""Persisted workspace audience mode for customer concierge exposure."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any, Literal

from keprix_constants import get_keprix_home

AudienceMode = Literal["team", "customers", "both"]
_lock = RLock()


def _path() -> Path:
    return get_keprix_home() / "customer-concierge-audience-modes.json"


def _read() -> dict[str, str]:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
        allowed = {"team", "customers", "both"}
        return {str(key): str(value) for key, value in raw.items() if value in allowed}
    except (OSError, TypeError, ValueError):
        return {}


def get_audience_mode(workspace_id: str) -> AudienceMode:
    with _lock:
        mode = _read().get(workspace_id, "team")
    return mode if mode in {"team", "customers", "both"} else "team"  # type: ignore[return-value]


def audience_mode_is_explicit(workspace_id: str) -> bool:
    with _lock:
        return workspace_id in _read()


def set_audience_mode(workspace_id: str, mode: str) -> dict[str, Any]:
    normalized = mode.strip().lower()
    if normalized not in {"team", "customers", "both"}:
        raise ValueError("mode must be team, customers, or both")
    with _lock:
        values = _read()
        values[workspace_id] = normalized
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(values, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    return audience_mode_payload(workspace_id)


def audience_mode_payload(workspace_id: str) -> dict[str, Any]:
    mode = get_audience_mode(workspace_id)
    return {
        "workspaceId": workspace_id,
        "mode": mode,
        "publicConciergeEnabled": mode in {"customers", "both"},
        "internalWorkspaceEnabled": mode in {"team", "both"},
    }
