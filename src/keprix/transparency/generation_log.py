"""Append-only generation audit trail (hashes only; no raw prompt/output storage)."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.transparency.hashing import sha256_json, sha256_text

logger = logging.getLogger(__name__)

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_log (
    log_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    input_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    content_type TEXT NOT NULL,
    feature_endpoint TEXT NOT NULL,
    session_id TEXT,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    locale TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_generation_log_ts ON generation_log(timestamp);
CREATE INDEX IF NOT EXISTS ix_generation_log_user_ts ON generation_log(user_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_generation_log_model_ts ON generation_log(model_name, timestamp);
CREATE INDEX IF NOT EXISTS ix_generation_log_feature_ts ON generation_log(feature_endpoint, timestamp);
"""


class ImmutableLogError(RuntimeError):
    """Raised when application code attempts to mutate the generation log."""


class GenerationLogStore:
    """SQLite-backed append-only store with optional Postgres mirror via raw SQL."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "generation_log.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    @staticmethod
    def _utcnow() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def log_generation(
        self,
        *,
        input_payload: Any,
        output_payload: Any,
        model_name: str,
        user_id: str,
        content_type: str = "text",
        feature_endpoint: str = "chat",
        session_id: str | None = None,
        workspace_id: str = "default",
        model_version: str | None = None,
        locale: str | None = None,
        metadata: dict[str, Any] | None = None,
        input_hash: str | None = None,
        output_hash: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "log_id": str(uuid.uuid4()),
            "timestamp": self._utcnow(),
            "user_id": str(user_id or "anonymous"),
            "model_name": str(model_name or "unknown"),
            "model_version": model_version,
            "input_hash": input_hash or (
                sha256_text(input_payload)
                if isinstance(input_payload, (str, bytes))
                else sha256_json(input_payload)
            ),
            "output_hash": output_hash or (
                sha256_text(output_payload)
                if isinstance(output_payload, (str, bytes))
                else sha256_json(output_payload)
            ),
            "content_type": str(content_type or "text"),
            "feature_endpoint": str(feature_endpoint or "unknown"),
            "session_id": session_id,
            "workspace_id": workspace_id or "default",
            "locale": locale,
            "metadata": dict(metadata or {}),
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO generation_log (
                    log_id, timestamp, user_id, model_name, model_version,
                    input_hash, output_hash, content_type, feature_endpoint,
                    session_id, workspace_id, locale, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["log_id"],
                    row["timestamp"],
                    row["user_id"],
                    row["model_name"],
                    row["model_version"],
                    row["input_hash"],
                    row["output_hash"],
                    row["content_type"],
                    row["feature_endpoint"],
                    row["session_id"],
                    row["workspace_id"],
                    row["locale"],
                    json.dumps(row["metadata"], ensure_ascii=False),
                ),
            )
            conn.commit()
        self._try_postgres_insert(row)
        return row

    def _try_postgres_insert(self, row: dict[str, Any]) -> None:
        """Best-effort mirror into Postgres when the async engine is configured."""
        try:
            import asyncio

            from keprix.database import get_session_factory

            factory = get_session_factory()
            if factory is None:
                return

            async def _insert() -> None:
                from sqlalchemy import text

                async with factory() as session:
                    await session.execute(
                        text(
                            """
                            INSERT INTO generation_log (
                                log_id, timestamp, user_id, model_name, model_version,
                                input_hash, output_hash, content_type, feature_endpoint,
                                session_id, workspace_id, locale, metadata
                            ) VALUES (
                                :log_id, CAST(:timestamp AS timestamptz), :user_id, :model_name,
                                :model_version, :input_hash, :output_hash, :content_type,
                                :feature_endpoint, :session_id, :workspace_id, :locale,
                                CAST(:metadata AS jsonb)
                            )
                            ON CONFLICT (log_id) DO NOTHING
                            """
                        ),
                        {
                            **row,
                            "metadata": json.dumps(row["metadata"], ensure_ascii=False),
                        },
                    )
                    await session.commit()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(_insert())
            else:
                loop.create_task(_insert())
        except Exception as exc:  # pragma: no cover - optional path
            logger.debug("generation_log postgres mirror skipped: %s", exc)

    def update_entry(self, *_args: Any, **_kwargs: Any) -> None:
        raise ImmutableLogError("generation_log is append-only; UPDATE is forbidden")

    def delete_entry(self, *_args: Any, **_kwargs: Any) -> None:
        raise ImmutableLogError("generation_log is append-only; DELETE is forbidden")

    def query_log(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        user_id: str | None = None,
        model_name: str | None = None,
        feature_endpoint: str | None = None,
        content_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[Any] = []
        if start:
            clauses.append("timestamp >= ?")
            params.append(start)
        if end:
            clauses.append("timestamp <= ?")
            params.append(end)
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        if model_name:
            clauses.append("model_name = ?")
            params.append(model_name)
        if feature_endpoint:
            clauses.append("feature_endpoint = ?")
            params.append(feature_endpoint)
        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type)
        params.append(max(1, min(int(limit), 5000)))
        sql = (
            "SELECT * FROM generation_log WHERE "
            + " AND ".join(clauses)
            + " ORDER BY timestamp ASC LIMIT ?"
        )
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            meta = item.get("metadata")
            if isinstance(meta, str):
                try:
                    item["metadata"] = json.loads(meta)
                except json.JSONDecodeError:
                    item["metadata"] = {}
            out.append(item)
        return out

    def generate_compliance_report(
        self,
        date: str,
        *,
        workspace_id: str | None = None,
        signer: str = "keprix-transparency",
    ) -> dict[str, Any]:
        """Formal day report for regulatory audit (timestamped, signed, exportable)."""
        day = str(date).strip()[:10]
        start = f"{day}T00:00:00Z"
        end = f"{day}T23:59:59Z"
        entries = self.query_log(start=start, end=end, limit=5000)
        if workspace_id:
            entries = [e for e in entries if e.get("workspace_id") == workspace_id]
        body = {
            "report_type": "eu_ai_act_sgi_generation_log",
            "report_date": day,
            "generated_at": self._utcnow(),
            "workspace_id": workspace_id,
            "entry_count": len(entries),
            "entries": entries,
        }
        body["content_hash"] = sha256_json(
            {"report_date": day, "entry_count": body["entry_count"], "entries": entries}
        )
        body["signature"] = {
            "alg": "HMAC-SHA256-placeholder",
            "signer": signer,
            "value": sha256_text(f"{signer}:{body['content_hash']}"),
        }
        body["export_format"] = "application/json"
        return body


_store: GenerationLogStore | None = None


def get_generation_log_store() -> GenerationLogStore:
    global _store
    if _store is None:
        _store = GenerationLogStore()
    return _store
