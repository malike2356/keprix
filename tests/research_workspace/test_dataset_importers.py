"""Dataset importer tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def dataset_manager(tmp_path, monkeypatch):
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
    return DatasetManager(store)


def test_import_csv_assigns_codebook(dataset_manager, tmp_path):
    store = dataset_manager.store
    project = store.create_project(title="Survey", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score,region\n30,88,north\n25,72,south\n", encoding="utf-8")
    result = dataset_manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Field survey",
        owner="analyst",
    )
    assert result["dataset_id"].startswith("ds-")
    assert result["codebook"]["variables"]
    names = {variable["name"] for variable in result["codebook"]["variables"]}
    assert names == {"age", "score", "region"}
    original = Path(result["meta"]["original_path"])
    assert original.exists()


def test_original_data_not_mutated_on_transform(dataset_manager, tmp_path):
    store = dataset_manager.store
    project = store.create_project(title="Survey", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n", encoding="utf-8")
    imported = dataset_manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Field survey",
        owner="analyst",
    )
    original_text = Path(imported["meta"]["original_path"]).read_text(encoding="utf-8")
    codebook = dataset_manager.load_codebook(imported["dataset_id"], 1)
    assert codebook is not None
    codebook.variables[0].missing_codes = ["88"]
    dataset_manager.save_codebook(codebook)
    dataset_manager.transform(
        imported["dataset_id"],
        transform="apply_missing",
        params={},
    )
    assert Path(imported["meta"]["original_path"]).read_text(encoding="utf-8") == original_text
