"""Agent-facing Graphiti query tool."""

from __future__ import annotations

import json
from typing import Any

from keprix.brain.graphiti_bridge import graphiti_enabled, graphiti_url
from keprix.brain.graphiti_ingest_service import GraphitiIngestService
from keprix.tools.registry import registry


def graphiti_available() -> bool:
    return graphiti_enabled() and bool(graphiti_url())


def graphiti_query_handler(args: dict[str, Any], **_kwargs: Any) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"ok": False, "error": "query is required"})
    result = GraphitiIngestService().query(
        query,
        max_results=int(args.get("max_results") or 10),
        include_sources=bool(args.get("include_sources", True)),
    )
    return json.dumps(result)


registry.register(
    name="graphiti_query",
    toolset="brain",
    description="Query the optional Graphiti MCP knowledge graph and return structured hits with citations when available.",
    emoji="🧠",
    requires_env=True,
    check_fn=graphiti_available,
    schema={
        "type": "function",
        "function": {
            "name": "graphiti_query",
            "description": "Query Graphiti knowledge graph memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 10},
                    "include_sources": {"type": "boolean", "default": True},
                },
                "required": ["query"],
            },
        },
    },
    handler=graphiti_query_handler,
)
