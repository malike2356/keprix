"""Capability graph loader and query helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

NodeStatus = Literal["wired", "partial", "ui_only", "exception"]
ChannelSurface = str


class CapabilityGraphError(ValueError):
    pass


@dataclass(frozen=True)
class CapabilityNode:
    id: str
    label: str
    nav_id: str | None = None
    tools: tuple[str, ...] = ()
    channel_surfaces: tuple[str, ...] = ()
    object_types: tuple[str, ...] = ()
    status: NodeStatus = "ui_only"
    notes: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CapabilityNode:
        node_id = str(raw.get("id") or "").strip()
        if not node_id:
            raise CapabilityGraphError("node missing id")
        status = str(raw.get("status") or "ui_only").strip()
        if status not in {"wired", "partial", "ui_only", "exception"}:
            raise CapabilityGraphError(f"invalid status for {node_id}: {status}")
        return cls(
            id=node_id,
            label=str(raw.get("label") or node_id),
            nav_id=(str(raw["nav_id"]).strip() if raw.get("nav_id") else None),
            tools=tuple(str(t) for t in (raw.get("tools") or [])),
            channel_surfaces=tuple(str(s) for s in (raw.get("channel_surfaces") or [])),
            object_types=tuple(str(o) for o in (raw.get("object_types") or [])),
            status=status,  # type: ignore[arg-type]
            notes=(str(raw["notes"]) if raw.get("notes") is not None else None),
        )


@dataclass(frozen=True)
class CapabilityEdge:
    from_id: str
    to_id: str
    relation: str
    via_id_field: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CapabilityEdge:
        frm = str(raw.get("from") or "").strip()
        to = str(raw.get("to") or "").strip()
        relation = str(raw.get("relation") or "").strip()
        if not frm or not to or not relation:
            raise CapabilityGraphError("edge requires from, to, relation")
        via = raw.get("via_id_field")
        return cls(
            from_id=frm,
            to_id=to,
            relation=relation,
            via_id_field=(str(via).strip() if via else None),
        )


@dataclass
class CapabilityGraph:
    version: int
    nodes: dict[str, CapabilityNode] = field(default_factory=dict)
    edges: list[CapabilityEdge] = field(default_factory=list)
    updated: str | None = None
    description: str | None = None

    def get_node(self, node_id: str) -> CapabilityNode:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise CapabilityGraphError(f"unknown node: {node_id}") from exc

    def neighbors(self, node_id: str, *, direction: str = "out") -> list[tuple[CapabilityEdge, CapabilityNode]]:
        self.get_node(node_id)
        out: list[tuple[CapabilityEdge, CapabilityNode]] = []
        for edge in self.edges:
            if direction in {"out", "both"} and edge.from_id == node_id:
                out.append((edge, self.get_node(edge.to_id)))
            if direction in {"in", "both"} and edge.to_id == node_id:
                out.append((edge, self.get_node(edge.from_id)))
        return out

    def tools_for(self, node_id: str) -> tuple[str, ...]:
        return self.get_node(node_id).tools

    def channel_ready(self, channel: str, *, require_wired: bool = False) -> list[CapabilityNode]:
        channel = channel.strip().lower()
        rows: list[CapabilityNode] = []
        for node in self.nodes.values():
            if channel not in {s.lower() for s in node.channel_surfaces}:
                continue
            if require_wired and node.status != "wired":
                continue
            rows.append(node)
        return sorted(rows, key=lambda n: n.id)

    def validate(self) -> None:
        if not self.nodes:
            raise CapabilityGraphError("graph has no nodes")
        seen: set[str] = set()
        for node_id in self.nodes:
            if node_id in seen:
                raise CapabilityGraphError(f"duplicate node id: {node_id}")
            seen.add(node_id)
        for edge in self.edges:
            if edge.from_id not in self.nodes:
                raise CapabilityGraphError(f"dangling edge from: {edge.from_id}")
            if edge.to_id not in self.nodes:
                raise CapabilityGraphError(f"dangling edge to: {edge.to_id}")


def default_graph_path() -> Path:
    return Path(__file__).resolve().parent / "capability_graph.yaml"


def load_graph(path: Path | str | None = None) -> CapabilityGraph:
    graph_path = Path(path) if path else default_graph_path()
    if not graph_path.is_file():
        raise CapabilityGraphError(f"graph file not found: {graph_path}")
    raw = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CapabilityGraphError("graph root must be a mapping")
    nodes_raw = raw.get("nodes") or []
    edges_raw = raw.get("edges") or []
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        raise CapabilityGraphError("nodes and edges must be lists")

    nodes: dict[str, CapabilityNode] = {}
    for item in nodes_raw:
        if not isinstance(item, dict):
            raise CapabilityGraphError("each node must be a mapping")
        node = CapabilityNode.from_dict(item)
        if node.id in nodes:
            raise CapabilityGraphError(f"duplicate node id: {node.id}")
        nodes[node.id] = node

    edges: list[CapabilityEdge] = []
    for item in edges_raw:
        if not isinstance(item, dict):
            raise CapabilityGraphError("each edge must be a mapping")
        edges.append(CapabilityEdge.from_dict(item))

    graph = CapabilityGraph(
        version=int(raw.get("version") or 1),
        nodes=nodes,
        edges=edges,
        updated=(str(raw["updated"]) if raw.get("updated") is not None else None),
        description=(str(raw["description"]) if raw.get("description") is not None else None),
    )
    graph.validate()
    return graph


def iter_seed_required_ids() -> Iterable[str]:
    return (
        "home",
        "chat",
        "calendar",
        "vical",
        "contacts",
        "companies-house",
        "memory",
        "playbooks",
        "cron",
        "vault",
    )
