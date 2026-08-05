"""Full JSON export for brain graphs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.brain.graph_query import BrainGraphQuery


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_by_kind(nodes: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        counts[node.kind] = counts.get(node.kind, 0) + 1
    return counts


async def export_brain_json(workspace_id: str) -> dict[str, Any]:
    graph = await BrainGraphQuery().load(workspace_id, limit_nodes=10_000)
    return {
        "format": "keprix-brain-export",
        "version": "1.0",
        "exported_at": _utcnow(),
        "workspace_id": workspace_id,
        "nodes": [node.to_dict() for node in graph.nodes],
        "edges": [edge.to_dict() for edge in graph.edges],
        "stats": {
            "total_nodes": graph.total_nodes,
            "total_edges": graph.total_edges,
            "nodes_by_kind": _count_by_kind(graph.nodes),
        },
    }
