"""Persisted browser harness sessions."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HarnessSessionRecord:
    session_id: str
    workspace_id: str
    profile_id: str | None
    objective: str
    url: str
    trace_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _session_root() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "browser" / "sessions"
    except Exception:
        root = Path.home() / ".keprix" / "browser" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


class HarnessSessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._root = base_dir or _session_root()
        self._root.mkdir(parents=True, exist_ok=True)
        self._path = self._root / "sessions.json"
        self._rows: dict[str, HarnessSessionRecord] = {}
        if self._path.exists():
            for row in json.loads(self._path.read_text(encoding="utf-8")):
                record = HarnessSessionRecord(**row)
                self._rows[record.session_id] = record

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([row.to_dict() for row in self._rows.values()], indent=2),
            encoding="utf-8",
        )

    def create(
        self,
        *,
        workspace_id: str,
        objective: str,
        url: str,
        profile_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> HarnessSessionRecord:
        sid = session_id or str(uuid.uuid4())
        record = HarnessSessionRecord(
            session_id=sid,
            workspace_id=workspace_id,
            profile_id=profile_id,
            objective=objective,
            url=url,
            trace_id=str(uuid.uuid4()),
            metadata=metadata or {},
        )
        self._rows[record.session_id] = record
        self._save()
        return record

    def get(self, session_id: str) -> HarnessSessionRecord | None:
        return self._rows.get(session_id)

    def list_for_workspace(self, workspace_id: str) -> list[HarnessSessionRecord]:
        return [row for row in self._rows.values() if row.workspace_id == workspace_id]

    def list_recent(self, workspace_id: str, *, limit: int = 50) -> list[HarnessSessionRecord]:
        rows = self.list_for_workspace(workspace_id)
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows[:limit]

    def update_metadata(self, session_id: str, patch: dict[str, Any]) -> HarnessSessionRecord | None:
        record = self._rows.get(session_id)
        if record is None:
            return None
        record.metadata.update(patch)
        self._save()
        return record


def session_mode(record: HarnessSessionRecord) -> str:
    explicit = record.metadata.get("mode")
    if explicit in {"dry_run", "live"}:
        return str(explicit)
    if str(record.metadata.get("profile_kind") or "") == "disposable":
        return "dry_run"
    return "live"


_store: HarnessSessionStore | None = None


def get_session_store() -> HarnessSessionStore:
    global _store
    if _store is None:
        _store = HarnessSessionStore()
    return _store
