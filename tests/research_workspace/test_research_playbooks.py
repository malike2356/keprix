"""Research workspace playbook tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.playbook_runner import ResearchPlaybookRunner, list_playbook_specs, load_playbook
from keprix.research_workspace.playbook_routes import router as research_playbook_router
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.store import ResearchWorkspaceStore


PLAYBOOK_IDS = [
    "literature_review",
    "survey_analysis",
    "dataset_to_report",
    "obsidian_research_map",
    "pspp_analysis",
    "jamovi_preparation",
    "borehole_field_research",
]


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

    for target in (
        "keprix.research_workspace.store.get_research_workspace_store",
        "keprix.research_workspace.routes.get_research_workspace_store",
        "keprix.research_workspace.playbook_routes.get_research_workspace_store",
    ):
        monkeypatch.setattr(target, _get_store)
    return store


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(research_playbook_router)
    return test_app


def test_all_required_playbooks_exist():
    specs = {item["id"] for item in list_playbook_specs()}
    for playbook_id in PLAYBOOK_IDS:
        assert playbook_id in specs


@pytest.mark.parametrize("playbook_id", PLAYBOOK_IDS)
def test_playbook_dry_run(research_store, playbook_id):
    project = ResearchProjectService(research_store).create(title="Playbook test", owner="analyst")
    runner = ResearchPlaybookRunner(research_store)
    result = runner.run(project.project_id, playbook_id, owner="analyst", dry_run=True)
    assert result["trace_id"]
    assert result["run"]["status"] == "dry_run"
    assert len(result["run"]["steps"]) == len(load_playbook(playbook_id).get("steps") or [])


def test_playbook_live_run_records_artifacts_and_review_flags(research_store):
    project = ResearchProjectService(research_store).create(title="Live run", owner="analyst")
    runner = ResearchPlaybookRunner(research_store)
    result = runner.run(project.project_id, "pspp_analysis", owner="analyst", dry_run=False)
    assert result["trace_id"]
    assert result["run"]["status"] == "completed"
    assert "interpret_results" in result["run"]["pending_approvals"]
    objects = research_store.list_objects(project.project_id, object_type="playbook_run")
    assert objects
    assert objects[0]["trace_id"] == result["trace_id"]


@pytest.mark.asyncio
async def test_api_list_and_run_playbook(app, research_store):
    project = ResearchProjectService(research_store).create(title="API", owner="analyst")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/research/playbooks")
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert any(item["id"] == "literature_review" for item in items)
        run = await client.post(
            "/api/research/playbooks/literature_review/run",
            json={"project_id": project.project_id, "dry_run": True},
        )
    assert run.status_code == 200
    payload = run.json()
    assert payload["trace_id"]
    assert payload["run"]["playbook_id"] == "literature_review"


def test_survey_analysis_with_fixture_dataset(research_store, tmp_path):
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    project = ResearchProjectService(research_store).create(title="Survey", owner="analyst")
    runner = ResearchPlaybookRunner(research_store)
    result = runner.run(
        project.project_id,
        "survey_analysis",
        owner="analyst",
        dry_run=False,
        parameters={"dataset_path": str(csv_path), "dataset_name": "Survey"},
    )
    assert result["run"]["pending_approvals"]
    dataset_objects = research_store.list_objects(project.project_id, object_type="dataset")
    assert dataset_objects
