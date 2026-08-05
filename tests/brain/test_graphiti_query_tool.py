"""Prompt 269 graphiti_query tool tests."""

from __future__ import annotations

import json

from keprix.tools.graphiti_query import graphiti_query_handler


def test_graphiti_query_tool_returns_structured_json(monkeypatch) -> None:
    class MockService:
        def query(self, query: str, *, max_results: int, include_sources: bool):
            return {"ok": True, "hits": [{"fact": query, "source": "s1"}]}

    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://graphiti.test/mcp")
    monkeypatch.setattr("keprix.tools.graphiti_query.GraphitiIngestService", lambda: MockService())

    payload = json.loads(graphiti_query_handler({"query": "competitor", "max_results": 5}))

    assert payload["ok"] is True
    assert payload["hits"][0]["fact"] == "competitor"


def test_graphiti_query_tool_requires_query() -> None:
    payload = json.loads(graphiti_query_handler({"query": ""}))

    assert payload["ok"] is False
