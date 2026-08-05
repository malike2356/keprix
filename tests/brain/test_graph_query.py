from pathlib import Path

import pytest

from keprix.brain.graph_query import BrainGraphQuery
from keprix.brain.node_resolvers import NodeResolver
from keprix.data_architecture.graph_edges import add_graph_edge


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))


@pytest.mark.asyncio
async def test_graph_query_loads_filters_and_tombstones() -> None:
    workspace_id = "graph-query"
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id="mem-1",
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
    )
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="memory",
        source_id="mem-1",
        target_kind="session",
        target_id="sess-1",
        relation="derived_from",
    )
    add_graph_edge(
        workspace_id=workspace_id,
        source_kind="tool",
        source_id="calendar_book",
        target_kind="session",
        target_id="sess-2",
        relation="used_in",
    )
    resolver = NodeResolver()
    resolver.seed(workspace_id, "memory", "mem-1", {"content": "Client prefers PDF invoices"})
    query = BrainGraphQuery(resolver=resolver)

    graph = await query.load(workspace_id, session_id="sess-1")
    memory_only = await query.load(workspace_id, kinds=["memory"])
    neighbours = await query.neighbours(workspace_id, "memory", "mem-1")
    depth_two = await query.neighbours(workspace_id, "memory", "mem-1", depth=2)
    search = await query.search(workspace_id, "invoices")
    stats = await query.stats(workspace_id)

    assert graph.total_edges == 1
    assert graph.edges[0].weight == 2
    assert {node.kind for node in graph.nodes} == {"memory", "session"}
    assert any(node.deleted for node in graph.nodes if node.kind == "session")
    assert memory_only.total_edges == 0
    assert neighbours.total_nodes == 2
    assert depth_two.total_nodes >= neighbours.total_nodes
    assert search[0]["id"] == "mem-1"
    assert stats["edges_by_relation"]["derived_from"] == 1
