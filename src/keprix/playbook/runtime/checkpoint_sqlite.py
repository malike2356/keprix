"""SQLite checkpoint store for local installs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from keprix.playbook.runtime.checkpoint import CheckpointRecord, CheckpointStore


class SQLiteCheckpointStore(CheckpointStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS playbook_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    graph_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    input_state TEXT NOT NULL,
                    output_state TEXT,
                    timestamp TEXT NOT NULL,
                    error TEXT,
                    approval_request TEXT,
                    artifacts TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_playbook_checkpoints_run "
                "ON playbook_checkpoints(run_id, timestamp)"
            )
            conn.commit()

    async def save(self, record: CheckpointRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO playbook_checkpoints (
                    checkpoint_id, run_id, graph_id, node_name,
                    input_state, output_state, timestamp, error,
                    approval_request, artifacts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.checkpoint_id,
                    record.run_id,
                    record.graph_id,
                    record.node_name,
                    json.dumps(record.input_state),
                    json.dumps(record.output_state) if record.output_state is not None else None,
                    record.timestamp.isoformat(),
                    record.error,
                    json.dumps(record.approval_request) if record.approval_request else None,
                    json.dumps(record.artifacts),
                ),
            )
            conn.commit()

    async def get_latest(self, run_id: str) -> CheckpointRecord | None:
        rows = await self.list_for_run(run_id)
        return rows[-1] if rows else None

    async def list_for_run(self, run_id: str) -> list[CheckpointRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM playbook_checkpoints
                WHERE run_id = ?
                ORDER BY timestamp ASC
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> CheckpointRecord:
        from datetime import datetime

        return CheckpointRecord(
            checkpoint_id=row["checkpoint_id"],
            run_id=row["run_id"],
            graph_id=row["graph_id"],
            node_name=row["node_name"],
            input_state=json.loads(row["input_state"]),
            output_state=json.loads(row["output_state"]) if row["output_state"] else None,
            timestamp=datetime.fromisoformat(row["timestamp"]),
            error=row["error"],
            approval_request=json.loads(row["approval_request"]) if row["approval_request"] else None,
            artifacts=json.loads(row["artifacts"]),
        )
