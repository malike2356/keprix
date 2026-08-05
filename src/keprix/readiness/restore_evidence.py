"""Restore-test evidence tracking for recovery readiness."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS restore_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    backup_id TEXT,
    ok INTEGER NOT NULL,
    restored_files INTEGER NOT NULL DEFAULT 0,
    encrypted INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
"""


class RestoreEvidenceStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "restore_evidence.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def record(
        self,
        *,
        ok: bool,
        backup_id: str | None = None,
        restored_files: int = 0,
        encrypted: bool = False,
        note: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "created_at": time.time(),
            "backup_id": backup_id,
            "ok": bool(ok),
            "restored_files": int(restored_files),
            "encrypted": bool(encrypted),
            "note": note,
            "detail": detail or {},
        }
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO restore_evidence (
                    created_at, backup_id, ok, restored_files, encrypted, note, detail_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["created_at"],
                    row["backup_id"],
                    1 if row["ok"] else 0,
                    row["restored_files"],
                    1 if row["encrypted"] else 0,
                    row["note"],
                    json.dumps(row["detail"]),
                ),
            )
            conn.commit()
        return row

    def latest(self) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT created_at, backup_id, ok, restored_files, encrypted, note, detail_json
                FROM restore_evidence
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        try:
            detail = json.loads(row[6] or "{}")
        except Exception:
            detail = {}
        return {
            "created_at": row[0],
            "backup_id": row[1],
            "ok": bool(row[2]),
            "restored_files": row[3],
            "encrypted": bool(row[4]),
            "note": row[5],
            "detail": detail,
        }

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT created_at, backup_id, ok, restored_files, encrypted, note, detail_json
                FROM restore_evidence
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, min(int(limit), 100)),),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                detail = json.loads(row[6] or "{}")
            except Exception:
                detail = {}
            out.append(
                {
                    "created_at": row[0],
                    "backup_id": row[1],
                    "ok": bool(row[2]),
                    "restored_files": row[3],
                    "encrypted": bool(row[4]),
                    "note": row[5],
                    "detail": detail,
                }
            )
        return out


_store: RestoreEvidenceStore | None = None


def get_restore_evidence_store() -> RestoreEvidenceStore:
    global _store
    if _store is None:
        _store = RestoreEvidenceStore()
    return _store


def reset_restore_evidence_store_for_tests(store: RestoreEvidenceStore | None = None) -> RestoreEvidenceStore:
    global _store
    _store = store if store is not None else RestoreEvidenceStore()
    return _store
