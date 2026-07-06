"""Notebook export and orchestration tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.notebooks.html_export import notebook_to_html, write_html_report
from keprix.research_workspace.notebooks.notebook import attach_cell_output, build_provenance, create_notebook
from keprix.research_workspace.notebooks.runner import NotebookRunner
from keprix.research_workspace.notebooks.errors import DangerousCodeError
from keprix.research_workspace.notebooks.sandbox import SandboxConfig
from keprix.research_workspace.store import ResearchWorkspaceStore


@pytest.fixture
def notebook_runner(tmp_path, monkeypatch):
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
    return NotebookRunner(store)


def test_notebook_export_includes_provenance():
    provenance = build_provenance(project_id="proj-1", dataset_id="ds-1", dataset_version=2, trace_id="trace-abc")
    notebook = create_notebook(code_cells=["print(1)"], provenance=provenance, runtime="python")
    assert notebook["metadata"]["keprix"]["trace_id"] == "trace-abc"
    assert notebook["metadata"]["keprix"]["dataset_id"] == "ds-1"
    html = notebook_to_html(notebook)
    assert "trace-abc" in html
    assert "ds-1" in html


def test_failed_cell_captures_repair_suggestions():
    notebook = create_notebook(code_cells=["broken()"], runtime="python")
    updated = attach_cell_output(
        notebook,
        cell_index=0,
        stdout="",
        stderr="NameError: name 'broken' is not defined",
        return_code=1,
        repair_suggestions=["Define the function or fix the variable name."],
    )
    outputs = updated["cells"][0]["outputs"]
    assert any(output.get("output_type") == "error" for output in outputs)


def test_notebook_runner_end_to_end(notebook_runner, tmp_path):
    manager = DatasetManager(notebook_runner.store)
    project = manager.store.create_project(title="Notebook", owner="analyst")
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text("age,score\n30,88\n25,70\n", encoding="utf-8")
    imported = manager.import_file(
        project["project_id"],
        source_path=csv_path,
        name="Survey",
        owner="analyst",
    )
    dataset = manager.get_dataset(imported["dataset_id"])
    code = "print('analysis-complete')\n"
    manifest = notebook_runner.prepare_run(
        project_id=project["project_id"],
        runtime="python",
        code=code,
        dataset_id=imported["dataset_id"],
        dataset_version=int(dataset["payload"].get("version_number") or 1),
        dataset_path=Path(dataset["payload"]["path"]),
    )
    assert manifest["trace_id"]
    assert manifest["dataset_id"] == imported["dataset_id"]

    class Completed:
        returncode = 0
        stdout = "analysis-complete\n"
        stderr = ""

    with patch("keprix.research_workspace.notebooks.python_runner.detect_python") as detect:
        detect.return_value.installed = True
        detect.return_value.binary = "/usr/bin/python3"
        detect.return_value.optional_packages = ["pandas"]
        with patch("keprix.research_workspace.notebooks.python_runner.subprocess.run", return_value=Completed()):
            result = notebook_runner.execute(
                project_id=project["project_id"],
                run_id=manifest["run_id"],
                config=SandboxConfig(),
            )
    assert result["status"] == "completed"
    assert result["html_report"]
    notebook = json.loads(Path(result["paths"]["notebook"]).read_text(encoding="utf-8"))
    assert notebook["metadata"]["keprix"]["trace_id"] == manifest["trace_id"]
    assert Path(result["html_report"]).exists()
    write_html_report(notebook, Path(result["html_report"]))


def test_dangerous_code_requires_approval(notebook_runner):
    manager = DatasetManager(notebook_runner.store)
    project = manager.store.create_project(title="Notebook", owner="analyst")
    with pytest.raises(DangerousCodeError):
        notebook_runner.prepare_run(
            project_id=project["project_id"],
            runtime="python",
            code="import subprocess\nsubprocess.run(['curl', 'example.com'])",
            config=SandboxConfig(approve_dangerous=False),
        )
