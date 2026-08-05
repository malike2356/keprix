"""Brain health report computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from keprix.brain.coverage import detect_coverage_gaps
from keprix.brain.duplicates import find_duplicate_candidates, fuzzy_similarity
from keprix.brain.graph_query import BrainGraphQuery
from keprix.brain.graph_types import GraphNode, NodeRef
from keprix.brain.node_flags import list_archived_nodes
from keprix.brain.node_resolvers import NodeResolver
from keprix.data_architecture.graph_edges import list_graph_edges
from keprix.memory.episodic.store import create_episodic_store


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _short(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _health_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 40:
        return "Needs attention"
    return "Poor"


def compute_health_score(
    *,
    total_nodes: int,
    orphan_count: int,
    stale_count: int,
    duplicate_group_count: int,
    hub_count: int,
) -> int:
    if total_nodes <= 0:
        return 100
    orphan_pct = orphan_count / total_nodes
    stale_pct = stale_count / total_nodes
    score = 100.0
    score -= min(30.0, orphan_pct * 30.0)
    score -= min(20.0, stale_pct * 20.0)
    score -= min(25.0, duplicate_group_count * 5.0)
    score -= max(0.0, 25.0 - hub_count * 5.0)
    return max(0, min(100, int(round(score))))


@dataclass
class BrainHealthReport:
    workspace_id: str
    generated_at: datetime
    total_nodes: int = 0
    nodes_by_kind: dict[str, int] = field(default_factory=dict)
    total_edges: int = 0
    edges_by_relation: dict[str, int] = field(default_factory=dict)
    orphan_nodes: list[GraphNode] = field(default_factory=list)
    orphan_count: int = 0
    stale_nodes: list[GraphNode] = field(default_factory=list)
    stale_count: int = 0
    hub_nodes: list[GraphNode] = field(default_factory=list)
    duplicate_groups: list[list[GraphNode]] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    avg_memory_age_days: float = 0.0
    health_score: int = 100
    health_label: str = "Excellent"
    duplicate_pairs: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "generated_at": self.generated_at.isoformat(),
            "total_nodes": self.total_nodes,
            "nodes_by_kind": self.nodes_by_kind,
            "total_edges": self.total_edges,
            "edges_by_relation": self.edges_by_relation,
            "orphan_nodes": [node.to_dict() for node in self.orphan_nodes],
            "orphan_count": self.orphan_count,
            "stale_nodes": [node.to_dict() for node in self.stale_nodes],
            "stale_count": self.stale_count,
            "hub_nodes": [node.to_dict() for node in self.hub_nodes],
            "duplicate_groups": [[node.to_dict() for node in group] for group in self.duplicate_groups],
            "duplicate_pairs": self.duplicate_pairs,
            "coverage_gaps": self.coverage_gaps,
            "avg_memory_age_days": self.avg_memory_age_days,
            "health_score": self.health_score,
            "health_label": self.health_label,
        }


class BrainHealthService:
    def __init__(self, resolver: NodeResolver | None = None) -> None:
        self.query = BrainGraphQuery(resolver=resolver)
        self.resolver = resolver or NodeResolver()
        self.episodic_store = create_episodic_store()

    async def build_report(self, workspace_id: str) -> BrainHealthReport:
        graph = await self.query.load(workspace_id, limit_nodes=2000)
        archived = list_archived_nodes(workspace_id)
        edge_rows = list_graph_edges(workspace_id=workspace_id, limit=5000)

        degree: dict[tuple[str, str], int] = {}
        last_activity: dict[tuple[str, str], datetime] = {}
        edges_by_relation: dict[str, int] = {}

        for row in edge_rows:
            relation = row["relation"]
            edges_by_relation[relation] = edges_by_relation.get(relation, 0) + 1
            created_at = _parse_datetime(row.get("created_at")) or _now()
            for kind, node_id in (
                (row["source_kind"], row["source_id"]),
                (row["target_kind"], row["target_id"]),
            ):
                key = (kind, node_id)
                degree[key] = degree.get(key, 0) + 1
                current = last_activity.get(key)
                if current is None or created_at > current:
                    last_activity[key] = created_at

        node_map: dict[tuple[str, str], GraphNode] = {}
        for node in graph.nodes:
            key = (node.kind, node.id)
            if key in archived:
                continue
            node_map[key] = node

        memories = await self.episodic_store.list_all(workspace_id)
        for memory in memories:
            key = ("memory", memory.id)
            if key in archived:
                continue
            if key not in node_map:
                node_map[key] = GraphNode(
                    id=memory.id,
                    kind="memory",
                    label=_short(memory.content, 80),
                    summary=_short(memory.content, 200),
                    created_at=memory.created_at or _now(),
                    metadata=dict(memory.metadata or {}),
                    content=memory.to_dict(),
                )

        stale_cutoff = _now() - timedelta(days=30)
        orphan_nodes: list[GraphNode] = []
        stale_nodes: list[GraphNode] = []
        hub_candidates: list[tuple[int, GraphNode]] = []

        for key, node in node_map.items():
            node_degree = degree.get(key, 0)
            if node_degree == 0:
                orphan_nodes.append(node)
                continue
            last_seen = last_activity.get(key)
            if last_seen is None or last_seen < stale_cutoff:
                stale_nodes.append(node)
            hub_candidates.append((node_degree, node))

        orphan_nodes.sort(key=lambda node: node.created_at)
        stale_nodes.sort(key=lambda node: node.created_at)
        hub_candidates.sort(key=lambda item: item[0], reverse=True)
        hub_nodes = [node for _, node in hub_candidates[:10]]

        memory_nodes = [node for node in node_map.values() if node.kind == "memory"]
        duplicate_id_groups = await find_duplicate_candidates(memory_nodes)
        duplicate_groups: list[list[GraphNode]] = []
        duplicate_pairs: list[dict[str, object]] = []
        memory_by_id = {node.id: node for node in memory_nodes}
        for group_ids in duplicate_id_groups:
            group = [memory_by_id[node_id] for node_id in group_ids if node_id in memory_by_id]
            if len(group) > 1:
                duplicate_groups.append(group)
                left, right = group[0], group[1]
                duplicate_pairs.append(
                    {
                        "left": left.to_dict(),
                        "right": right.to_dict(),
                        "similarity": round(
                            fuzzy_similarity(f"{left.label} {left.summary}", f"{right.label} {right.summary}") * 100,
                            1,
                        ),
                    }
                )

        coverage_gaps = detect_coverage_gaps(memory_nodes)
        nodes_by_kind: dict[str, int] = {}
        for node in node_map.values():
            nodes_by_kind[node.kind] = nodes_by_kind.get(node.kind, 0) + 1

        memory_ages = [(_now() - node.created_at).total_seconds() / 86400 for node in memory_nodes if node.created_at]
        avg_memory_age_days = sum(memory_ages) / len(memory_ages) if memory_ages else 0.0
        total_nodes = len(node_map)
        health_score = compute_health_score(
            total_nodes=total_nodes,
            orphan_count=len(orphan_nodes),
            stale_count=len(stale_nodes),
            duplicate_group_count=len(duplicate_groups),
            hub_count=len(hub_nodes),
        )

        return BrainHealthReport(
            workspace_id=workspace_id,
            generated_at=_now(),
            total_nodes=total_nodes,
            nodes_by_kind=nodes_by_kind,
            total_edges=len(edge_rows),
            edges_by_relation=edges_by_relation,
            orphan_nodes=orphan_nodes,
            orphan_count=len(orphan_nodes),
            stale_nodes=stale_nodes,
            stale_count=len(stale_nodes),
            hub_nodes=hub_nodes,
            duplicate_groups=duplicate_groups,
            duplicate_pairs=duplicate_pairs,
            coverage_gaps=coverage_gaps,
            avg_memory_age_days=round(avg_memory_age_days, 1),
            health_score=health_score,
            health_label=_health_label(health_score),
        )

    async def delete_orphans(self, workspace_id: str) -> int:
        report = await self.build_report(workspace_id)
        deleted = 0
        for node in report.orphan_nodes:
            if node.kind == "memory":
                await self.episodic_store.delete(workspace_id, node.id)
                deleted += 1
        return deleted

    async def merge_duplicates(self, workspace_id: str, *, keep_id: str, delete_id: str) -> dict[str, int]:
        from keprix.data_architecture.graph_edges import remap_graph_node_edges

        remapped = remap_graph_node_edges(
            workspace_id=workspace_id,
            from_kind="memory",
            from_id=delete_id,
            to_kind="memory",
            to_id=keep_id,
        )
        await self.episodic_store.delete(workspace_id, delete_id)
        return {"remapped_edges": remapped, "deleted_nodes": 1}

    async def archive_stale(self, workspace_id: str, node_refs: list[tuple[str, str]]) -> int:
        from keprix.brain.node_flags import archive_nodes

        return archive_nodes(workspace_id, node_refs)
