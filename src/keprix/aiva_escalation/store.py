"""SQLite store for Aiva escalations (K05)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data_root() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "aiva_escalation"
    except Exception:
        root = Path.home() / ".keprix" / "aiva_escalation"
    root.mkdir(parents=True, exist_ok=True)
    return root


SCHEMA = """
CREATE TABLE IF NOT EXISTS aiva_escalations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    session_id TEXT,
    escalation_type TEXT NOT NULL,
    confidence_score REAL,
    original_input TEXT NOT NULL,
    holding_message TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_va TEXT,
    va_response TEXT,
    channel TEXT,
    notify_log TEXT,
    audit_log TEXT,
    created_at TEXT NOT NULL,
    assigned_at TEXT,
    completed_at TEXT,
    reassigned_at TEXT
);

CREATE TABLE IF NOT EXISTS aiva_human_assist_requests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'normal',
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    escalation_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_aiva_esc_ws_status ON aiva_escalations(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_aiva_assist_ws ON aiva_human_assist_requests(workspace_id, status);
"""


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("notify_log", "audit_log"):
        if data.get(key):
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                data[key] = []
        else:
            data[key] = []
    return data


class EscalationStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_data_root() / "escalations.sqlite")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        return _row(self._conn.execute(sql, params).fetchone())

    def _all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [d for r in self._conn.execute(sql, params).fetchall() if (d := _row(r))]

    def create_escalation(self, **fields: Any) -> dict[str, Any]:
        esc_id = str(uuid.uuid4())
        now = _utcnow()
        audit = [{"at": now, "event": "created", "by": "system"}]
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO aiva_escalations (
                    id, workspace_id, worker_id, session_id, escalation_type, confidence_score,
                    original_input, holding_message, status, assigned_va, va_response, channel,
                    notify_log, audit_log, created_at, assigned_at, completed_at, reassigned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    esc_id,
                    fields["workspace_id"],
                    fields["worker_id"],
                    fields.get("session_id"),
                    fields.get("escalation_type") or "low_confidence",
                    fields.get("confidence_score"),
                    fields["original_input"],
                    fields.get("holding_message"),
                    fields.get("status") or "pending",
                    fields.get("assigned_va"),
                    fields.get("va_response"),
                    fields.get("channel"),
                    json.dumps(fields.get("notify_log") or []),
                    json.dumps(audit),
                    now,
                    None,
                    None,
                    None,
                ),
            )
            self._conn.commit()
        return self.get_escalation(esc_id)  # type: ignore[return-value]

    def get_escalation(self, escalation_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM aiva_escalations WHERE id = ?", (escalation_id,))

    def list_queue(
        self,
        workspace_id: str,
        *,
        status: str | None = "pending",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if status:
            return self._all(
                """
                SELECT * FROM aiva_escalations
                WHERE workspace_id = ? AND status = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (workspace_id, status, limit),
            )
        return self._all(
            """
            SELECT * FROM aiva_escalations
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (workspace_id, limit),
        )

    def append_audit(self, escalation_id: str, event: str, **extra: Any) -> None:
        row = self.get_escalation(escalation_id)
        if not row:
            return
        audit = list(row.get("audit_log") or [])
        audit.append({"at": _utcnow(), "event": event, **extra})
        with self._lock:
            self._conn.execute(
                "UPDATE aiva_escalations SET audit_log = ? WHERE id = ?",
                (json.dumps(audit), escalation_id),
            )
            self._conn.commit()

    def set_notify_log(self, escalation_id: str, notify_log: list[dict[str, Any]]) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE aiva_escalations SET notify_log = ? WHERE id = ?",
                (json.dumps(notify_log), escalation_id),
            )
            self._conn.commit()

    def assign(self, escalation_id: str, assigned_va: str) -> dict[str, Any] | None:
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                UPDATE aiva_escalations
                SET status = 'assigned', assigned_va = ?, assigned_at = ?
                WHERE id = ? AND status IN ('pending', 'assigned')
                """,
                (assigned_va, now, escalation_id),
            )
            self._conn.commit()
        self.append_audit(escalation_id, "assigned", by=assigned_va)
        return self.get_escalation(escalation_id)

    def mark_in_progress(self, escalation_id: str, assigned_va: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            if assigned_va:
                self._conn.execute(
                    """
                    UPDATE aiva_escalations
                    SET status = 'in_progress', assigned_va = COALESCE(?, assigned_va)
                    WHERE id = ?
                    """,
                    (assigned_va, escalation_id),
                )
            else:
                self._conn.execute(
                    "UPDATE aiva_escalations SET status = 'in_progress' WHERE id = ?",
                    (escalation_id,),
                )
            self._conn.commit()
        self.append_audit(escalation_id, "in_progress", by=assigned_va or "va")
        return self.get_escalation(escalation_id)

    def complete(self, escalation_id: str, va_response: str, assigned_va: str | None = None) -> dict[str, Any] | None:
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                UPDATE aiva_escalations
                SET status = 'completed', va_response = ?, completed_at = ?,
                    assigned_va = COALESCE(?, assigned_va)
                WHERE id = ?
                """,
                (va_response, now, assigned_va, escalation_id),
            )
            self._conn.commit()
        self.append_audit(escalation_id, "completed", by=assigned_va or "va")
        return self.get_escalation(escalation_id)

    def cancel(self, escalation_id: str, reason: str = "") -> dict[str, Any] | None:
        with self._lock:
            self._conn.execute(
                "UPDATE aiva_escalations SET status = 'cancelled' WHERE id = ?",
                (escalation_id,),
            )
            self._conn.commit()
        self.append_audit(escalation_id, "cancelled", reason=reason)
        return self.get_escalation(escalation_id)

    def reassign_stale(self, *, older_than_iso: str) -> list[dict[str, Any]]:
        """Clear assignment on pending/assigned items older than cutoff; return reassigned rows."""
        stale = self._all(
            """
            SELECT * FROM aiva_escalations
            WHERE status IN ('pending', 'assigned')
              AND created_at <= ?
              AND (reassigned_at IS NULL OR reassigned_at <= ?)
            """,
            (older_than_iso, older_than_iso),
        )
        now = _utcnow()
        out: list[dict[str, Any]] = []
        for row in stale:
            with self._lock:
                self._conn.execute(
                    """
                    UPDATE aiva_escalations
                    SET status = 'pending', assigned_va = NULL, assigned_at = NULL, reassigned_at = ?
                    WHERE id = ?
                    """,
                    (now, row["id"]),
                )
                self._conn.commit()
            self.append_audit(str(row["id"]), "timeout_reassigned", previous_va=row.get("assigned_va"))
            updated = self.get_escalation(str(row["id"]))
            if updated:
                out.append(updated)
        return out

    def create_assist_request(self, **fields: Any) -> dict[str, Any]:
        req_id = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO aiva_human_assist_requests (
                    id, workspace_id, worker_id, reason, urgency, details, status, escalation_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req_id,
                    fields["workspace_id"],
                    fields["worker_id"],
                    fields["reason"],
                    fields.get("urgency") or "normal",
                    fields.get("details"),
                    fields.get("status") or "pending",
                    fields.get("escalation_id"),
                    now,
                ),
            )
            self._conn.commit()
        return self._one("SELECT * FROM aiva_human_assist_requests WHERE id = ?", (req_id,))  # type: ignore[return-value]


_store: EscalationStore | None = None
_lock = threading.Lock()


def get_escalation_store(path: Path | None = None) -> EscalationStore:
    global _store
    if path is not None:
        return EscalationStore(path=path)
    with _lock:
        if _store is None:
            _store = EscalationStore()
        return _store


def reset_escalation_store_for_tests(path: Path | None = None) -> EscalationStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = EscalationStore(path=path) if path else EscalationStore()
        return _store
