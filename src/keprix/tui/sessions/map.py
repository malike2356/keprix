"""Compact session relationship map for the TUI sidebar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from keprix.tui.client import SessionItem

SessionRelation = Literal["current", "pinned", "forked", "resumed", "related", "search", "recent", "flat"]


@dataclass(frozen=True)
class SessionMapNode:
    id: str
    title: str
    preview: str = ""
    last_active: str = ""
    relation: SessionRelation = "recent"
    parent_id: str = ""
    related_ids: tuple[str, ...] = ()
    pinned: bool = False
    depth: int = 0


def _matches_query(item: SessionItem, query: str) -> bool:
    if not query:
        return False
    needle = query.casefold()
    haystack = " ".join([item.title, item.preview, item.search_match]).casefold()
    return needle in haystack


def _relation_for(item: SessionItem, *, current_session_id: str, query: str, has_relationship_data: bool) -> SessionRelation:
    if item.id == current_session_id:
        return "current"
    if item.pinned:
        return "pinned"
    if item.forked_from or item.parent_id:
        return "forked"
    if item.resumed_from:
        return "resumed"
    if item.related_ids:
        return "related"
    if _matches_query(item, query):
        return "search"
    return "recent" if has_relationship_data else "flat"


def build_session_map(
    sessions: Sequence[SessionItem],
    *,
    current_session_id: str = "",
    query: str = "",
    limit: int = 16,
) -> list[SessionMapNode]:
    has_relationship_data = any(
        item.pinned or item.parent_id or item.related_ids or item.resumed_from or item.forked_from or item.search_match
        for item in sessions
    )
    nodes: list[SessionMapNode] = []
    for item in sessions[: max(0, limit)]:
        relation = _relation_for(
            item,
            current_session_id=current_session_id,
            query=query,
            has_relationship_data=has_relationship_data,
        )
        parent_id = item.forked_from or item.parent_id or item.resumed_from
        nodes.append(
            SessionMapNode(
                id=item.id,
                title=item.title or "Conversation",
                preview=item.preview,
                last_active=item.last_active,
                relation=relation,
                parent_id=parent_id,
                related_ids=tuple(item.related_ids),
                pinned=item.pinned,
                depth=1 if parent_id else 0,
            )
        )
    return nodes


def render_session_map(nodes: Sequence[SessionMapNode], *, width: int = 34, selected_id: str = "") -> str:
    if not nodes:
        return "Session map\nNo sessions yet."

    labels: dict[SessionRelation, str] = {
        "current": "current",
        "pinned": "pinned",
        "forked": "fork",
        "resumed": "resume",
        "related": "related",
        "search": "match",
        "recent": "recent",
        "flat": "recent",
    }
    rows = ["Session map"]
    body_width = max(12, width - 4)
    for node in nodes:
        marker = ">" if node.id == selected_id or node.relation == "current" else " "
        branch = "  " if node.depth else ""
        label = labels[node.relation]
        title = node.title.replace("\n", " ").strip() or "Conversation"
        preview = node.preview.replace("\n", " ").strip()
        title = title[:body_width]
        meta = node.last_active[:16] if node.last_active else label
        rows.append(f"{marker} {branch}{title}")
        detail = preview[:body_width] if preview else meta
        rows.append(f"  {branch}{label}: {detail}")
    return "\n".join(rows)


class SessionMapNavigator:
    def __init__(self, nodes: Sequence[SessionMapNode], *, selected_id: str = "") -> None:
        self.nodes = list(nodes)
        self.index = 0
        if selected_id:
            for index, node in enumerate(self.nodes):
                if node.id == selected_id:
                    self.index = index
                    break

    def move(self, step: int) -> SessionMapNode | None:
        if not self.nodes:
            return None
        self.index = (self.index + step) % len(self.nodes)
        return self.selected()

    def selected(self) -> SessionMapNode | None:
        if not self.nodes:
            return None
        return self.nodes[self.index]

    def select(self, session_id: str) -> SessionMapNode | None:
        for index, node in enumerate(self.nodes):
            if node.id == session_id:
                self.index = index
                return node
        return None
