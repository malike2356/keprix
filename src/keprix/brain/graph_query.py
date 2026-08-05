"""Brain graph query engine over retrieval graph edges."""

from __future__ import annotations

from datetime import datetime

from keprix.brain.edge_weights import compute_edge_weights
from keprix.brain.graph_types import BrainGraphData, GraphEdge, NODE_KINDS, NodeRef
from keprix.brain.memory_graph_sync import MEMORY_HUB_SESSION_ID, build_memory_overlay_edges
from keprix.brain.node_flags import list_archived_nodes
from keprix.brain.node_resolvers import NodeResolver
from keprix.data_architecture.graph_edges import list_graph_edges


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BrainGraphQuery:
    def __init__(self, resolver: NodeResolver | None = None) -> None:
        self.resolver = resolver or NodeResolver()

    async def load(
        self,
        workspace_id: str,
        *,
        kinds: list[str] | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        limit_nodes: int = 500,
        include_archived: bool = False,
        owner_user_id: str | None = None,
        include_memory_overlay: bool = True,
    ) -> BrainGraphData:
        allowed = set(kinds or NODE_KINDS)
        # Keep the Memory vault anchor visible when filtering to memories/entities only.
        if kinds and (("memory" in allowed) or ("entity" in allowed)):
            allowed = set(allowed) | {"session"}
        owners = [uid for uid in (owner_user_id, workspace_id, "default") if uid]
        self.resolver.owner_user_ids = list(dict.fromkeys(owners))
        edges = await self._load_edges(workspace_id, kinds=list(allowed), session_id=session_id, since=since)
        if include_memory_overlay and not session_id:
            # Only skip overlay when filtering to a live chat session replay.
            overlay = await build_memory_overlay_edges(workspace_id, self.resolver.owner_user_ids)
            if kinds:
                overlay = [
                    edge
                    for edge in overlay
                    if (
                        edge.source_kind in allowed
                        and (
                            edge.target_kind in allowed
                            or (
                                edge.target_kind == "session"
                                and edge.target_id == MEMORY_HUB_SESSION_ID
                            )
                        )
                    )
                ]
            edges = self._merge_edges(edges, overlay)
        refs = self._collect_node_ids(edges)
        if not include_archived:
            archived = list_archived_nodes(workspace_id)
            refs = {ref for ref in refs if (ref.kind, ref.id) not in archived}
            edges = [
                edge
                for edge in edges
                if (edge.source_kind, edge.source_id) not in archived and (edge.target_kind, edge.target_id) not in archived
            ]
        if kinds:
            refs = {
                ref
                for ref in refs
                if ref.kind in allowed
                or (ref.kind == "session" and ref.id == MEMORY_HUB_SESSION_ID)
            }
            edges = [
                edge
                for edge in edges
                if edge.source_kind in allowed
                and (
                    edge.target_kind in allowed
                    or (edge.target_kind == "session" and edge.target_id == MEMORY_HUB_SESSION_ID)
                )
            ]
        truncated = len(refs) > limit_nodes
        limited_refs = set(sorted(refs, key=lambda ref: (ref.kind, ref.id))[:limit_nodes])
        nodes = await self._resolve_nodes(workspace_id, limited_refs)
        limited_keys = {(ref.kind, ref.id) for ref in limited_refs}
        edges = [
            edge
            for edge in edges
            if (edge.source_kind, edge.source_id) in limited_keys and (edge.target_kind, edge.target_id) in limited_keys
        ]
        edges = compute_edge_weights(edges)
        return BrainGraphData(nodes=nodes, edges=edges, total_nodes=len(nodes), total_edges=len(edges), truncated=truncated)

    async def neighbours(
        self,
        workspace_id: str,
        kind: str,
        node_id: str,
        *,
        depth: int = 1,
        owner_user_id: str | None = None,
    ) -> BrainGraphData:
        graph = await self.load(workspace_id, limit_nodes=2000, owner_user_id=owner_user_id)
        frontier = {NodeRef(kind, node_id)}
        refs = set(frontier)
        connected_edges: list[GraphEdge] = []
        for _ in range(max(1, min(depth, 3))):
            next_frontier: set[NodeRef] = set()
            for edge in graph.edges:
                source = NodeRef(edge.source_kind, edge.source_id)
                target = NodeRef(edge.target_kind, edge.target_id)
                if source in frontier or target in frontier:
                    connected_edges.append(edge)
                    if len(refs) < 100:
                        next_frontier.add(source)
                        next_frontier.add(target)
            next_frontier -= refs
            refs |= next_frontier
            frontier = next_frontier
            if not frontier:
                break
        connected_edges = compute_edge_weights(connected_edges)
        nodes = await self._resolve_nodes(workspace_id, refs)
        return BrainGraphData(nodes=nodes, edges=connected_edges, total_nodes=len(nodes), total_edges=len(connected_edges))

    async def search(
        self,
        workspace_id: str,
        query: str,
        *,
        kinds: list[str] | None = None,
        limit: int = 50,
        owner_user_id: str | None = None,
    ) -> list[dict[str, str]]:
        needle = query.lower().strip()
        if not needle:
            return []
        graph = await self.load(workspace_id, kinds=kinds, limit_nodes=2000, owner_user_id=owner_user_id)
        matches: list[dict[str, str]] = []
        for node in graph.nodes:
            haystack = f"{node.label} {node.summary} {node.metadata}".lower()
            if needle not in haystack:
                continue
            source = f"{node.label} {node.summary}"
            at = max(0, source.lower().find(needle))
            excerpt = source[max(0, at - 50): at + len(needle) + 50].strip()
            matches.append({"id": node.id, "kind": node.kind, "label": node.label, "excerpt": excerpt})
            if len(matches) >= limit:
                break
        return matches

    async def stats(self, workspace_id: str, *, owner_user_id: str | None = None) -> dict[str, dict[str, int]]:
        graph = await self.load(workspace_id, limit_nodes=2000, owner_user_id=owner_user_id)
        node_counts: dict[str, int] = {}
        relation_counts: dict[str, int] = {}
        for node in graph.nodes:
            node_counts[node.kind] = node_counts.get(node.kind, 0) + 1
        for edge in graph.edges:
            relation_counts[edge.relation] = relation_counts.get(edge.relation, 0) + 1
        return {"nodes_by_kind": node_counts, "edges_by_relation": relation_counts}

    async def _load_edges(
        self,
        workspace_id: str,
        *,
        kinds: list[str] | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
    ) -> list[GraphEdge]:
        rows = list_graph_edges(workspace_id=workspace_id, limit=5000)
        allowed = set(kinds or NODE_KINDS)
        edges: list[GraphEdge] = []
        for row in rows:
            created_at = _parse_datetime(row.get("created_at"))
            if since and created_at and created_at < since:
                continue
            if row["source_kind"] not in allowed or row["target_kind"] not in allowed:
                continue
            if session_id and not (
                (row["source_kind"] == "session" and row["source_id"] == session_id)
                or (row["target_kind"] == "session" and row["target_id"] == session_id)
            ):
                continue
            # Drop self-loops (e.g. legacy SESSION_LINKED session->session rows).
            if row["source_kind"] == row["target_kind"] and row["source_id"] == row["target_id"]:
                continue
            edges.append(
                GraphEdge(
                    edge_id=row["edge_id"],
                    source_kind=row["source_kind"],
                    source_id=row["source_id"],
                    target_kind=row["target_kind"],
                    target_id=row["target_id"],
                    relation=row["relation"],
                    created_at=created_at or datetime.now(),
                    metadata=dict(row.get("metadata") or {}),
                )
            )
        return edges

    def _collect_node_ids(self, edges: list[GraphEdge]) -> set[NodeRef]:
        refs: set[NodeRef] = set()
        for edge in edges:
            refs.add(NodeRef(edge.source_kind, edge.source_id))
            refs.add(NodeRef(edge.target_kind, edge.target_id))
        return refs

    @staticmethod
    def _merge_edges(primary: list[GraphEdge], overlay: list[GraphEdge]) -> list[GraphEdge]:
        seen: set[tuple[str, str, str, str, str]] = set()
        merged: list[GraphEdge] = []
        for edge in [*primary, *overlay]:
            key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
            if key in seen:
                continue
            seen.add(key)
            merged.append(edge)
        return merged

    async def _resolve_nodes(self, workspace_id: str, node_refs: set[NodeRef]) -> list:
        nodes = []
        for ref in sorted(node_refs, key=lambda item: (item.kind, item.id)):
            resolved = await self.resolver.resolve(workspace_id, ref.kind, ref.id)
            nodes.append(resolved or self.resolver.tombstone(ref.kind, ref.id))
        return nodes
