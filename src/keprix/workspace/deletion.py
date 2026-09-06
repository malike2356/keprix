"""Self-service workspace deletion lifecycle with a mandatory grace period."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from keprix.billing.subscriptions.lifecycle import cancel_subscription


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _path() -> Path:
    root = Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")) / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    return root / "deletions.json"


class WorkspaceDeletionStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _path()
        self._lock = threading.RLock()

    def _read(self) -> dict[str, dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, value: dict[str, dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def get(self, workspace_id: str) -> dict[str, Any] | None:
        return self._read().get(workspace_id)

    def save(self, workspace_id: str, row: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            data[workspace_id] = row
            self._write(data)
            return row

    def list_due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current = (now or _now()).timestamp()
        return [row for row in self._read().values() if not row.get("cancelled_at") and not row.get("purged_at") and _timestamp(row.get("purge_after")) <= current]


def _timestamp(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return float("inf")


_store: WorkspaceDeletionStore | None = None


def get_deletion_store() -> WorkspaceDeletionStore:
    global _store
    if _store is None:
        _store = WorkspaceDeletionStore()
    return _store


def _status(row: dict[str, Any] | None, workspace_id: str) -> dict[str, Any]:
    if not row or row.get("cancelled_at") or row.get("purged_at"):
        return {"workspace_id": workspace_id, "state": "active", "scheduled": False, "seconds_remaining": None}
    remaining = max(0, int(_timestamp(row.get("purge_after")) - _now().timestamp()))
    return {"workspace_id": workspace_id, "state": "pending_deletion", "scheduled": True, "seconds_remaining": remaining, **row}


async def request_deletion(workspace_id: str, owner_user_id: str) -> dict[str, Any]:
    existing = get_deletion_store().get(workspace_id)
    if existing and not existing.get("cancelled_at") and not existing.get("purged_at"):
        return _status(existing, workspace_id)
    await cancel_subscription(owner_user_id, at_period_end=True)
    requested = _now()
    row = {"id": str(uuid.uuid4()), "workspace_id": workspace_id, "owner_user_id": owner_user_id, "deletion_requested_at": requested.isoformat(), "purge_after": (requested + timedelta(hours=72)).isoformat(), "subscription_cancelled_at": requested.isoformat(), "documents_unlinked": True, "audit_events": [{"event": "workspace_deletion_requested", "at": requested.isoformat(), "workspace_id": workspace_id, "owner_user_id": owner_user_id}]}
    return _status(get_deletion_store().save(workspace_id, row), workspace_id)


def cancel_deletion(workspace_id: str) -> dict[str, Any]:
    row = get_deletion_store().get(workspace_id)
    if not row or row.get("cancelled_at") or row.get("purged_at"):
        return _status(row, workspace_id)
    if _timestamp(row.get("purge_after")) <= _now().timestamp():
        return _status(row, workspace_id)
    row["cancelled_at"] = _now().isoformat()
    row.setdefault("audit_events", []).append({"event": "workspace_deletion_cancelled", "at": row["cancelled_at"], "workspace_id": workspace_id})
    get_deletion_store().save(workspace_id, row)
    return _status(row, workspace_id)


def purge_due(*, purge_workspace: Callable[[str], None] | None = None) -> list[str]:
    if purge_workspace is None:
        raise ValueError("purge_workspace callback is required for destructive purge")
    purged: list[str] = []
    for row in get_deletion_store().list_due():
        workspace_id = str(row["workspace_id"])
        purge_workspace(workspace_id)
        row["purged_at"] = _now().isoformat()
        row.setdefault("audit_events", []).append({"event": "workspace_deletion_purged", "at": row["purged_at"], "workspace_id": workspace_id})
        get_deletion_store().save(workspace_id, row)
        purged.append(workspace_id)
    return purged
