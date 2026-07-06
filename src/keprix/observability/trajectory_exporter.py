"""Trajectory file export for admin session review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _logs_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "logs"
    except Exception:
        return Path.home() / ".keprix" / "logs"


def find_trajectory_file(session_id: str) -> Path | None:
    logs = _logs_dir()
    if not logs.is_dir():
        return None
    candidates = sorted(logs.glob(f"session_*{session_id}*.json"), reverse=True)
    if candidates:
        return candidates[0]
    for path in sorted(logs.glob("session_*.json"), reverse=True):
        if session_id in path.name:
            return path
    return None


def load_trajectory(session_id: str) -> dict[str, Any] | None:
    path = find_trajectory_file(session_id)
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"raw_file": str(path), "error": "Could not parse trajectory JSON"}


def summarize_trajectory(session_id: str) -> dict[str, Any]:
    data = load_trajectory(session_id)
    if data is None:
        return {"session_id": session_id, "found": False}
    conversations = data.get("conversations") or data.get("messages") or []
    return {
        "session_id": session_id,
        "found": True,
        "model": data.get("model"),
        "completed": data.get("completed"),
        "turn_count": len(conversations),
        "timestamp": data.get("timestamp"),
    }
