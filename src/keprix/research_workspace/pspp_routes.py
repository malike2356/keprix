"""PSPP HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.stats.pspp.errors import (
    PSPPPathNotAllowedError,
    PSPPRunError,
    PSPPUnsafeFragmentError,
)
from keprix.research_workspace.stats.pspp.runner import PsppRunner, detect_pspp
from keprix.research_workspace.store import get_research_workspace_store

router = APIRouter(prefix="/api/research/pspp", tags=["research-pspp"])


class GenerateBody(BaseModel):
    dataset_id: str = Field(..., min_length=1)
    procedures: list[dict[str, Any]] = Field(default_factory=list)
    approve_external_paths: bool = False


class RunBody(BaseModel):
    run_id: str = Field(..., min_length=1)
    output_format: Literal["html", "odt", "txt"] = "txt"


def _runner() -> PsppRunner:
    return PsppRunner(get_research_workspace_store())


def _dataset_context(dataset_id: str) -> tuple[DatasetManager, dict[str, Any]]:
    manager = DatasetManager(get_research_workspace_store())
    dataset = manager.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return manager, dataset


@router.get("/status")
async def pspp_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    detection = detect_pspp()
    return {
        "installed": detection.installed,
        "binary": detection.binary,
        "version": detection.version,
        "setup_instructions": detection.setup_instructions,
    }


@router.post("/generate")
async def generate_pspp_syntax(
    body: GenerateBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    manager, dataset = _dataset_context(body.dataset_id)
    version_number = int(dataset["payload"].get("version_number") or 1)
    codebook = manager.load_codebook(body.dataset_id, version_number)
    if codebook is None:
        raise HTTPException(status_code=404, detail="Codebook not found")
    project_id = dataset["project_id"]
    try:
        manifest = _runner().generate(
            project_id=project_id,
            dataset_id=body.dataset_id,
            codebook=codebook,
            data_path=Path(dataset["payload"]["path"]),
            procedures=body.procedures,
            approve_external_paths=body.approve_external_paths,
        )
    except (PSPPPathNotAllowedError, PSPPUnsafeFragmentError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return manifest


@router.post("/run")
async def run_pspp_analysis(body: RunBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = get_research_workspace_store()
    with store.plane.connect() as conn:
        row = conn.execute(
            "SELECT project_id FROM research_objects WHERE object_id = ?",
            (body.run_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="PSPP run not found")
    try:
        return _runner().run(
            project_id=row["project_id"],
            run_id=body.run_id,
            output_format=body.output_format,
        )
    except PSPPRunError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
