"""Builder HTTP routes (Prompt 29)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from keprix.backend.builder.build_agent import cancel_build_job, start_build_job, stream_job_log
from keprix.backend.builder.registry import get_project_registry
from keprix.backend.builder.store import get_builder_store
from keprix.backend.builder.templates.engine import list_templates, scaffold_project, template_details
from keprix.backend.builder.tools import deploy_to_docker, deploy_to_lampp

router = APIRouter(prefix="/api/builder", tags=["builder"])


class BuildBody(BaseModel):
    instruction: str = Field(min_length=1)


class ScaffoldBody(BaseModel):
    template: str
    name: str
    path: str
    config: dict[str, Any] = Field(default_factory=dict)


@router.get("/projects")
async def list_projects() -> dict[str, Any]:
    rows = get_project_registry().list_projects()
    return {"projects": rows, "count": len(rows)}


@router.post("/projects/scan")
async def scan_projects() -> dict[str, Any]:
    rows = get_project_registry().scan()
    return {"projects": rows, "count": len(rows)}


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    project = get_project_registry().get_project(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    analysis = get_project_registry().analyse(project_id)
    return {"project": project, "analysis": analysis}


@router.get("/projects/{project_id}/tree")
async def project_tree(project_id: str, depth: int = Query(default=2, ge=1, le=5)) -> dict[str, Any]:
    try:
        tree = get_project_registry().tree(project_id, depth=depth)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"tree": tree}


@router.get("/projects/{project_id}/analyse")
async def analyse_project(project_id: str) -> dict[str, Any]:
    try:
        return get_project_registry().analyse(project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/build")
async def start_build(project_id: str, body: BuildBody, background_tasks: BackgroundTasks) -> dict[str, Any]:
    project = get_project_registry().get_project(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    job = get_builder_store().create_job(
        {
            "project_id": project_id,
            "job_type": "add-feature",
            "instruction": body.instruction,
        }
    )
    background_tasks.add_task(start_build_job, job["id"])
    return {"job": job}


@router.get("/jobs")
async def list_jobs(project_id: str | None = None) -> dict[str, Any]:
    rows = get_builder_store().list_jobs(project_id=project_id)
    return {"jobs": rows, "count": len(rows)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = get_builder_store().get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    log = get_builder_store().read_job_log(job_id)
    trajectory: list[dict[str, Any]] = []
    run_id = job.get("trajectory_run_id")
    if run_id:
        from keprix.coding.trajectory_steps import load_patch_steps_for_run

        trajectory = load_patch_steps_for_run(str(run_id))
    return {"job": job, "log": log, "trajectory": trajectory}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    job = get_builder_store().get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    async def generate():
        async for event in stream_job_log(job_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    if not cancel_build_job(job_id):
        raise HTTPException(400, "Job cannot be cancelled")
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/scaffold")
async def scaffold(body: ScaffoldBody) -> dict[str, Any]:
    try:
        result = scaffold_project(
            template=body.template,
            name=body.name,
            path=body.path,
            config=body.config,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    registry = get_project_registry()
    project = registry._store.upsert_project(
        {
            "name": body.name,
            "path": result["path"],
            "tech_stack": ["typescript", "nextjs"] if body.template == "keprix-nextjs-app" else [],
            "stack_type": "nextjs" if body.template == "keprix-nextjs-app" else body.template,
            "framework": body.template,
            "status": "wip",
            "keprix_app": body.template.startswith("keprix-"),
        }
    )
    return {"result": result, "project": project}


@router.get("/templates")
async def templates() -> dict[str, Any]:
    return {"templates": list_templates()}


@router.get("/templates/{name}")
async def template_detail(name: str) -> dict[str, Any]:
    try:
        return template_details(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/deploy")
async def deploy_project(project_id: str, target: str = "lampp") -> dict[str, Any]:
    project = get_project_registry().get_project(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if target == "docker":
        return deploy_to_docker(project["path"])
    return deploy_to_lampp(project["path"])
