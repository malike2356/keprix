"""Append-only SQLite trajectory store."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from keprix.trajectory.redaction import redact_payload
from keprix.trajectory.types import EVENT_TYPES, TrajectoryEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trajectories (
    trajectory_id TEXT PRIMARY KEY,
    session_id TEXT,
    run_id TEXT,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    parent_trajectory_id TEXT,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS trajectory_events (
    event_id TEXT PRIMARY KEY,
    trajectory_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    tool_name TEXT,
    soft_wall_outcome TEXT,
    error_text TEXT,
    FOREIGN KEY (trajectory_id) REFERENCES trajectories(trajectory_id),
    UNIQUE (trajectory_id, seq)
);
CREATE INDEX IF NOT EXISTS ix_traj_events_traj_seq
    ON trajectory_events(trajectory_id, seq);
CREATE INDEX IF NOT EXISTS ix_traj_events_type
    ON trajectory_events(event_type);
CREATE INDEX IF NOT EXISTS ix_traj_events_tool
    ON trajectory_events(tool_name);
CREATE INDEX IF NOT EXISTS ix_traj_ws
    ON trajectories(workspace_id, updated_at);
"""


class AppendOnlyViolation(RuntimeError):
    """Raised when code attempts to mutate or delete past trajectory events."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class TrajectoryStore:
    """SQLite-backed append-only trajectory persistence."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        if sqlite_path is None:
            try:
                from keprix_constants import get_keprix_home

                base = Path(get_keprix_home()) / "trajectories"
            except Exception:
                base = Path.home() / ".keprix" / "trajectories"
            sqlite_path = base / "trajectories.db"
        self._sqlite_path = Path(sqlite_path)
        self._lock = threading.RLock()
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def create_trajectory(
        self,
        *,
        trajectory_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        workspace_id: str = "default",
        parent_trajectory_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tid = trajectory_id or str(uuid.uuid4())
        now = _utcnow()
        row = {
            "trajectory_id": tid,
            "session_id": session_id or tid,
            "run_id": run_id,
            "workspace_id": workspace_id or "default",
            "parent_trajectory_id": parent_trajectory_id,
            "title": title or f"trajectory {tid[:8]}",
            "created_at": now,
            "updated_at": now,
            "metadata": json.dumps(redact_payload(metadata or {}), ensure_ascii=False),
        }
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    INSERT INTO trajectories (
                        trajectory_id, session_id, run_id, workspace_id,
                        parent_trajectory_id, title, created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["trajectory_id"],
                        row["session_id"],
                        row["run_id"],
                        row["workspace_id"],
                        row["parent_trajectory_id"],
                        row["title"],
                        row["created_at"],
                        row["updated_at"],
                        row["metadata"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return row

    def append_event(
        self,
        trajectory_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        tool_name: str | None = None,
        soft_wall_outcome: str | None = None,
        error_text: str | None = None,
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> TrajectoryEvent:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unknown event_type: {event_type}")
        safe_payload = redact_payload(payload or {})
        if not isinstance(safe_payload, dict):
            safe_payload = {"value": safe_payload}
        with self._lock:
            conn = self._conn()
            try:
                exists = conn.execute(
                    "SELECT 1 FROM trajectories WHERE trajectory_id = ?",
                    (trajectory_id,),
                ).fetchone()
                if not exists:
                    raise KeyError(f"Unknown trajectory_id: {trajectory_id}")
                row = conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) AS m FROM trajectory_events WHERE trajectory_id = ?",
                    (trajectory_id,),
                ).fetchone()
                next_seq = int(row["m"]) + 1
                eid = event_id or str(uuid.uuid4())
                ts = timestamp or _utcnow()
                conn.execute(
                    """
                    INSERT INTO trajectory_events (
                        event_id, trajectory_id, seq, event_type, timestamp,
                        payload, tool_name, soft_wall_outcome, error_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        eid,
                        trajectory_id,
                        next_seq,
                        event_type,
                        ts,
                        json.dumps(safe_payload, ensure_ascii=False),
                        tool_name,
                        soft_wall_outcome,
                        redact_payload(error_text) if error_text else None,
                    ),
                )
                conn.execute(
                    "UPDATE trajectories SET updated_at = ? WHERE trajectory_id = ?",
                    (ts, trajectory_id),
                )
                conn.commit()
            finally:
                conn.close()
        return TrajectoryEvent(
            event_id=eid,
            trajectory_id=trajectory_id,
            seq=next_seq,
            event_type=event_type,
            timestamp=ts,
            payload=safe_payload,
            tool_name=tool_name,
            soft_wall_outcome=soft_wall_outcome,
            error_text=error_text,
        )

    def update_event(self, event_id: str, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(
            "trajectory_events is append-only; UPDATE is forbidden"
        )

    def delete_event(self, event_id: str) -> None:
        raise AppendOnlyViolation(
            "trajectory_events is append-only; DELETE is forbidden"
        )

    def get_trajectory(self, trajectory_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT * FROM trajectories WHERE trajectory_id = ?",
                    (trajectory_id,),
                ).fetchone()
                if row is None:
                    return None
                return dict(row)
            finally:
                conn.close()

    def list_trajectories(
        self,
        *,
        workspace_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        with self._lock:
            conn = self._conn()
            try:
                if workspace_id:
                    rows = conn.execute(
                        """
                        SELECT * FROM trajectories
                        WHERE workspace_id = ?
                        ORDER BY updated_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (workspace_id, limit, offset),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM trajectories
                        ORDER BY updated_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def list_events(
        self,
        trajectory_id: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[TrajectoryEvent]:
        limit = max(1, min(int(limit), 5000))
        offset = max(0, int(offset))
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM trajectory_events
                    WHERE trajectory_id = ?
                    ORDER BY seq ASC
                    LIMIT ? OFFSET ?
                    """,
                    (trajectory_id, limit, offset),
                ).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def search_events(
        self,
        *,
        trajectory_id: str | None = None,
        workspace_id: str | None = None,
        event_type: str | None = None,
        tool_name: str | None = None,
        soft_wall_outcome: str | None = None,
        error_query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TrajectoryEvent]:
        limit = max(1, min(int(limit), 1000))
        offset = max(0, int(offset))
        clauses: list[str] = []
        params: list[Any] = []
        join = ""
        if workspace_id:
            join = "JOIN trajectories t ON t.trajectory_id = e.trajectory_id"
            clauses.append("t.workspace_id = ?")
            params.append(workspace_id)
        if trajectory_id:
            clauses.append("e.trajectory_id = ?")
            params.append(trajectory_id)
        if event_type:
            clauses.append("e.event_type = ?")
            params.append(event_type)
        if tool_name:
            clauses.append("e.tool_name = ?")
            params.append(tool_name)
        if soft_wall_outcome:
            clauses.append("e.soft_wall_outcome = ?")
            params.append(soft_wall_outcome)
        if error_query:
            clauses.append("e.error_text LIKE ?")
            params.append(f"%{error_query}%")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT e.* FROM trajectory_events e
            {join}
            {where}
            ORDER BY e.timestamp DESC, e.seq DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [self._row_to_event(r) for r in rows]
            finally:
                conn.close()

    def export_events_for_fixture(
        self,
        trajectory_id: str,
        *,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """Stable export for recorded-session tests (prompt 772)."""
        return [e.to_dict() for e in self.list_events(trajectory_id, limit=limit)]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> TrajectoryEvent:
        payload_raw = row["payload"] or "{}"
        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = {"raw": payload_raw}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        return TrajectoryEvent(
            event_id=row["event_id"],
            trajectory_id=row["trajectory_id"],
            seq=int(row["seq"]),
            event_type=row["event_type"],
            timestamp=row["timestamp"],
            payload=payload,
            tool_name=row["tool_name"],
            soft_wall_outcome=row["soft_wall_outcome"],
            error_text=row["error_text"],
        )


_STORE: TrajectoryStore | None = None
_STORE_LOCK = threading.Lock()


def get_trajectory_store(sqlite_path: Path | None = None) -> TrajectoryStore:
    global _STORE
    with _STORE_LOCK:
        if sqlite_path is not None:
            return TrajectoryStore(sqlite_path=sqlite_path)
        if _STORE is None:
            _STORE = TrajectoryStore()
        return _STORE


def reset_trajectory_store_for_tests(sqlite_path: Path | None = None) -> TrajectoryStore:
    global _STORE
    with _STORE_LOCK:
        _STORE = TrajectoryStore(sqlite_path=sqlite_path)
        return _STORE
