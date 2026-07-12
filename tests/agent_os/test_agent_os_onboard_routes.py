"""Prompt 276 onboard API route tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def test_agent_os_onboard_routes_complete_and_mark_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    started = client.post("/api/agent-os/onboard/start", json={"workspace_id": "demo"})
    assert started.status_code == 200
    session_id = started.json()["session"]["session_id"]

    for index in range(1, 8):
        response = client.post(f"/api/agent-os/onboard/{session_id}/answer", json={"question": index, "text": f"answer {index}"})
        assert response.status_code == 200

    completed = client.post(f"/api/agent-os/onboard/{session_id}/complete", json={})
    assert completed.status_code == 200
    assert completed.json()["session"]["status"] == "completed"

    progress = client.get("/api/agent-os/onboarding")
    assert progress.status_code == 200
    assert progress.json()["steps"]["l0_onboard"] is True
