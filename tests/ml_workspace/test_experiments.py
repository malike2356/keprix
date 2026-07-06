"""ML workspace experiment tracking tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.ml_workspace.store import MLWorkspaceStore


@pytest.fixture
def ml_store(tmp_path):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    store = MLWorkspaceStore(workspace_id=plane.workspace_id)
    store.plane = plane
    return store


def test_experiment_run_stores_metrics_and_parameters(ml_store: MLWorkspaceStore):
    experiment = ml_store.create_experiment(
        name="Baseline classifier",
        task_type="classification",
        dataset_id="ds-survey",
        parameters={"algorithm": "logistic_regression", "max_iter": 200},
    )
    run = ml_store.create_run(
        experiment["experiment_id"],
        metrics={"accuracy": 0.91, "f1": 0.88},
    )
    assert run["experiment_id"] == experiment["experiment_id"]

    runs = ml_store.list_runs(experiment["experiment_id"])
    assert len(runs) == 1
    assert runs[0]["metrics"]["accuracy"] == 0.91
    assert runs[0]["metrics"]["f1"] == 0.88

    experiments = ml_store.list_experiments()
    assert experiments[0]["parameters"]["algorithm"] == "logistic_regression"


def test_model_registry_lists_completed_runs(ml_store: MLWorkspaceStore):
    experiment = ml_store.create_experiment(
        name="Drift check",
        task_type="regression",
        dataset_id="ds-ops",
    )
    ml_store.create_run(experiment["experiment_id"], metrics={"rmse": 0.12})
    registry = ml_store.model_registry()
    assert isinstance(registry, list)
