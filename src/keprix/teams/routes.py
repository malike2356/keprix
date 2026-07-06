"""HTTP routes for CrewAI-style teams (Prompt 52)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.teams.registry import team_registry
from keprix.teams.run_store import attach_team_run_recorder, team_run_store
from keprix.teams.yaml_loader import crew_from_yaml, crew_to_yaml

router = APIRouter(prefix="/api/teams", tags=["teams"])


class ImportTeamBody(BaseModel):
    yaml: str = Field(..., min_length=1)


class RunTeamBody(BaseModel):
    objective: str = Field(..., min_length=1)
    initial_state: dict[str, Any] | None = None
    approved_tasks: list[str] | None = None


@router.get("")
async def list_teams() -> dict[str, Any]:
    return {"teams": team_registry.list_names()}


@router.post("/import")
async def import_team(body: ImportTeamBody) -> dict[str, Any]:
    try:
        crew, flow = crew_from_yaml(body.yaml)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    team_registry.register(crew, flow)
    return {
        "name": crew.name,
        "tasks": [task.id for task in crew.tasks],
        "flow_start": flow.start,
    }


@router.get("/{name}")
async def get_team(name: str) -> dict[str, Any]:
    entry = team_registry.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return {
        "name": entry.crew.name,
        "roles": sorted(entry.crew.roles.keys()),
        "tasks": [task.to_dict() for task in entry.crew.tasks],
        "flow": {"start": entry.flow.start, "events": entry.flow.events},
    }


@router.get("/{name}/yaml")
async def export_team_yaml(name: str) -> dict[str, str]:
    entry = team_registry.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"yaml": crew_to_yaml(entry.crew, entry.flow)}


@router.post("/{name}/run")
async def run_team(name: str, body: RunTeamBody) -> dict[str, Any]:
    entry = team_registry.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Team not found")

    run_id = str(uuid4())
    team_run_store.create(name, run_id)
    attach_team_run_recorder(entry.crew, team_name=name, run_id=run_id)

    state = dict(body.initial_state or {})
    state["objective"] = body.objective
    if body.approved_tasks:
        state["approved_tasks"] = list(body.approved_tasks)
    try:
        compiled = entry.flow.compile_to_playbook(entry.crew).compile()
        runner = PlaybookRunner(compiled)
        run = await runner.execute_inline(state)
    except Exception as exc:
        team_run_store.finalize(name, run_id, status="failed", state={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    team_run_store.finalize(name, run_id, status=run.status.value, state=run.state)
    return {
        "name": name,
        "run_id": run_id,
        "status": run.status.value,
        "state": run.state,
        "events_url": f"/api/teams/{name}/runs/{run_id}/events",
        "workspace_url": f"/admin/teams?team={name}&run={run_id}",
    }


@router.get("/{name}/runs/{run_id}/events")
async def get_team_run_events(name: str, run_id: str) -> dict[str, Any]:
    record = team_run_store.get(name, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Team run not found")
    return {
        "team_name": record.team_name,
        "run_id": record.run_id,
        "status": record.status,
        "events": [event.to_dict() for event in record.events],
    }
