"""Workflow 5: Memory System loop.

CAPTURE → STORE → READ → VISUALIZE against the single markdown vault.
"""

from __future__ import annotations

from typing import Any

from keprix.vault.capture import capture_conversation, ensure_default_vault
from keprix.vault.config import get_configured_provider


async def run_memory_system(
    *,
    query: str = "",
    session_id: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    config = ensure_default_vault()
    provider = get_configured_provider()

    capture_result: dict[str, Any] | None = None
    if session_id and messages:
        capture_result = await capture_conversation(
            session_id=session_id,
            messages=messages,
            title=title,
            source="memory-system",
        )

    search_hits = []
    if query.strip():
        search_hits = [item.to_dict() for item in await provider.search(query.strip())]

    try:
        conversation_files = await provider.list_files("conversations")
    except FileNotFoundError:
        conversation_files = []

    recent: list[dict[str, Any]] = []
    for entry in conversation_files:
        if entry.is_dir:
            try:
                for year_month in await provider.list_files(entry.path):
                    if year_month.is_dir:
                        try:
                            for note in await provider.list_files(year_month.path):
                                if not note.is_dir:
                                    recent.append(note.to_dict())
                        except FileNotFoundError:
                            continue
                    elif not year_month.is_dir:
                        recent.append(year_month.to_dict())
            except FileNotFoundError:
                continue
        else:
            recent.append(entry.to_dict())

    recent = sorted(recent, key=lambda item: item.get("modified_at") or "", reverse=True)[:25]
    graph = await provider.get_graph()

    markdown = [
        "# Memory system",
        "",
        f"- Vault: `{config.root_path}`",
        f"- Conversation notes indexed: {len(recent)}",
        f"- Graph nodes: {len(graph.get('nodes') or [])}",
        f"- Graph edges: {len(graph.get('edges') or [])}",
    ]
    if capture_result and capture_result.get("ok"):
        markdown.extend(["", f"Captured session note: `{capture_result.get('path')}`"])
    if query.strip():
        markdown.extend(["", f"## Search: {query.strip()}", ""])
        if search_hits:
            for hit in search_hits[:10]:
                markdown.append(f"- `{hit.get('path')}`")
        else:
            markdown.append("- No matches")
    markdown.extend(["", "## Recent conversation notes", ""])
    for note in recent[:10]:
        markdown.append(f"- `{note.get('path')}`")

    return {
        "status": "ok",
        "workflow": "memory-system",
        "vault_root": config.root_path,
        "capture": capture_result,
        "search_query": query,
        "search_results": search_hits,
        "recent_notes": recent,
        "graph": {
            "node_count": len(graph.get("nodes") or []),
            "edge_count": len(graph.get("edges") or []),
            "nodes": (graph.get("nodes") or [])[:50],
            "edges": (graph.get("edges") or [])[:100],
        },
        "output": "\n".join(markdown),
        "artifact": {
            "type": "memory_system",
            "note_count": len(recent),
            "node_count": len(graph.get("nodes") or []),
            "edge_count": len(graph.get("edges") or []),
        },
    }
