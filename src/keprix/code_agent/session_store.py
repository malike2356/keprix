"""Persistent store for long-horizon coding sessions."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

SessionStatus = Literal["active", "paused", "completed", "failed"]


def _sessions_dir() -> Path:
    base = Path.home() / ".keprix" / "code_agent" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CodingSessionRecord:
    id: str
    workspace_id: str
    objective: str
    status: SessionStatus = "active"
    turn: int = 0
    repo_path: str | None = None
    sandbox_session_id: str | None = None
    provider: str = "docker"
    control_center_session_id: str | None = None
    trajectory_run_id: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CodingSessionRecord:
        return cls(
            id=str(payload["id"]),
            workspace_id=str(payload.get("workspace_id") or "default"),
            objective=str(payload.get("objective") or ""),
            status=payload.get("status") or "active",
            turn=int(payload.get("turn") or 0),
            repo_path=payload.get("repo_path"),
            sandbox_session_id=payload.get("sandbox_session_id"),
            provider=str(payload.get("provider") or "docker"),
            control_center_session_id=payload.get("control_center_session_id"),
            trajectory_run_id=str(payload.get("trajectory_run_id") or ""),
            messages=list(payload.get("messages") or []),
            created_at=str(payload.get("created_at") or _utcnow()),
            updated_at=str(payload.get("updated_at") or _utcnow()),
        )


class CodingSessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _sessions_dir()

    def _path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def create(
        self,
        *,
        workspace_id: str,
        objective: str,
        repo_path: str | None = None,
        provider: str = "docker",
        control_center_session_id: str | None = None,
    ) -> CodingSessionRecord:
        record = CodingSessionRecord(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            objective=objective,
            repo_path=repo_path,
            provider=provider,
            control_center_session_id=control_center_session_id,
            trajectory_run_id=str(uuid.uuid4()),
        )
        self.save(record)
        return record

    def get(self, session_id: str) -> CodingSessionRecord | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CodingSessionRecord.from_dict(payload)

    def save(self, record: CodingSessionRecord) -> None:
        record.updated_at = _utcnow()
        path = self._path(record.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")

    def list_sessions(self, *, status: str | None = None) -> list[CodingSessionRecord]:
        rows: list[CodingSessionRecord] = []
        for path in sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            record = CodingSessionRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if status and record.status != status:
                continue
            rows.append(record)
        return rows


_store: CodingSessionStore | None = None


def get_coding_session_store() -> CodingSessionStore:
    global _store
    if _store is None:
        _store = CodingSessionStore()
    return _store
