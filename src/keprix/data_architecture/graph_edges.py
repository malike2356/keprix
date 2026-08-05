"""Retrieval graph edge helpers (Prompt 32)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.data_architecture.data_plane import get_workspace_data_plane


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_graph_table(workspace_id: str = "default") -> None:
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect(write=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retrieval_graph_edges (
                edge_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_retrieval_graph_source
            ON retrieval_graph_edges(workspace_id, source_kind, source_id)
            """
        )


def add_graph_edge(
    *,
    workspace_id: str,
    source_kind: str,
    source_id: str,
    target_kind: str,
    target_id: str,
    relation: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_graph_table(workspace_id)
    edge_id = f"edge-{uuid.uuid4().hex[:12]}"
    row = {
        "edge_id": edge_id,
        "workspace_id": workspace_id,
        "source_kind": source_kind,
        "source_id": source_id,
        "target_kind": target_kind,
        "target_id": target_id,
        "relation": relation,
        "metadata": metadata or {},
        "created_at": _utcnow(),
    }
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect(write=True) as conn:
        conn.execute(
            """
            INSERT INTO retrieval_graph_edges (
                edge_id, workspace_id, source_kind, source_id, target_kind, target_id,
                relation, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_id,
                workspace_id,
                source_kind,
                source_id,
                target_kind,
                target_id,
                relation,
                json.dumps(row["metadata"]),
                row["created_at"],
            ),
        )
    return row


def list_graph_edges(
    *,
    workspace_id: str,
    source_kind: str | None = None,
    source_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_graph_table(workspace_id)
    plane = get_workspace_data_plane(workspace_id)
    query = "SELECT * FROM retrieval_graph_edges WHERE workspace_id = ?"
    params: list[Any] = [workspace_id]
    if source_kind:
        query += " AND source_kind = ?"
        params.append(source_kind)
    if source_id:
        query += " AND source_id = ?"
        params.append(source_id)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with plane.connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "edge_id": row["edge_id"],
            "workspace_id": row["workspace_id"],
            "source_kind": row["source_kind"],
            "source_id": row["source_id"],
            "target_kind": row["target_kind"],
            "target_id": row["target_id"],
            "relation": row["relation"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def list_graph_edges_for_session(
    *,
    workspace_id: str,
    session_id: str,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    ensure_graph_table(workspace_id)
    plane = get_workspace_data_plane(workspace_id)
    query = """
        SELECT * FROM retrieval_graph_edges
        WHERE workspace_id = ?
          AND (
            (target_kind = 'session' AND target_id = ?)
            OR (source_kind = 'session' AND source_id = ?)
          )
        ORDER BY created_at ASC
        LIMIT ?
    """
    with plane.connect() as conn:
        rows = conn.execute(query, (workspace_id, session_id, session_id, limit)).fetchall()
    return [
        {
            "edge_id": row["edge_id"],
            "workspace_id": row["workspace_id"],
            "source_kind": row["source_kind"],
            "source_id": row["source_id"],
            "target_kind": row["target_kind"],
            "target_id": row["target_id"],
            "relation": row["relation"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def delete_graph_edges(
    *,
    workspace_id: str,
    source_kind: str | None = None,
    source_id: str | None = None,
    target_kind: str | None = None,
    target_id: str | None = None,
) -> int:
    ensure_graph_table(workspace_id)
    query = "DELETE FROM retrieval_graph_edges WHERE workspace_id = ?"
    params: list[Any] = [workspace_id]
    for column, value in (
        ("source_kind", source_kind),
        ("source_id", source_id),
        ("target_kind", target_kind),
        ("target_id", target_id),
    ):
        if value:
            query += f" AND {column} = ?"
            params.append(value)
    plane = get_workspace_data_plane(workspace_id)
    with plane.connect(write=True) as conn:
        cursor = conn.execute(query, params)
        return int(cursor.rowcount or 0)


def remap_graph_node_edges(
    *,
    workspace_id: str,
    from_kind: str,
    from_id: str,
    to_kind: str,
    to_id: str,
) -> int:
    ensure_graph_table(workspace_id)
    plane = get_workspace_data_plane(workspace_id)
    updated = 0
    with plane.connect(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE retrieval_graph_edges
            SET source_kind = ?, source_id = ?
            WHERE workspace_id = ? AND source_kind = ? AND source_id = ?
            """,
            (to_kind, to_id, workspace_id, from_kind, from_id),
        )
        updated += int(cursor.rowcount or 0)
        cursor = conn.execute(
            """
            UPDATE retrieval_graph_edges
            SET target_kind = ?, target_id = ?
            WHERE workspace_id = ? AND target_kind = ? AND target_id = ?
            """,
            (to_kind, to_id, workspace_id, from_kind, from_id),
        )
        updated += int(cursor.rowcount or 0)
    return updated
