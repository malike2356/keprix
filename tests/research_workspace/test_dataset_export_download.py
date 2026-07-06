"""Dataset export download route tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.datasets.dataset import DatasetManager
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
    monkeypatch.setattr("keprix.research_workspace.store.get_research_workspace_store", lambda: store)
    monkeypatch.setattr(
        "keprix.research_workspace.dataset_routes.get_research_workspace_store",
        lambda: store,
    )
    monkeypatch.setattr(
        "keprix.research_workspace.pspp_routes.get_research_workspace_store",
        lambda: store,
    )
    return store


@pytest.mark.asyncio
async def test_download_jamovi_zip(research_store, tmp_path):
    manager = DatasetManager(research_store)
    project = research_store.create_project(title="Export", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    imported = manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/research/datasets/{imported['dataset_id']}/export/download",
            params={"format": "jamovi"},
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "jamovi" in (response.headers.get("content-disposition") or "")
    assert response.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_download_pspp_syntax(research_store, tmp_path):
    manager = DatasetManager(research_store)
    project = research_store.create_project(title="PSPP", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n", encoding="utf-8")
    imported = manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/research/datasets/{imported['dataset_id']}/export/download",
            params={"format": "pspp"},
        )
    assert response.status_code == 200
    assert b"FREQUENCIES" in response.content or b"GET FILE" in response.content
