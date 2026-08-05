"""Prompt 269 Graphiti API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


class MockBridge:
    def status(self):
        return {"status": "connected", "url": "http://graphiti.test/mcp"}

    def add_episode(self, *, name: str, content: str, source_ref: str) -> dict:
        return {"episode_id": "ep-1", "nodes_added": 1, "edges_added": 1}

    def query(self, query: str, *, max_results: int, include_sources: bool) -> dict:
        return {"hits": [{"fact": query}]}


def test_graphiti_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://graphiti.test/mcp")
    monkeypatch.setattr("keprix.api.graphiti_routes.GraphitiBridge", lambda: MockBridge())
    monkeypatch.setattr(
        "keprix.brain.graphiti_ingest_service.GraphitiBridge",
        lambda: MockBridge(),
    )
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    status = client.get("/api/brain/graphiti/status")
    assert status.status_code == 200
    assert status.json()["status"] == "connected"

    created = client.post("/api/brain/graphiti/ingest", json={"source_type": "manual", "source_ref": "note", "content": "Alpha"})
    assert created.status_code == 200
    job = created.json()["job"]
    assert job["status"] == "done"
    assert job["nodes_added"] == 1

    listed = client.get("/api/brain/graphiti/jobs")
    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["job_id"] == job["job_id"]

    detail = client.get(f"/api/brain/graphiti/jobs/{job['job_id']}")
    assert detail.status_code == 200

    query = client.post("/api/brain/graphiti/query", json={"query": "Alpha"})
    assert query.status_code == 200
    assert query.json()["ok"] is True


def test_graphiti_feature_flag_disables_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_GRAPHITI_ENABLED", "0")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    assert client.post("/api/brain/graphiti/query", json={"query": "Alpha"}).status_code == 403
