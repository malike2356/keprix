"""Notebook HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.notebooks.errors import DangerousCodeError, NotebookRunError, RunnerNotInstalledError
from keprix.research_workspace.notebooks.kernel_manager import detect_python, detect_r
from keprix.research_workspace.notebooks.runner import NotebookRunner
from keprix.research_workspace.notebooks.sandbox import SandboxConfig
from keprix.research_workspace.store import get_research_workspace_store

router = APIRouter(prefix="/api/research/notebooks", tags=["research-notebooks"])


class PrepareBody(BaseModel):
    project_id: str = Field(..., min_length=1)
    runtime: Literal["python", "r"] = "python"
    code: str = Field(..., min_length=1)
    dataset_id: str | None = None
    markdown_cells: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    allow_network: bool = False
    approve_dangerous: bool = False


class ExecuteBody(BaseModel):
    run_id: str = Field(..., min_length=1)
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    allow_network: bool = False
    approve_dangerous: bool = False


def _runner() -> NotebookRunner:
    return NotebookRunner(get_research_workspace_store())


def _sandbox(body: PrepareBody | ExecuteBody) -> SandboxConfig:
    return SandboxConfig(
        timeout_seconds=body.timeout_seconds,
        allow_network=body.allow_network,
        approve_dangerous=body.approve_dangerous,
    )


@router.get("/status")
async def notebook_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    python = detect_python()
    r_runtime = detect_r()
    return {
        "python": {
            "installed": python.installed,
            "binary": python.binary,
            "version": python.version,
            "optional_packages": python.optional_packages,
            "setup_instructions": python.setup_instructions,
        },
        "r": {
            "installed": r_runtime.installed,
            "binary": r_runtime.binary,
            "version": r_runtime.version,
            "optional_packages": r_runtime.optional_packages,
            "setup_instructions": r_runtime.setup_instructions,
        },
    }


@router.post("/prepare")
async def prepare_notebook(body: PrepareBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    dataset_path: Path | None = None
    dataset_version: int | None = None
    if body.dataset_id:
        manager = DatasetManager(get_research_workspace_store())
        dataset = manager.get_dataset(body.dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        dataset_path = Path(dataset["payload"]["path"])
        dataset_version = int(dataset["payload"].get("version_number") or 1)
    try:
        return _runner().prepare_run(
            project_id=body.project_id,
            runtime=body.runtime,
            code=body.code,
            dataset_id=body.dataset_id,
            dataset_version=dataset_version,
            dataset_path=dataset_path,
            markdown_cells=body.markdown_cells,
            config=_sandbox(body),
        )
    except DangerousCodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/execute")
async def execute_notebook(body: ExecuteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = get_research_workspace_store()
    with store.plane.connect() as conn:
        row = conn.execute(
            "SELECT project_id FROM research_objects WHERE object_id = ?",
            (body.run_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Notebook run not found")
    try:
        return _runner().execute(
            project_id=row["project_id"],
            run_id=body.run_id,
            config=_sandbox(body),
        )
    except (RunnerNotInstalledError, NotebookRunError, DangerousCodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
