"""ML workspace HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.ml_workspace.store import get_ml_workspace_store

router = APIRouter(prefix="/api/ml", tags=["ml-workspace"])


class ExperimentBody(BaseModel):
    name: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)
    dataset_id: str | None = None
    parameters: dict[str, Any] | None = None


class RunBody(BaseModel):
    experiment_id: str
    metrics: dict[str, Any] | None = None


@router.get("/datasets")
async def list_ml_datasets(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.data_plane.catalog import get_dataset_catalog

    return {"items": get_dataset_catalog().list()}


@router.post("/experiments")
async def create_experiment(body: ExperimentBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    experiment = get_ml_workspace_store().create_experiment(
        name=body.name,
        task_type=body.task_type,
        dataset_id=body.dataset_id,
        parameters=body.parameters,
    )
    return {"experiment": experiment}


@router.get("/experiments")
async def list_experiments(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": get_ml_workspace_store().list_experiments()}


@router.get("/runs")
async def list_runs(
    experiment_id: str | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return {"items": get_ml_workspace_store().list_runs(experiment_id)}


@router.post("/runs")
async def create_run(body: RunBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"run": get_ml_workspace_store().create_run(body.experiment_id, metrics=body.metrics)}


@router.get("/model-registry")
async def model_registry(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": get_ml_workspace_store().model_registry()}
