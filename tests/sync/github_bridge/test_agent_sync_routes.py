from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AGENT_SYNC_GITHUB_TOKEN", raising=False)


def test_agent_sync_routes_require_auth_and_settings() -> None:
    app = create_app()
    client = TestClient(app)
    unauth = client.get("/api/agent-sync/status")
    assert unauth.status_code in {401, 403}

    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u1",
        "role": "admin",
        "workspace_id": "default",
    }
    status = client.get("/api/agent-sync/status")
    assert status.status_code == 200
    assert status.json()["product"] in {"keprix", "hermes", "shared", "carina", "aiva"}

    saved = client.put(
        "/api/agent-sync/settings",
        json={
            "enabled": True,
            "owner": "malike2356",
            "repo": "agent-sync",
            "product": "keprix",
            "token": "test-token-value",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["enabled"] is True
    assert body["has_token"] or body["hasToken"]
    assert body["repo"] == "malike2356/agent-sync"
