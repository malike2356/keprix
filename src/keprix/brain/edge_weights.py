"""Edge co-occurrence weights for the brain graph."""

from __future__ import annotations

from keprix.brain.graph_types import GraphEdge


def compute_edge_weights(edges: list[GraphEdge]) -> list[GraphEdge]:
    counts: dict[tuple[str, str, str, str, str], int] = {}
    for edge in edges:
        key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
        counts[key] = counts.get(key, 0) + 1

    seen: set[tuple[str, str, str, str, str]] = set()
    weighted: list[GraphEdge] = []
    for edge in edges:
        key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
        if key in seen:
            continue
        seen.add(key)
        edge.weight = float(counts[key])
        weighted.append(edge)
    return weighted
