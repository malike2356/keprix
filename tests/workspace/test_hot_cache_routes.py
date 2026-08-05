"""Prompt 278 hot cache route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_hot_cache_routes_config_refresh_and_read(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    config = client.put("/api/workspaces/demo/hot-cache/config", json={"enabled": True, "workspace_path": str(workspace)})
    assert config.status_code == 200
    assert config.json()["config"]["enabled"] is True

    refreshed = client.post(
        "/api/workspaces/demo/hot-cache/refresh",
        json={"workspace_path": str(workspace), "source_session_id": "sess-1", "recent_text": "launch priorities\nspeaker lineup"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["written"] is True

    read = client.get(f"/api/workspaces/demo/hot-cache?workspace_path={workspace}")
    assert read.status_code == 200
    assert "speaker lineup" in read.json()["content"]
