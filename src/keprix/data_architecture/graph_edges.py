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
