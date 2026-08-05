"""Google Workspace API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_google_workspace_status_and_callback_marks_connections(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("GOOGLE_WORKSPACE_TOKEN_PATH", str(tmp_path / "token.json"))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)
    workspace = tmp_path / "workspace"

    init = client.post("/api/agent-os/connections/init-template", json={"workspace_path": str(workspace)})
    assert init.status_code == 200

    status = client.get("/api/integrations/google-workspace/status")
    assert status.status_code == 200
    assert status.json()["connected"] is False

    callback = client.post(
        "/api/integrations/google-workspace/oauth/callback",
        json={
            "code": "oauth-code",
            "account_email": "owner@example.com",
            "workspace_path": str(workspace),
        },
    )
    assert callback.status_code == 200
    assert callback.json()["connected"] is True

    connections = client.get("/api/agent-os/connections", params={"workspace_path": str(workspace)})
    rows = {row["id"]: row for row in connections.json()["domains"]}
    assert rows["calendar"]["status"] == "live"
    assert rows["calendar"]["integration_ref"] == "google-workspace"


def test_google_workspace_start_returns_setup_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("GOOGLE_WORKSPACE_CREDENTIALS_PATH", raising=False)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    response = client.post("/api/integrations/google-workspace/oauth/start", json={})

    assert response.status_code == 400
    assert "GOOGLE_WORKSPACE_CREDENTIALS_PATH" in response.json()["detail"]
