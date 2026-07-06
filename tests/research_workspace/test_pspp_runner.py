"""PSPP runner tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.stats.pspp.runner import PsppRunner, detect_pspp
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def pspp_runner(tmp_path, monkeypatch):
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
    return PsppRunner(store)


def test_detect_pspp_not_installed():
    with patch("keprix.research_workspace.stats.pspp.runner.shutil.which", return_value=None):
        detection = detect_pspp()
    assert detection.installed is False
    assert "PSPP is not installed" in detection.setup_instructions


def test_runner_preserves_syntax_when_pspp_missing(pspp_runner, tmp_path):
    manager = DatasetManager(pspp_runner.store)
    project = manager.store.create_project(title="PSPP", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    imported = manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    dataset = manager.get_dataset(imported["dataset_id"])
    codebook = manager.load_codebook(imported["dataset_id"], 1)
    manifest = pspp_runner.generate(
        project_id=project["project_id"],
        dataset_id=imported["dataset_id"],
        codebook=codebook,
        data_path=Path(dataset["payload"]["path"]),
        procedures=[{"type": "frequencies", "variables": ["age", "score"]}],
    )
    with patch("keprix.research_workspace.stats.pspp.runner.shutil.which", return_value=None):
        result = pspp_runner.run(project_id=project["project_id"], run_id=manifest["run_id"])
    assert result["status"] == "syntax_only"
    assert Path(result["syntax_path"]).exists()
    assert "setup_instructions" in result


def test_runner_executes_pspp_when_installed(pspp_runner, tmp_path):
    manager = DatasetManager(pspp_runner.store)
    project = manager.store.create_project(title="PSPP", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    imported = manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    dataset = manager.get_dataset(imported["dataset_id"])
    codebook = manager.load_codebook(imported["dataset_id"], 1)
    manifest = pspp_runner.generate(
        project_id=project["project_id"],
        dataset_id=imported["dataset_id"],
        codebook=codebook,
        data_path=Path(dataset["payload"]["path"]),
        procedures=[{"type": "frequencies", "variables": ["age", "score"]}],
    )

    class Completed:
        returncode = 0
        stdout = "PSPP ok"
        stderr = ""

    with patch("keprix.research_workspace.stats.pspp.runner.shutil.which", return_value="/usr/bin/pspp"):
        with patch("keprix.research_workspace.stats.pspp.runner.subprocess.run", return_value=Completed()):
            workdir = pspp_runner.root / manifest["run_id"]
            (workdir / "output.txt").write_text("Frequencies\nage  count\n30  1\n", encoding="utf-8")
            result = pspp_runner.run(project_id=project["project_id"], run_id=manifest["run_id"], output_format="txt")
    assert result["installed"] is True
    assert result["status"] == "complete"
    assert result["parsed_tables"]
