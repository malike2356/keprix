"""Memory MCP server (ported from Odysseus)."""

from __future__ import annotations

import json
import os


def build_manage_memory_tool_schema() -> dict:
    return {
        "name": "manage_memory",
        "description": "Manage the user's memory system: list, add, edit, delete, or search memories.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "add", "edit", "delete", "search"],
                },
                "text": {"type": "string"},
                "memory_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["action"],
        },
    }


class MemoryMcpServer:
    """Lightweight MCP-compatible memory adapter for external clients."""

    def __init__(self, store=None, owner: str | None = None) -> None:
        from keprix.memory.episodic.store import create_episodic_store

        self.store = store or create_episodic_store()
        self.owner = owner or os.getenv("KEPRIX_MCP_MEMORY_OWNER", "default")

    async def call_tool(self, arguments: dict) -> str:
        action = arguments.get("action", "")
        if action == "list":
            memories = await self.store.list_all(self.owner)
            if not memories:
                return "No memories found."
            lines = [f"Found {len(memories)} memory entries:"]
            for memory in memories:
                lines.append(f"- [{memory.id}] {memory.content}")
            return "\n".join(lines)

        if action == "add":
            text = str(arguments.get("text", "")).strip()
            if not text:
                return "Error: add requires text"
            memory_id = await self.store.save(
                self.owner,
                text,
                metadata={"tags": arguments.get("tags") or []},
            )
            return json.dumps({"ok": True, "memory_id": memory_id})

        if action == "delete":
            memory_id = str(arguments.get("memory_id", "")).strip()
            if not memory_id:
                return "Error: delete requires memory_id"
            await self.store.delete(self.owner, memory_id)
            return json.dumps({"ok": True})

        if action == "search":
            query = str(arguments.get("text", "")).strip()
            if not query:
                return "Error: search requires text"
            results = await self.store.search(self.owner, query, limit=10)
            if not results:
                return "No matching memories."
            lines = [f"Found {len(results)} matches:"]
            for result in results:
                score = f" ({result.score:.3f})" if result.score is not None else ""
                lines.append(f"- {result.content}{score}")
            return "\n".join(lines)

        return f"Error: unknown action {action!r}"
