"""Prompt 269 Graphiti bridge tests."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.error

from keprix.brain.graphiti_bridge import GraphitiBridge


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_graphiti_status_uses_builtin_when_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("GRAPHITI_MCP_URL", raising=False)

    status = GraphitiBridge().status()
    assert status["status"] == "connected"
    assert status["backend"] == "builtin"


def test_builtin_ingest_and_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("GRAPHITI_MCP_URL", raising=False)
    bridge = GraphitiBridge()

    created = bridge.add_episode(name="manual:note", content="Alpha competes with Beta", source_ref="note")
    assert created["episode_id"]
    assert created["nodes_added"] > 0

    result = bridge.query("Alpha")
    assert result["hits"]
    assert "Alpha" in result["hits"][0]["fact"] or "alpha" in result["hits"][0]["fact"].lower()


def test_graphiti_bridge_wraps_search(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict, headers: dict | None = None):
            self.payload = payload
            self.headers = headers or {"mcp-session-id": "test-session"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        calls.append(payload)
        method = payload.get("method")
        if method == "initialize":
            return FakeResponse({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}})
        if method == "notifications/initialized":
            return FakeResponse({})
        if method == "tools/call":
            name = (payload.get("params") or {}).get("name")
            if name == "search_memory_facts":
                return FakeResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "result": {
                            "structuredContent": {"result": {"facts": [{"fact": "alpha"}]}},
                            "isError": False,
                        },
                    }
                )
            if name == "search_nodes":
                return FakeResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "result": {"structuredContent": {"result": {"nodes": []}}, "isError": False},
                    }
                )
        return FakeResponse({"jsonrpc": "2.0", "id": 9, "result": {}})

    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://graphiti.test/mcp")
    monkeypatch.setattr("keprix.brain.graphiti_bridge.urllib.request.urlopen", fake_urlopen)

    result = GraphitiBridge().query("alpha")
    assert result["hits"][0]["fact"] == "alpha"
    assert any(call.get("method") == "tools/call" for call in calls)


def test_graphiti_status_unreachable(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("down")

    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://graphiti.test/mcp")
    monkeypatch.setattr("keprix.brain.graphiti_bridge.urllib.request.urlopen", fake_urlopen)

    assert GraphitiBridge().status()["status"] == "unreachable"