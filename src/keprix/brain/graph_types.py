"""Data contracts for the workspace brain graph API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


NODE_KINDS = {"memory", "skill", "task", "tool", "session", "document", "source", "entity"}


@dataclass(frozen=True)
class NodeRef:
    kind: str
    id: str


@dataclass
class GraphNode:
    id: str
    kind: str
    label: str
    summary: str
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    deleted: bool = False
    content: dict[str, Any] | None = None

    def to_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
            "deleted": self.deleted,
        }
        if include_content:
            payload["content"] = self.content or {}
        return payload


@dataclass
class GraphEdge:
    edge_id: str
    source_kind: str
    source_id: str
    target_kind: str
    target_id: str
    relation: str
    weight: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class BrainGraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int = 0
    total_edges: int = 0
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "truncated": self.truncated,
        }
