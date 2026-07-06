"""Playbook graph builder and compiler."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from keprix.playbook.runtime.edge import EdgeCondition, PlaybookEdge
from keprix.playbook.runtime.errors import PlaybookGraphError
from keprix.playbook.runtime.node import NodeHandler, PlaybookNode

END = "__end__"


class PlaybookGraph:
    """State graph with nodes, edges, conditional branching, and subgraphs."""

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        self._nodes: dict[str, PlaybookNode] = {}
        self._edges: list[PlaybookEdge] = []
        self._entry: str | None = None
        self._subgraphs: dict[str, CompiledPlaybookGraph] = {}

    def add_node(self, name: str, handler: NodeHandler) -> None:
        if name == END:
            raise PlaybookGraphError("Node name '__end__' is reserved")
        self._nodes[name] = PlaybookNode(name, handler)
        if self._entry is None:
            self._entry = name

    def add_edge(
        self,
        source: str,
        target: str,
        condition: EdgeCondition | None = None,
    ) -> None:
        if source not in self._nodes and source not in self._subgraphs:
            raise PlaybookGraphError(f"Unknown source node '{source}'")
        if target != END and target not in self._nodes and target not in self._subgraphs:
            raise PlaybookGraphError(f"Unknown target node '{target}'")
        self._edges.append(PlaybookEdge(source, target, condition=condition))

    def add_subgraph(self, name: str, graph: PlaybookGraph) -> None:
        compiled = graph.compile()
        self._subgraphs[name] = compiled
        self._nodes[name] = PlaybookNode(name, compiled.as_node_handler())
        if self._entry is None:
            self._entry = name

    def set_entry(self, name: str) -> None:
        if name not in self._nodes:
            raise PlaybookGraphError(f"Unknown entry node '{name}'")
        self._entry = name

    def compile(self) -> CompiledPlaybookGraph:
        if not self._nodes:
            raise PlaybookGraphError("Graph has no nodes")
        if self._entry is None:
            raise PlaybookGraphError("Graph has no entry node")
        return CompiledPlaybookGraph(
            graph_id=self.graph_id,
            entry=self._entry,
            nodes=dict(self._nodes),
            edges=list(self._edges),
            subgraphs=dict(self._subgraphs),
        )


class CompiledPlaybookGraph:
    """Executable playbook graph."""

    def __init__(
        self,
        *,
        graph_id: str,
        entry: str,
        nodes: dict[str, PlaybookNode],
        edges: list[PlaybookEdge],
        subgraphs: dict[str, CompiledPlaybookGraph],
    ) -> None:
        self.graph_id = graph_id
        self.entry = entry
        self.nodes = nodes
        self.edges = edges
        self.subgraphs = subgraphs

    def next_node(self, current: str, state: dict[str, Any]) -> str | None:
        candidates: list[str] = []
        for edge in self.edges:
            if edge.source != current:
                continue
            target = edge.resolve(state)
            if target:
                candidates.append(target)
        if not candidates:
            return None
        return candidates[0]

    def as_node_handler(self) -> Callable[[dict[str, Any]], Any]:
        graph = self

        async def _run_subgraph(state: dict[str, Any]) -> dict[str, Any]:
            from keprix.playbook.runtime.runner import PlaybookRunner

            runner = PlaybookRunner(graph)
            result = await runner.execute_inline(state)
            return result.state

        return _run_subgraph
