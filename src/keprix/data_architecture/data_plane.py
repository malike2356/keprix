"""Portable SQLite workspace data plane."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from keprix.data_architecture.migrations import (
    DATA_PLANE_DDL,
    DATA_PLANE_SCHEMA_VERSION,
    RESEARCH_WORKSPACE_V2_DDL,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_data_dir(workspace_id: str = "default") -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "workspaces" / workspace_id
    except Exception:
        root = Path.home() / ".keprix" / "workspaces" / workspace_id
    root.mkdir(parents=True, exist_ok=True)
    return root


class WorkspaceDataPlane:
    def __init__(self, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.root = workspace_data_dir(workspace_id)
        self.db_path = self.root / "data_plane.sqlite"

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(DATA_PLANE_DDL)
            row = conn.execute("SELECT version FROM schema_migrations LIMIT 1").fetchone()
            version = int(row[0]) if row else 0
            if row is None:
                conn.execute("INSERT INTO schema_migrations(version) VALUES (1)")
                version = 1
            if version < DATA_PLANE_SCHEMA_VERSION:
                if version < 2:
                    self._migrate_research_workspace_v2(conn)
                conn.execute(
                    "UPDATE schema_migrations SET version = ?",
                    (DATA_PLANE_SCHEMA_VERSION,),
                )

    def _migrate_research_workspace_v2(self, conn: sqlite3.Connection) -> None:
        conn.executescript(RESEARCH_WORKSPACE_V2_DDL)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(research_projects)").fetchall()}
        additions = {
            "owner": "TEXT NOT NULL DEFAULT 'default'",
            "trace_id": "TEXT",
            "sensitivity_level": "TEXT NOT NULL DEFAULT 'internal'",
            "export_policy": "TEXT NOT NULL DEFAULT 'allow'",
            "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE research_projects ADD COLUMN {name} {ddl}")
        source_columns = {row[1] for row in conn.execute("PRAGMA table_info(research_sources)").fetchall()}
        for name, ddl in {
            "owner": "TEXT NOT NULL DEFAULT 'default'",
            "trace_id": "TEXT",
            "sensitivity_level": "TEXT NOT NULL DEFAULT 'internal'",
            "export_policy": "TEXT NOT NULL DEFAULT 'allow'",
        }.items():
            if name not in source_columns:
                conn.execute(f"ALTER TABLE research_sources ADD COLUMN {name} {ddl}")
        claim_columns = {row[1] for row in conn.execute("PRAGMA table_info(research_claims)").fetchall()}
        for name, ddl in {
            "owner": "TEXT NOT NULL DEFAULT 'default'",
            "trace_id": "TEXT",
        }.items():
            if name not in claim_columns:
                conn.execute(f"ALTER TABLE research_claims ADD COLUMN {name} {ddl}")

    @contextmanager
    def connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        self.root.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        if write:
            conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            if write:
                conn.commit()
        except Exception:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def backup(self, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, dest)
        return dest

    def restore(self, source: Path) -> None:
        shutil.copy2(source, self.db_path)

    def integrity_check(self) -> dict[str, Any]:
        with self.connect() as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            ok = result is not None and result[0] == "ok"
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            ]
        return {"ok": ok, "tables": tables, "db_path": str(self.db_path)}

    def register_dataset_version(
        self,
        *,
        dataset_id: str,
        name: str,
        fmt: str,
        path: str,
        db_path: str | None,
        engine: str | None,
        row_count: int | None,
        lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        version_id = f"{dataset_id}-v1"
        now = _utcnow()
        with self.connect(write=True) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dataset_catalog
                (dataset_id, workspace_id, name, format, path, db_path, engine, row_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dataset_id, self.workspace_id, name, fmt, path, db_path, engine, row_count, now),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO dataset_versions
                (version_id, dataset_id, version_number, path, row_count, lineage_json, created_at)
                VALUES (?, ?, 1, ?, ?, ?, ?)
                """,
                (version_id, dataset_id, path, row_count, json.dumps(lineage or {}), now),
            )
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "workspace_id": self.workspace_id,
            "row_count": row_count,
        }

    def list_dataset_versions(self, dataset_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT version_id, dataset_id, version_number, path, row_count, lineage_json, created_at
                FROM dataset_versions WHERE dataset_id = ? ORDER BY version_number DESC
                """,
                (dataset_id,),
            ).fetchall()
        return [
            {
                "version_id": row["version_id"],
                "dataset_id": row["dataset_id"],
                "version_number": row["version_number"],
                "path": row["path"],
                "row_count": row["row_count"],
                "lineage": json.loads(row["lineage_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


_planes: dict[str, WorkspaceDataPlane] = {}


def get_workspace_data_plane(workspace_id: str = "default") -> WorkspaceDataPlane:
    plane = _planes.get(workspace_id)
    if plane is None:
        plane = WorkspaceDataPlane(workspace_id)
        plane.initialize()
        _planes[workspace_id] = plane
    return plane
