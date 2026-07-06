"""Playbook run HTTP routes (durable workflow runtime)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.playbook.graph_catalog import PLAYBOOK_GRAPH_CATALOG, get_graph_template
from keprix.playbook.runtime import PlaybookRunError, playbook_registry
from keprix.playbook.runtime.errors import PlaybookGraphError
from keprix.playbook.sdk_workflow import start_workflow_run

router = APIRouter(prefix="/api/playbook-runs", tags=["playbook-runs"])


class ResumeRequest(BaseModel):
    state_patch: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None


class StartWorkflowRequest(BaseModel):
    workspace_id: str = "default"
    graph_id: str = "sdk-workflow"
    initial_state: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    entry: str | None = None


@router.get("")
async def list_playbook_runs(workspace_id: str = "default", limit: int = 50) -> dict[str, Any]:
    """List in-memory playbook runs for a workspace (lost on process restart)."""
    runs = playbook_registry.list_runs(workspace_id=workspace_id, limit=limit)
    interrupted = sum(
        1
        for run in runs
        if run.status.value in {"interrupted", "waiting_for_approval"}
    )
    return {
        "runs": [run.to_dict() for run in runs],
        "count": len(runs),
        "interrupted_count": interrupted,
        "persistence": "in_memory",
    }


@router.get("/graphs")
async def list_playbook_graphs() -> dict[str, Any]:
    """Built-in playbook templates available from the workspace UI."""
    return {
        "graphs": [
            {
                "graph_id": item["graph_id"],
                "title": item["title"],
                "description": item["description"],
                "entry": item.get("entry"),
                "steps": item.get("steps") or [],
                "edges": item.get("edges") or [],
            }
            for item in PLAYBOOK_GRAPH_CATALOG
        ]
    }


@router.post("/start")
async def start_playbook_run(body: StartWorkflowRequest) -> dict[str, Any]:
    steps = list(body.steps)
    edges = list(body.edges)
    entry = body.entry
    if not steps:
        template = get_graph_template(body.graph_id)
        if template is not None:
            steps = list(template.get("steps") or [])
            edges = list(template.get("edges") or [])
            entry = entry or template.get("entry")

    spec = {
        "graph_id": body.graph_id,
        "steps": steps,
        "edges": edges,
        "entry": entry,
    }
    try:
        run = await start_workflow_run(
            spec,
            workspace_id=body.workspace_id,
            initial_state=body.initial_state,
        )
    except PlaybookGraphError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict()


@router.get("/{run_id}")
async def get_playbook_run(run_id: str) -> dict[str, Any]:
    run = playbook_registry.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Playbook run not found")
    return run.to_dict()


@router.get("/{run_id}/events")
async def get_playbook_run_events(run_id: str) -> dict[str, Any]:
    emitter = playbook_registry.get_events(run_id)
    if emitter is None:
        raise HTTPException(status_code=404, detail="Playbook run not found")
    return {"events": [event.to_dict() for event in emitter.list_events(run_id)]}


@router.post("/{run_id}/resume")
async def resume_playbook_run(run_id: str, body: ResumeRequest) -> dict[str, Any]:
    try:
        run = await playbook_registry.resume(
            run_id,
            state_patch=body.state_patch,
            approved_by=body.approved_by,
        )
    except PlaybookRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict()


@router.post("/{run_id}/pause")
async def pause_playbook_run(run_id: str) -> dict[str, Any]:
    try:
        run = await playbook_registry.pause(run_id)
    except PlaybookRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict()


@router.post("/{run_id}/cancel")
async def cancel_playbook_run(run_id: str) -> dict[str, Any]:
    try:
        run = await playbook_registry.cancel(run_id)
    except PlaybookRunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run.to_dict()
