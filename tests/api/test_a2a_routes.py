"""Tests for A2A HTTP API and GUI catalog status."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.api.a2a_routes import router as a2a_router
from keprix.upgrade.gui_catalog import list_gui_modules


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_user() -> dict:
        return {"id": "u1", "username": "tester", "role": "admin"}

    from keprix.auth.dependencies import get_current_user

    app = FastAPI()
    app.include_router(a2a_router)
    app.dependency_overrides[get_current_user] = fake_user
    return TestClient(app)


def test_a2a_status_and_create_task(client: TestClient) -> None:
    status = client.get("/api/a2a/status")
    assert status.status_code == 200
    body = status.json()
    assert body["enabled"] is True
    assert body["agent_count"] >= 1

    agents = client.get("/api/a2a/agents")
    assert agents.status_code == 200
    assert any(row["id"] == "keprix-local" for row in agents.json()["agents"])

    created = client.post(
        "/api/a2a/tasks",
        json={"description": "Summarise weekly report", "agent_id": "keprix-local"},
    )
    assert created.status_code == 200
    task = created.json()["task"]
    assert task["status"] == "running"
    assert task["agent_id"] == "keprix-local"

    listed = client.get("/api/a2a/tasks")
    assert listed.status_code == 200
    assert any(row["id"] == task["id"] for row in listed.json()["tasks"])

    cancelled = client.post(f"/api/a2a/tasks/{task['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["task"]["status"] == "cancelled"


def test_partial_modules_cleared_for_completed_guis() -> None:
    modules = {mod.id: mod for mod in list_gui_modules(installed_version="0.16.0")}
    for key in ("a2a", "observability", "notion", "sso_linking"):
        assert key in modules
        assert modules[key].gui_status == "available"
        assert modules[key].gui_href
