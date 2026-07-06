"""Research handoff from analytics workspace (Prompt 197)."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.routes import router as research_workspace_router
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture(autouse=True)
def _auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")


@pytest.fixture
def research_store(tmp_path, monkeypatch):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    store = ResearchWorkspaceStore(workspace_id=plane.workspace_id)
    store.plane = plane
    monkeypatch.setattr(
        "keprix.research_workspace.store.get_workspace_data_plane",
        lambda workspace_id="default": plane,
    )

    def _get_store(workspace_id: str = "default") -> ResearchWorkspaceStore:
        return store

    monkeypatch.setattr("keprix.research_workspace.store.get_research_workspace_store", _get_store)
    monkeypatch.setattr("keprix.research_workspace.routes.get_research_workspace_store", _get_store)
    return store


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(research_workspace_router)
    return test_app


@pytest.mark.asyncio
async def test_analytics_handoff_creates_research_artifact(app, research_store) -> None:
    project = ResearchProjectService(research_store).create(title="Analytics target", owner="analyst")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/research/projects/{project.project_id}/artifacts",
            json={
                "title": "Quarterly chart",
                "summary": "Average score is 88.5",
                "chart_export": [{"x": "Alice", "y": 85}],
                "analytics_session_id": "sess-123",
            },
        )

    assert response.status_code == 200
    artifact = response.json()["artifact"]
    assert artifact["object_type"] == "analytics_artifact"
    objects = research_store.list_objects(project.project_id)
    assert any(item["object_id"] == artifact["object_id"] for item in objects)
