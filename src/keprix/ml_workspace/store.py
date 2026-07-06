"""ML workspace experiment tracking."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.data_architecture.data_plane import get_workspace_data_plane


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MLWorkspaceStore:
    def __init__(self, workspace_id: str = "default") -> None:
        self.plane = get_workspace_data_plane(workspace_id)

    def create_experiment(
        self,
        *,
        name: str,
        task_type: str,
        dataset_id: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        experiment_id = f"exp-{uuid.uuid4().hex[:10]}"
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO ml_experiments
                (experiment_id, workspace_id, dataset_id, name, task_type, parameters_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    self.plane.workspace_id,
                    dataset_id,
                    name,
                    task_type,
                    json.dumps(parameters or {}),
                    now,
                ),
            )
        return self.get_experiment(experiment_id) or {"experiment_id": experiment_id, "name": name}

    def list_experiments(self) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            rows = conn.execute("SELECT * FROM ml_experiments ORDER BY created_at DESC").fetchall()
        return [self._experiment_row(row) for row in rows]

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        with self.plane.connect() as conn:
            row = conn.execute(
                "SELECT * FROM ml_experiments WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
        return self._experiment_row(row) if row else None

    def create_run(self, experiment_id: str, *, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO ml_runs (run_id, experiment_id, status, metrics_json, created_at)
                VALUES (?, ?, 'running', ?, ?)
                """,
                (run_id, experiment_id, json.dumps(metrics or {}), now),
            )
        return {"run_id": run_id, "experiment_id": experiment_id, "status": "running"}

    def list_runs(self, experiment_id: str | None = None) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            if experiment_id:
                rows = conn.execute(
                    "SELECT * FROM ml_runs WHERE experiment_id = ? ORDER BY created_at DESC",
                    (experiment_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM ml_runs ORDER BY created_at DESC").fetchall()
        return [self._run_row(row) for row in rows]

    def model_registry(self) -> list[dict[str, Any]]:
        runs = self.list_runs()
        return [
            {
                "run_id": row["run_id"],
                "experiment_id": row["experiment_id"],
                "status": row["status"],
                "metrics": row["metrics"],
                "artifact_path": row.get("artifact_path"),
            }
            for row in runs
            if row.get("artifact_path") or row.get("status") == "completed"
        ]

    @staticmethod
    def _experiment_row(row: Any) -> dict[str, Any]:
        return {
            "experiment_id": row["experiment_id"],
            "workspace_id": row["workspace_id"],
            "dataset_id": row["dataset_id"],
            "name": row["name"],
            "task_type": row["task_type"],
            "parameters": json.loads(row["parameters_json"] or "{}"),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _run_row(row: Any) -> dict[str, Any]:
        return {
            "run_id": row["run_id"],
            "experiment_id": row["experiment_id"],
            "status": row["status"],
            "metrics": json.loads(row["metrics_json"] or "{}"),
            "artifact_path": row["artifact_path"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }


_store: MLWorkspaceStore | None = None


def get_ml_workspace_store(workspace_id: str = "default") -> MLWorkspaceStore:
    global _store
    if _store is None:
        _store = MLWorkspaceStore(workspace_id)
    return _store
