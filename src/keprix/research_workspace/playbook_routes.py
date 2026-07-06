"""Research playbook HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.playbook_runner import ResearchPlaybookRunner, list_playbook_specs, load_playbook
from keprix.research_workspace.store import get_research_workspace_store

router = APIRouter(prefix="/api/research/playbooks", tags=["research-playbooks"])


class RunPlaybookBody(BaseModel):
    project_id: str = Field(..., min_length=1)
    dry_run: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


@router.get("")
async def list_playbooks(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": list_playbook_specs()}


@router.get("/{playbook_id}")
async def get_playbook(playbook_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        spec = load_playbook(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"playbook": spec}


@router.post("/{playbook_id}/run")
async def run_playbook(
    playbook_id: str,
    body: RunPlaybookBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    store = get_research_workspace_store()
    runner = ResearchPlaybookRunner(store)
    try:
        result = runner.run(
            body.project_id,
            playbook_id,
            owner=_user_id(user),
            dry_run=body.dry_run,
            parameters=body.parameters,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/projects/{project_id}/runs")
async def list_project_playbook_runs(
    project_id: str,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    store = get_research_workspace_store()
    if store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    runs = [
        item
        for item in store.list_objects(project_id)
        if item.get("object_type") == "playbook_run"
    ]
    return {"items": runs}
