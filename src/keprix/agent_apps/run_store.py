"""Persistent storage for agent app runs and lifecycle events."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _store_root() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "agent_apps"
    except Exception:
        root = Path.home() / ".keprix" / "agent_apps"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _db_path() -> Path:
    return _store_root() / "runs.db"


def retention_days() -> int:
    raw = os.environ.get("KEPRIX_AGENT_APP_RUN_RETENTION_DAYS", "30").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_run_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                trace_id TEXT PRIMARY KEY,
                app_name TEXT NOT NULL,
                user_id TEXT,
                status TEXT NOT NULL,
                runner TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                error TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration_ms INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_runs_app_started ON runs(app_name, started_at DESC);

            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                event TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_trace ON lifecycle_events(trace_id, id);

            CREATE TABLE IF NOT EXISTS eval_last (
                app_name TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                ran_at TEXT NOT NULL
            );
            """
        )


def prune_old_runs(*, days: int | None = None) -> int:
    init_run_store()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days or retention_days())
    cutoff_iso = cutoff.isoformat()
    with _connect() as conn:
        trace_rows = conn.execute(
            "SELECT trace_id FROM runs WHERE started_at < ?",
            (cutoff_iso,),
        ).fetchall()
        trace_ids = [row["trace_id"] for row in trace_rows]
        if trace_ids:
            placeholders = ",".join("?" for _ in trace_ids)
            conn.execute(
                f"DELETE FROM lifecycle_events WHERE trace_id IN ({placeholders})",
                trace_ids,
            )
        deleted = conn.execute("DELETE FROM runs WHERE started_at < ?", (cutoff_iso,)).rowcount
        conn.commit()
    return int(deleted or 0)


def record_run_start(
    *,
    trace_id: str,
    app_name: str,
    runner: str,
    input_payload: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    init_run_store()
    prune_old_runs()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO runs
            (trace_id, app_name, user_id, status, runner, input_json, started_at)
            VALUES (?, ?, ?, 'running', ?, ?, ?)
            """,
            (
                trace_id,
                app_name,
                user_id,
                runner,
                json.dumps(input_payload or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def record_run_finish(
    *,
    trace_id: str,
    status: str,
    output: dict[str, Any] | None = None,
    error: str | None = None,
    started_at: str | None = None,
) -> None:
    init_run_store()
    finished = datetime.now(timezone.utc)
    duration_ms = None
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            duration_ms = int((finished - started).total_seconds() * 1000)
        except ValueError:
            duration_ms = None
    with _connect() as conn:
        conn.execute(
            """
            UPDATE runs
            SET status = ?, output_json = ?, error = ?, finished_at = ?, duration_ms = ?
            WHERE trace_id = ?
            """,
            (
                status,
                json.dumps(output or {}),
                error,
                finished.isoformat(),
                duration_ms,
                trace_id,
            ),
        )


def record_lifecycle_event(
    *,
    trace_id: str,
    event: str,
    payload: dict[str, Any],
    created_at: str,
) -> None:
    init_run_store()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO lifecycle_events (trace_id, event, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                trace_id,
                event,
                json.dumps(payload),
                created_at,
            ),
        )


def list_runs(app_name: str, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    init_run_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT trace_id, app_name, status, runner, input_json, output_json, error,
                   started_at, finished_at, duration_ms
            FROM runs
            WHERE app_name = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (app_name, limit, offset),
        ).fetchall()
    return [_row_to_run_dict(row, include_io=False) for row in rows]


def get_run(trace_id: str) -> dict[str, Any] | None:
    init_run_store()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT trace_id, app_name, status, runner, input_json, output_json, error,
                   started_at, finished_at, duration_ms
            FROM runs WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_run_dict(row)


def list_run_events(trace_id: str) -> list[dict[str, Any]]:
    init_run_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT event, payload_json, created_at
            FROM lifecycle_events
            WHERE trace_id = ?
            ORDER BY id ASC
            """,
            (trace_id,),
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload_json"] or "{}")
        events.append({"event": row["event"], "payload": payload, "created_at": row["created_at"]})
    return events


def save_eval_result(app_name: str, result: dict[str, Any]) -> dict[str, Any]:
    init_run_store()
    ran_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO eval_last (app_name, result_json, ran_at)
            VALUES (?, ?, ?)
            ON CONFLICT(app_name) DO UPDATE SET
                result_json = excluded.result_json,
                ran_at = excluded.ran_at
            """,
            (app_name, json.dumps(result), ran_at),
        )
        conn.commit()
    return {"app_name": app_name, "ran_at": ran_at, "result": result}


def get_last_eval(app_name: str) -> dict[str, Any] | None:
    init_run_store()
    with _connect() as conn:
        row = conn.execute(
            "SELECT result_json, ran_at FROM eval_last WHERE app_name = ?",
            (app_name,),
        ).fetchone()
    if row is None:
        return None
    return {
        "app_name": app_name,
        "ran_at": row["ran_at"],
        "result": json.loads(row["result_json"] or "{}"),
    }


def _input_preview(payload: dict[str, Any]) -> str:
    raw_input = str(payload.get("input") or "").strip()
    if raw_input:
        return raw_input[:120]
    context = payload.get("context")
    if isinstance(context, dict):
        form = context.get("form") or context.get("inputs")
        if isinstance(form, dict):
            for value in form.values():
                text = str(value).strip()
                if text:
                    return text[:120]
    return ""


def _row_to_run_dict(row: sqlite3.Row, *, include_io: bool = True) -> dict[str, Any]:
    input_payload = json.loads(row["input_json"] or "{}")
    data: dict[str, Any] = {
        "trace_id": row["trace_id"],
        "app_name": row["app_name"],
        "status": row["status"],
        "runner": row["runner"],
        "input_preview": _input_preview(input_payload),
        "error": row["error"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_ms": row["duration_ms"],
    }
    if include_io:
        data["input"] = input_payload
        data["output"] = json.loads(row["output_json"] or "{}")
    return data
