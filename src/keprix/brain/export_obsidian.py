"""Obsidian-compatible markdown ZIP export for brain graphs."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from keprix.brain.graph_query import BrainGraphQuery

EXPORTABLE_KINDS = {"memory", "skill", "session", "document", "task", "tool", "source"}


def _wikilink_path(kind: str, node_id: str) -> str:
    folder = f"{kind}s" if kind != "memory" else "memories"
    if kind == "session":
        folder = "sessions"
    return f"{folder}/{node_id}"


def _frontmatter(node) -> str:
    tags = node.metadata.get("tags") if isinstance(node.metadata.get("tags"), list) else []
    payload = {
        "kind": node.kind,
        "id": node.id,
        "created": node.created_at.isoformat(),
        "tags": tags,
    }
    lines = ["---"]
    for key, value in payload.items():
        if isinstance(value, list):
            rendered = json.dumps(value)
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines)


async def export_brain_obsidian(workspace_id: str) -> bytes:
    graph = await BrainGraphQuery().load(workspace_id, limit_nodes=10_000)
    labels = {(node.kind, node.id): node.label for node in graph.nodes}
    edges_by_node: dict[tuple[str, str], list] = {}
    for edge in graph.edges:
        for kind, node_id, other_kind, other_id in (
            (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id),
            (edge.target_kind, edge.target_id, edge.source_kind, edge.source_id),
        ):
            key = (kind, node_id)
            edges_by_node.setdefault(key, []).append((other_kind, other_id, edge.relation))

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for node in graph.nodes:
            if node.kind not in EXPORTABLE_KINDS:
                continue
            path = f"{_wikilink_path(node.kind, node.id)}.md"
            body = node.summary or node.label
            connections = edges_by_node.get((node.kind, node.id), [])
            sections = [body]
            if connections:
                sections.append("\n## Connected to")
                for other_kind, other_id, relation in connections:
                    target = _wikilink_path(other_kind, other_id)
                    label = labels.get((other_kind, other_id), other_id)
                    sections.append(f"- [[{target}|{label}]] ({relation})")
            content = f"{_frontmatter(node)}\n\n" + "\n".join(sections) + "\n"
            zf.writestr(path, content)
    return archive.getvalue()
