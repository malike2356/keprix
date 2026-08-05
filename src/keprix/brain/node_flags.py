"""Archived and health flags for brain graph nodes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.data_architecture.data_plane import get_workspace_data_plane


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_node_flags_table(workspace_id: str = "default") -> None:
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect(write=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_node_flags (
                workspace_id TEXT NOT NULL,
                node_kind TEXT NOT NULL,
                node_id TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (workspace_id, node_kind, node_id)
            )
            """
        )


def list_archived_nodes(workspace_id: str) -> set[tuple[str, str]]:
    ensure_node_flags_table(workspace_id)
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect() as conn:
        rows = conn.execute(
            """
            SELECT node_kind, node_id
            FROM brain_node_flags
            WHERE workspace_id = ? AND archived = 1
            """,
            (workspace_id,),
        ).fetchall()
    return {(row["node_kind"], row["node_id"]) for row in rows}


def set_archived(
    workspace_id: str,
    *,
    node_kind: str,
    node_id: str,
    archived: bool,
) -> None:
    ensure_node_flags_table(workspace_id)
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect(write=True) as conn:
        conn.execute(
            """
            INSERT INTO brain_node_flags(workspace_id, node_kind, node_id, archived, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id, node_kind, node_id)
            DO UPDATE SET archived = excluded.archived, updated_at = excluded.updated_at
            """,
            (workspace_id, node_kind, node_id, 1 if archived else 0, _utcnow()),
        )


def archive_nodes(workspace_id: str, node_refs: list[tuple[str, str]]) -> int:
    for kind, node_id in node_refs:
        set_archived(workspace_id, node_kind=kind, node_id=node_id, archived=True)
    return len(node_refs)
