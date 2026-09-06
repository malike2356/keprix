"""Workspace-scoped worker profile and connection APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.personas.registry import get_persona_registry
from keprix.workers.store import get_worker_store

router = APIRouter(prefix="/api/workers", tags=["workers"])


class WorkerBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    persona: str = "NEXUS"


class TelegramBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    token: str = Field(min_length=20)
    chat_id: str = Field(min_length=1)


class TaskBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    task: dict[str, Any] | None = None


class ApprovalBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    action: str = Field(min_length=1)


def _worker(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "telegram" or "token_hash" not in value}


@router.get("")
async def list_workers(workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    rows = [_worker(row) for row in get_worker_store().list(workspace_id)]
    return {"items": rows, "count": len(rows)}


@router.post("", status_code=201)
async def create_worker(body: WorkerBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    persona = get_persona_registry().get(body.persona)
    if persona is None:
        raise HTTPException(status_code=422, detail="unknown_persona")
    return {"worker": _worker(get_worker_store().create(body.workspace_id, body.slug, persona.name))}


@router.get("/{worker_id}/briefing")
async def worker_briefing(worker_id: str, workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    worker = get_worker_store().get(workspace_id, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    persona = get_persona_registry().get(worker["persona"])
    return {"worker": _worker(worker), "briefing": {"persona": persona.to_dict() if persona else None, "workspace_id": workspace_id, "tools": []}}


@router.post("/{worker_id}/telegram")
async def connect_telegram(worker_id: str, body: TelegramBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().connect_telegram(body.workspace_id, worker_id, body.token, body.chat_id)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker": _worker(row), "connected": True}


@router.post("/{worker_id}/enable")
async def enable_worker(worker_id: str, workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().set_enabled(workspace_id, worker_id, True)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker": _worker(row), "enabled": True}


@router.post("/{worker_id}/disable")
async def disable_worker(worker_id: str, workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().set_enabled(workspace_id, worker_id, False)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker": _worker(row), "enabled": False}


@router.post("/{worker_id}/preferred")
async def prefer_worker(worker_id: str, workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().set_preferred(workspace_id, worker_id)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker": _worker(row), "preferred": True}


@router.post("/{worker_id}/task")
async def save_worker_task(worker_id: str, body: TaskBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().save_task(body.workspace_id, worker_id, body.task)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker": _worker(row), "pending_task": body.task}


@router.get("/{worker_id}/task")
async def resume_worker_task(worker_id: str, workspace_id: str = "default", user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    row = get_worker_store().get(workspace_id, worker_id)
    if row is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"worker_id": worker_id, "pending_task": row.get("pending_task"), "can_resume": bool(row.get("pending_task"))}


@router.post("/{worker_id}/approvals")
async def request_worker_approval(worker_id: str, body: ApprovalBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    approval = get_worker_store().request_approval(body.workspace_id, worker_id, body.action, str(user.get("id") or user.get("username") or "owner"))
    if approval is None:
        raise HTTPException(status_code=404, detail="worker_not_found")
    return {"approval": approval}
