"""Dataset export tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.datasets.codebook import Codebook, VariableDefinition
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.datasets.export import export_dataset
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


def test_export_preserves_labels_and_missing_values(dataset_manager, tmp_path):
    store = dataset_manager.store
    project = store.create_project(title="Export test", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    imported = dataset_manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    codebook = dataset_manager.load_codebook(imported["dataset_id"], 1)
    assert codebook is not None
    score = codebook.get_variable("score")
    assert score is not None
    score.label = "Happiness score"
    score.missing_codes = ["88"]
    score.value_labels = {"70": "Moderate", "88": "Missing"}
    dataset_manager.save_codebook(codebook)
    dataset_manager.transform(imported["dataset_id"], transform="apply_missing", params={})
    exported = dataset_manager.export(imported["dataset_id"], fmt="csv")
    content = Path(exported["path"]).read_text(encoding="utf-8")
    assert "Happiness score" in content
    assert "score" in content
    pspp = dataset_manager.export(imported["dataset_id"], fmt="pspp")
    pspp_text = Path(pspp["path"]).read_text(encoding="utf-8")
    assert "VALUE LABELS score" in pspp_text
    assert "MISSING VALUES score" in pspp_text


def test_lineage_recorded_on_transform(dataset_manager, tmp_path):
    store = dataset_manager.store
    project = store.create_project(title="Lineage", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n", encoding="utf-8")
    imported = dataset_manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    dataset_manager.transform(imported["dataset_id"], transform="apply_missing", params={})
    dataset = dataset_manager.get_dataset(imported["dataset_id"])
    assert dataset is not None
    steps = [step["step"] for step in dataset["lineage"]["steps"]]
    assert "import" in steps
    assert "apply_missing" in steps
