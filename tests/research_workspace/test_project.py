"""Research project tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.project import ResearchProjectService
from keprix.research_workspace.store import ResearchWorkspaceStore


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
    return store


def test_create_project_includes_trace_and_policies(research_store):
    service = ResearchProjectService(research_store)
    project = service.create(title="Borehole survey", question="What is the yield trend?", owner="analyst-1")
    assert project.project_id.startswith("rp-")
    assert project.trace_id
    assert project.sensitivity_level == "internal"
    assert project.export_policy == "allow"
    assert project.owner == "analyst-1"


def test_list_projects_returns_created_project(research_store):
    service = ResearchProjectService(research_store)
    created = service.create(title="NGO field study", owner="ngo-1")
    projects = service.list()
    assert any(item.project_id == created.project_id for item in projects)
