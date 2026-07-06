"""RAG MCP server adapter."""

from __future__ import annotations

import json

from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever


def build_manage_rag_tool_schema() -> dict:
    return {
        "name": "manage_rag",
        "description": "Manage RAG indexed documents: list sources, ingest text, or delete a source.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "ingest", "delete", "search"],
                },
                "source_id": {"type": "string"},
                "source_type": {"type": "string"},
                "content": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["action"],
        },
    }


class RagMcpServer:
    def __init__(self, user_id: str = "default") -> None:
        self.user_id = user_id
        self.indexer = RagIndexer()
        self.retriever = RagRetriever(indexer=self.indexer)

    async def call_tool(self, arguments: dict) -> str:
        action = arguments.get("action", "")
        if action == "list":
            sources = await self.indexer.list_sources(self.user_id)
            return json.dumps({"sources": sources})

        if action == "ingest":
            source_id = str(arguments.get("source_id", "")).strip()
            content = str(arguments.get("content", "")).strip()
            source_type = str(arguments.get("source_type", "plaintext")).strip() or "plaintext"
            if not source_id or not content:
                return "Error: ingest requires source_id and content"
            count = await self.indexer.ingest(
                user_id=self.user_id,
                source_type=source_type,
                source_id=source_id,
                content=content,
            )
            return json.dumps({"ok": True, "chunks": count})

        if action == "delete":
            source_id = str(arguments.get("source_id", "")).strip()
            if not source_id:
                return "Error: delete requires source_id"
            deleted = await self.indexer.delete_source(self.user_id, source_id)
            return json.dumps({"ok": True, "deleted_chunks": deleted})

        if action == "search":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return "Error: search requires query"
            results = await self.retriever.hybrid_search(self.user_id, query, limit=5)
            return json.dumps({"results": results})

        return f"Error: unknown action {action!r}"
