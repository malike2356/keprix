"""Prompt 277 connections API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_connections_routes_init_update_suggest_and_onboarding(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    initialized = client.post("/api/agent-os/connections/init-template", json={"workspace_path": str(workspace)})
    assert initialized.status_code == 200
    assert len(initialized.json()["domains"]) == 7

    suggested = client.post("/api/agent-os/connections/suggest-priority", json={"workspace_path": str(workspace)})
    assert suggested.status_code == 200
    assert len(suggested.json()["suggestions"]) >= 3

    updated = client.put(
        "/api/agent-os/connections",
        json={"workspace_path": str(workspace), "domain": "tasks", "status": "live", "tools": ["clickup"]},
    )
    assert updated.status_code == 200

    progress = client.get("/api/agent-os/onboarding")
    assert progress.status_code == 200
    assert progress.json()["steps"]["l2_connect_one"] is True
