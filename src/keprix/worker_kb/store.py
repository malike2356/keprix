"""SQLite metadata store for worker knowledge bases (K03)."""

from __future__ import annotations

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

        root = Path(data_dir()) / "worker_kb"
    except Exception:
        root = Path.home() / ".keprix" / "worker_kb"
    root.mkdir(parents=True, exist_ok=True)
    return root


SCHEMA = """
CREATE TABLE IF NOT EXISTS worker_knowledge_bases (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, worker_id, name)
);

CREATE TABLE IF NOT EXISTS worker_knowledge_entries (
    id TEXT PRIMARY KEY,
    knowledge_base_id TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    source TEXT,
    source_file TEXT,
    token_count INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_worker_kb_ws_worker ON worker_knowledge_bases(workspace_id, worker_id);
CREATE INDEX IF NOT EXISTS ix_worker_kb_entries_kb ON worker_knowledge_entries(knowledge_base_id);
"""


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if "enabled" in data and data["enabled"] is not None:
        data["enabled"] = bool(data["enabled"])
    return data


class WorkerKbStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_data_root() / "worker_kb.sqlite")
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

    def get_or_create_kb(
        self,
        workspace_id: str,
        worker_id: str,
        name: str = "Default",
    ) -> dict[str, Any]:
        existing = self._one(
            """
            SELECT * FROM worker_knowledge_bases
            WHERE workspace_id = ? AND worker_id = ? AND name = ?
            """,
            (workspace_id, worker_id, name),
        )
        if existing:
            return existing
        kb_id = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO worker_knowledge_bases (id, workspace_id, worker_id, name, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (kb_id, workspace_id, worker_id, name, now),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                existing = self._one(
                    """
                    SELECT * FROM worker_knowledge_bases
                    WHERE workspace_id = ? AND worker_id = ? AND name = ?
                    """,
                    (workspace_id, worker_id, name),
                )
                if existing:
                    return existing
                raise
        return self._one("SELECT * FROM worker_knowledge_bases WHERE id = ?", (kb_id,))  # type: ignore[return-value]

    def get_kb(self, kb_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM worker_knowledge_bases WHERE id = ?", (kb_id,))

    def get_kb_for_worker(self, workspace_id: str, worker_id: str, name: str = "Default") -> dict[str, Any] | None:
        return self._one(
            """
            SELECT * FROM worker_knowledge_bases
            WHERE workspace_id = ? AND worker_id = ? AND name = ?
            """,
            (workspace_id, worker_id, name),
        )

    def add_entry(
        self,
        knowledge_base_id: str,
        *,
        entry_type: str,
        content: str,
        title: str | None = None,
        source: str | None = None,
        source_file: str | None = None,
        token_count: int | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        entry_id = str(uuid.uuid4())
        now = _utcnow()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO worker_knowledge_entries (
                    id, knowledge_base_id, entry_type, title, content, source, source_file,
                    token_count, enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    knowledge_base_id,
                    entry_type,
                    title,
                    content,
                    source,
                    source_file,
                    token_count,
                    1 if enabled else 0,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return self.get_entry(entry_id)  # type: ignore[return-value]

    def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM worker_knowledge_entries WHERE id = ?", (entry_id,))

    def list_entries(
        self,
        knowledge_base_id: str,
        *,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        if enabled_only:
            return self._all(
                """
                SELECT * FROM worker_knowledge_entries
                WHERE knowledge_base_id = ? AND enabled = 1
                ORDER BY updated_at DESC
                """,
                (knowledge_base_id,),
            )
        return self._all(
            """
            SELECT * FROM worker_knowledge_entries
            WHERE knowledge_base_id = ?
            ORDER BY updated_at DESC
            """,
            (knowledge_base_id,),
        )

    def delete_entry(self, entry_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM worker_knowledge_entries WHERE id = ?", (entry_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def set_enabled(self, entry_id: str, enabled: bool) -> dict[str, Any] | None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE worker_knowledge_entries
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if enabled else 0, _utcnow(), entry_id),
            )
            self._conn.commit()
        return self.get_entry(entry_id)

    def resolve_entry_scope(self, entry_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT e.*, b.workspace_id, b.worker_id, b.name AS kb_name
            FROM worker_knowledge_entries e
            JOIN worker_knowledge_bases b ON b.id = e.knowledge_base_id
            WHERE e.id = ?
            """,
            (entry_id,),
        )


_store: WorkerKbStore | None = None
_lock = threading.Lock()


def get_worker_kb_store(path: Path | None = None) -> WorkerKbStore:
    global _store
    if path is not None:
        return WorkerKbStore(path=path)
    with _lock:
        if _store is None:
            _store = WorkerKbStore()
        return _store


def reset_worker_kb_store_for_tests(path: Path | None = None) -> WorkerKbStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = WorkerKbStore(path=path) if path else WorkerKbStore()
        return _store
