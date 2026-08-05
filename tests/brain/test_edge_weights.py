from datetime import datetime, timezone

from keprix.brain.edge_weights import compute_edge_weights
from keprix.brain.graph_types import GraphEdge


def test_edge_weights_collapse_repeated_pairs() -> None:
    edge = GraphEdge(
        edge_id="edge-1",
        source_kind="memory",
        source_id="mem-1",
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
        created_at=datetime.now(timezone.utc),
    )
    duplicate = GraphEdge(
        edge_id="edge-2",
        source_kind="memory",
        source_id="mem-1",
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
        created_at=datetime.now(timezone.utc),
    )

    weighted = compute_edge_weights([edge, duplicate])

    assert len(weighted) == 1
    assert weighted[0].weight == 2
