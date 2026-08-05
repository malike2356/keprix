"""SQLite store for triggers and leased runs."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.triggers.schema import (
    ActionSpec,
    EventSpec,
    ScheduleSpec,
    Trigger,
    TriggerRun,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS triggers (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    kind TEXT NOT NULL,
    schedule_json TEXT,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    event_json TEXT,
    action_json TEXT NOT NULL,
    approval_mode TEXT NOT NULL DEFAULT 'auto',
    ai_mode TEXT NOT NULL DEFAULT 'managed',
    next_run_at TEXT,
    last_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    condition_json TEXT NOT NULL DEFAULT '{}',
    note TEXT
);
CREATE INDEX IF NOT EXISTS ix_triggers_due ON triggers(enabled, next_run_at);
CREATE INDEX IF NOT EXISTS ix_triggers_event ON triggers(enabled, kind);

CREATE TABLE IF NOT EXISTS trigger_runs (
    id TEXT PRIMARY KEY,
    trigger_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    trigger_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    approval_id TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    locked_at TEXT,
    locked_by TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    ledger_entry_id TEXT,
    cost_credits INTEGER,
    quota_impact_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_trigger_runs_claim ON trigger_runs(status, locked_at);
CREATE INDEX IF NOT EXISTS ix_trigger_runs_trigger ON trigger_runs(trigger_id, created_at);
"""

LEASE_SECONDS = 120


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class TriggerStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "triggers.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path), timeout=30)
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def _row_trigger(self, row: sqlite3.Row) -> Trigger:
        schedule = json.loads(row["schedule_json"]) if row["schedule_json"] else None
        event = json.loads(row["event_json"]) if row["event_json"] else None
        action = json.loads(row["action_json"] or "{}")
        condition = json.loads(row["condition_json"] or "{}")
        return Trigger(
            id=row["id"],
            workspace_id=row["workspace_id"],
            owner_id=row["owner_id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            kind=row["kind"],  # type: ignore[arg-type]
            schedule=ScheduleSpec.from_dict(schedule),
            timezone=row["timezone"] or "UTC",
            event=EventSpec.from_dict(event),
            action=ActionSpec.from_dict(action),
            approval_mode=row["approval_mode"] or "auto",  # type: ignore[arg-type]
            ai_mode=row["ai_mode"] or "managed",  # type: ignore[arg-type]
            next_run_at=row["next_run_at"],
            last_run_at=row["last_run_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            condition=condition if isinstance(condition, dict) else {},
            note=row["note"],
        )

    def _row_run(self, row: sqlite3.Row) -> TriggerRun:
        quota = json.loads(row["quota_impact_json"]) if row["quota_impact_json"] else None
        return TriggerRun(
            id=row["id"],
            trigger_id=row["trigger_id"],
            workspace_id=row["workspace_id"],
            owner_id=row["owner_id"],
            status=row["status"],  # type: ignore[arg-type]
            trigger_kind=row["trigger_kind"],
            payload=json.loads(row["payload_json"] or "{}"),
            result=json.loads(row["result_json"] or "{}"),
            approval_id=row["approval_id"],
            attempts=int(row["attempts"] or 0),
            locked_at=row["locked_at"],
            locked_by=row["locked_by"],
            created_at=row["created_at"],
            finished_at=row["finished_at"],
            ledger_entry_id=row["ledger_entry_id"],
            cost_credits=row["cost_credits"],
            quota_impact=quota if isinstance(quota, dict) else None,
        )

    def create_trigger(self, trigger: Trigger) -> Trigger:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO triggers (
                    id, workspace_id, owner_id, name, enabled, kind, schedule_json, timezone,
                    event_json, action_json, approval_mode, ai_mode, next_run_at, last_run_at,
                    created_at, updated_at, condition_json, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trigger.id,
                    trigger.workspace_id,
                    trigger.owner_id,
                    trigger.name,
                    1 if trigger.enabled else 0,
                    trigger.kind,
                    json.dumps(trigger.schedule.to_dict()) if trigger.schedule else None,
                    trigger.timezone,
                    json.dumps(trigger.event.to_dict()) if trigger.event else None,
                    json.dumps(trigger.action.to_dict()),
                    trigger.approval_mode,
                    trigger.ai_mode,
                    trigger.next_run_at,
                    trigger.last_run_at,
                    trigger.created_at,
                    trigger.updated_at,
                    json.dumps(trigger.condition),
                    trigger.note,
                ),
            )
            conn.commit()
        return trigger

    def get_trigger(self, trigger_id: str) -> Trigger | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM triggers WHERE id = ?", (trigger_id,)).fetchone()
        return self._row_trigger(row) if row else None

    def list_triggers(
        self,
        *,
        workspace_id: str | None = None,
        enabled: bool | None = None,
        limit: int = 200,
    ) -> list[Trigger]:
        clauses: list[str] = []
        params: list[Any] = []
        if workspace_id:
            clauses.append("workspace_id = ?")
            params.append(workspace_id)
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(1 if enabled else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM triggers {where} ORDER BY updated_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_trigger(row) for row in rows]

    def update_trigger(self, trigger: Trigger) -> Trigger:
        trigger.updated_at = _utcnow()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE triggers SET
                    name = ?, enabled = ?, kind = ?, schedule_json = ?, timezone = ?,
                    event_json = ?, action_json = ?, approval_mode = ?, ai_mode = ?,
                    next_run_at = ?, last_run_at = ?, updated_at = ?, condition_json = ?, note = ?
                WHERE id = ?
                """,
                (
                    trigger.name,
                    1 if trigger.enabled else 0,
                    trigger.kind,
                    json.dumps(trigger.schedule.to_dict()) if trigger.schedule else None,
                    trigger.timezone,
                    json.dumps(trigger.event.to_dict()) if trigger.event else None,
                    json.dumps(trigger.action.to_dict()),
                    trigger.approval_mode,
                    trigger.ai_mode,
                    trigger.next_run_at,
                    trigger.last_run_at,
                    trigger.updated_at,
                    json.dumps(trigger.condition),
                    trigger.note,
                    trigger.id,
                ),
            )
            conn.commit()
        return trigger

    def delete_trigger(self, trigger_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
            conn.commit()
            return cur.rowcount > 0

    def due_schedule_triggers(self, *, now_iso: str | None = None) -> list[Trigger]:
        now = now_iso or _utcnow()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM triggers
                WHERE enabled = 1 AND kind = 'schedule'
                  AND next_run_at IS NOT NULL AND next_run_at <= ?
                ORDER BY next_run_at ASC
                LIMIT 100
                """,
                (now,),
            ).fetchall()
        return [self._row_trigger(row) for row in rows]

    def list_event_triggers(
        self,
        *,
        source: str,
        event_type: str | None = None,
        workspace_id: str | None = None,
    ) -> list[Trigger]:
        out: list[Trigger] = []
        for trigger in self.list_triggers(workspace_id=workspace_id, enabled=True, limit=500):
            if trigger.kind != "event" or not trigger.event:
                continue
            if trigger.event.source != source:
                continue
            if event_type and trigger.event.event_type not in {"*", event_type}:
                continue
            out.append(trigger)
        return out

    def enqueue_run(
        self,
        trigger: Trigger,
        *,
        payload: dict[str, Any] | None = None,
    ) -> TriggerRun:
        run = TriggerRun(
            id=_new_id("trun"),
            trigger_id=trigger.id,
            workspace_id=trigger.workspace_id,
            owner_id=trigger.owner_id,
            status="queued",
            trigger_kind=trigger.kind,
            payload=dict(payload or {}),
            result={},
            approval_id=None,
            attempts=0,
            locked_at=None,
            locked_by=None,
            created_at=_utcnow(),
            finished_at=None,
        )
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO trigger_runs (
                    id, trigger_id, workspace_id, owner_id, status, trigger_kind,
                    payload_json, result_json, approval_id, attempts, locked_at, locked_by,
                    created_at, finished_at, ledger_entry_id, cost_credits, quota_impact_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.trigger_id,
                    run.workspace_id,
                    run.owner_id,
                    run.status,
                    run.trigger_kind,
                    json.dumps(run.payload),
                    json.dumps(run.result),
                    run.approval_id,
                    run.attempts,
                    run.locked_at,
                    run.locked_by,
                    run.created_at,
                    run.finished_at,
                    run.ledger_entry_id,
                    run.cost_credits,
                    json.dumps(run.quota_impact) if run.quota_impact else None,
                ),
            )
            conn.commit()
        return run

    def claim_next_run(self, *, worker_id: str, lease_seconds: int = LEASE_SECONDS) -> TriggerRun | None:
        """Atomically claim one queued (or stale-leased) run."""
        now = time.time()
        stale_before = datetime.fromtimestamp(now - lease_seconds, tz=timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM trigger_runs
                WHERE status = 'queued'
                   OR (status = 'running' AND locked_at IS NOT NULL AND locked_at < ?)
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (stale_before,),
            ).fetchone()
            if not row:
                return None
            locked_at = _utcnow()
            cur = conn.execute(
                """
                UPDATE trigger_runs
                SET status = 'running', locked_at = ?, locked_by = ?, attempts = attempts + 1
                WHERE id = ? AND (
                    status = 'queued'
                    OR (status = 'running' AND locked_at IS NOT NULL AND locked_at < ?)
                )
                """,
                (locked_at, worker_id, row["id"], stale_before),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return None
            conn.commit()
            claimed = conn.execute("SELECT * FROM trigger_runs WHERE id = ?", (row["id"],)).fetchone()
        return self._row_run(claimed) if claimed else None

    def update_run(self, run: TriggerRun) -> TriggerRun:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE trigger_runs SET
                    status = ?, result_json = ?, approval_id = ?, attempts = ?,
                    locked_at = ?, locked_by = ?, finished_at = ?, ledger_entry_id = ?,
                    cost_credits = ?, quota_impact_json = ?
                WHERE id = ?
                """,
                (
                    run.status,
                    json.dumps(run.result),
                    run.approval_id,
                    run.attempts,
                    run.locked_at,
                    run.locked_by,
                    run.finished_at,
                    run.ledger_entry_id,
                    run.cost_credits,
                    json.dumps(run.quota_impact) if run.quota_impact else None,
                    run.id,
                ),
            )
            conn.commit()
        return run

    def get_run(self, run_id: str) -> TriggerRun | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM trigger_runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_run(row) if row else None

    def list_runs(
        self,
        *,
        trigger_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[TriggerRun]:
        clauses: list[str] = []
        params: list[Any] = []
        if trigger_id:
            clauses.append("trigger_id = ?")
            params.append(trigger_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM trigger_runs {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_run(row) for row in rows]


_store: TriggerStore | None = None


def get_trigger_store() -> TriggerStore:
    global _store
    if _store is None:
        _store = TriggerStore()
    return _store


def reset_trigger_store_for_tests(store: TriggerStore | None = None) -> TriggerStore:
    global _store
    _store = store if store is not None else TriggerStore()
    return _store


def new_trigger_id() -> str:
    return _new_id("trg")
