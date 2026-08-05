"""Persisted incident records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

from keprix.incident.severity import IncidentLevel


def _incidents_path() -> Path:
    return get_keprix_home() / "incidents" / "active.json"


def _load() -> dict[str, Any]:
    path = _incidents_path()
    if not path.exists():
        return {"incidents": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"incidents": []}


def _save(data: dict[str, Any]) -> None:
    path = _incidents_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_incidents(*, include_closed: bool = False) -> list[dict[str, Any]]:
    rows = list(_load().get("incidents") or [])
    if include_closed:
        return rows
    return [row for row in rows if row.get("status") != "closed"]


def get_incident(incident_id: str) -> dict[str, Any] | None:
    for row in list_incidents(include_closed=True):
        if row.get("id") == incident_id:
            return dict(row)
    return None


def create_incident(
    *,
    level: IncidentLevel,
    reason: str,
    product_id: str | None = None,
    session_id: str | None = None,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "id": f"inc-{uuid.uuid4().hex[:12]}",
        "level": level.value,
        "reason": reason,
        "product_id": product_id,
        "session_id": session_id,
        "status": "open",
        "opened_at": now,
        "actions_taken": actions or [],
        "timeline": [{"at": now, "event": "declared", "detail": reason}],
    }
    data = _load()
    incidents = list(data.get("incidents") or [])
    incidents.append(record)
    data["incidents"] = incidents[-100:]
    _save(data)
    return record


def append_timeline(incident_id: str, event: str, detail: str = "") -> dict[str, Any] | None:
    data = _load()
    incidents = list(data.get("incidents") or [])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for row in incidents:
        if row.get("id") != incident_id:
            continue
        timeline = list(row.get("timeline") or [])
        timeline.append({"at": now, "event": event, "detail": detail})
        row["timeline"] = timeline
        _save(data)
        return dict(row)
    return None


def close_incident(incident_id: str, *, resolution: str = "") -> dict[str, Any] | None:
    data = _load()
    incidents = list(data.get("incidents") or [])
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for row in incidents:
        if row.get("id") != incident_id:
            continue
        row["status"] = "closed"
        row["closed_at"] = now
        row["resolution"] = resolution
        timeline = list(row.get("timeline") or [])
        timeline.append({"at": now, "event": "closed", "detail": resolution})
        row["timeline"] = timeline
        _save(data)
        return dict(row)
    return None
