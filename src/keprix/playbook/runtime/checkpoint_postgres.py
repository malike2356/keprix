"""PostgreSQL checkpoint store."""

from __future__ import annotations

import json
from datetime import datetime

from keprix.playbook.runtime.checkpoint import CheckpointRecord, CheckpointStore


class PostgresCheckpointStore(CheckpointStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._schema_ready = False

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS playbook_checkpoints (
                    checkpoint_id UUID PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    graph_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    input_state JSONB NOT NULL,
                    output_state JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    error TEXT,
                    approval_request JSONB,
                    artifacts JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_playbook_checkpoints_run
                ON playbook_checkpoints(run_id, timestamp)
                """
            )
        finally:
            await conn.close()
        self._schema_ready = True

    async def save(self, record: CheckpointRecord) -> None:
        import asyncpg

        await self._ensure_schema()
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO playbook_checkpoints (
                    checkpoint_id, run_id, graph_id, node_name,
                    input_state, output_state, timestamp, error,
                    approval_request, artifacts
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9::jsonb, $10::jsonb)
                """,
                record.checkpoint_id,
                record.run_id,
                record.graph_id,
                record.node_name,
                json.dumps(record.input_state),
                json.dumps(record.output_state) if record.output_state is not None else None,
                record.timestamp,
                record.error,
                json.dumps(record.approval_request) if record.approval_request else None,
                json.dumps(record.artifacts),
            )
        finally:
            await conn.close()

    async def get_latest(self, run_id: str) -> CheckpointRecord | None:
        rows = await self.list_for_run(run_id)
        return rows[-1] if rows else None

    async def list_for_run(self, run_id: str) -> list[CheckpointRecord]:
        import asyncpg

        await self._ensure_schema()
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT checkpoint_id, run_id, graph_id, node_name,
                       input_state, output_state, timestamp, error,
                       approval_request, artifacts
                FROM playbook_checkpoints
                WHERE run_id = $1
                ORDER BY timestamp ASC
                """,
                run_id,
            )
        finally:
            await conn.close()

        records: list[CheckpointRecord] = []
        for row in rows:
            input_state = row["input_state"]
            output_state = row["output_state"]
            approval_request = row["approval_request"]
            artifacts = row["artifacts"]
            if isinstance(input_state, str):
                input_state = json.loads(input_state)
            if isinstance(output_state, str):
                output_state = json.loads(output_state)
            if isinstance(approval_request, str):
                approval_request = json.loads(approval_request)
            if isinstance(artifacts, str):
                artifacts = json.loads(artifacts)
            ts = row["timestamp"]
            if not isinstance(ts, datetime):
                ts = datetime.fromisoformat(str(ts))
            records.append(
                CheckpointRecord(
                    checkpoint_id=str(row["checkpoint_id"]),
                    run_id=row["run_id"],
                    graph_id=row["graph_id"],
                    node_name=row["node_name"],
                    input_state=dict(input_state),
                    output_state=dict(output_state) if output_state else None,
                    timestamp=ts,
                    error=row["error"],
                    approval_request=dict(approval_request) if approval_request else None,
                    artifacts=list(artifacts) if artifacts else [],
                )
            )
        return records
