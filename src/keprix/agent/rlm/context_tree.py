"""Session-local context tree; never mutates the parent conversation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class ContextNode:
    kind: str
    content: Any = None
    parent_id: str | None = None
    id: str = field(default_factory=lambda: f"ctx_{uuid.uuid4().hex[:12]}")
    children: list[str] = field(default_factory=list)
    pruned: bool = False


class ContextTree:
    def __init__(self) -> None:
        self.nodes: dict[str, ContextNode] = {}
        self.root_id = f"ctx_{uuid.uuid4().hex[:12]}"
        self.nodes[self.root_id] = ContextNode(kind="root", id=self.root_id)

    def build(self, messages: list[dict[str, Any]]) -> str:
        root = self.nodes[self.root_id]
        root.children.clear()
        for message in messages:
            node = ContextNode(kind=str(message.get("role") or "message"), content=dict(message), parent_id=self.root_id)
            self.nodes[node.id] = node
            root.children.append(node.id)
        return self.root_id

    def prune(self, node_id: str) -> None:
        self.nodes[node_id].pruned = True

    def expand(self, node_id: str) -> None:
        self.nodes[node_id].pruned = False

    def subset(self, node_id: str) -> list[Any]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        out: list[Any] = []

        def visit(current_id: str) -> None:
            node = self.nodes[current_id]
            if node.pruned:
                return
            if node is not self.nodes[node_id] and node.content is not None:
                out.append(node.content)
            for child_id in node.children:
                visit(child_id)

        visit(node_id)
        return out

    def serialize(self) -> dict[str, Any]:
        return {"root_id": self.root_id, "nodes": {key: {"kind": value.kind, "parent_id": value.parent_id, "children": list(value.children), "pruned": value.pruned} for key, value in self.nodes.items()}}
