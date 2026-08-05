"""CSV export for brain graph nodes and edges."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Any

from keprix.brain.graph_query import BrainGraphQuery


def _edge_stats(edges: list) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], set[str]]]:
    degrees: dict[tuple[str, str], int] = defaultdict(int)
    relations: dict[tuple[str, str], set[str]] = defaultdict(set)
    for edge in edges:
        for kind, node_id in ((edge.source_kind, edge.source_id), (edge.target_kind, edge.target_id)):
            key = (kind, node_id)
            degrees[key] += 1
            relations[key].add(edge.relation)
    return degrees, relations


async def export_brain_nodes_csv(workspace_id: str) -> str:
    graph = await BrainGraphQuery().load(workspace_id, limit_nodes=10_000)
    degrees, relations = _edge_stats(graph.edges)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "kind", "label", "summary", "created_at", "edge_count", "relation_types"])
    for node in graph.nodes:
        key = (node.kind, node.id)
        writer.writerow(
            [
                node.id,
                node.kind,
                node.label,
                node.summary,
                node.created_at.isoformat(),
                degrees.get(key, 0),
                ";".join(sorted(relations.get(key, set()))),
            ]
        )
    return buffer.getvalue()


async def export_brain_edges_csv(workspace_id: str) -> str:
    graph = await BrainGraphQuery().load(workspace_id, limit_nodes=10_000)
    labels = {(node.kind, node.id): node.label for node in graph.nodes}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "edge_id",
            "source_kind",
            "source_id",
            "source_label",
            "target_kind",
            "target_id",
            "target_label",
            "relation",
            "weight",
            "created_at",
        ]
    )
    for edge in graph.edges:
        writer.writerow(
            [
                edge.edge_id,
                edge.source_kind,
                edge.source_id,
                labels.get((edge.source_kind, edge.source_id), edge.source_id),
                edge.target_kind,
                edge.target_id,
                labels.get((edge.target_kind, edge.target_id), edge.target_id),
                edge.relation,
                edge.weight,
                edge.created_at.isoformat(),
            ]
        )
    return buffer.getvalue()
