"""Task workspace routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import TaskCreate, TaskReorder, TaskUpdate

router = APIRouter(prefix="/api/workspace/tasks", tags=["workspace-tasks"])


@router.post("", status_code=201)
async def create_task(body: TaskCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.create_task(user, **body.model_dump())


@router.get("")
async def list_tasks(
    user: dict = Depends(get_current_user),
    status: str | None = None,
    tag: str | None = None,
    due_before: datetime | None = Query(None),
) -> dict[str, Any]:
    rows = workspace_repo.list_tasks(user, status=status, tag=tag, due_before=due_before)
    return {"items": rows}


@router.post("/reorder")
async def reorder_tasks(body: TaskReorder, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        rows = workspace_repo.reorder_tasks(user, body.order)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return {"items": rows}


@router.get("/{task_id}")
async def get_task(task_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.get_task(user, task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found") from None


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.update_task(user, task_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found") from None


@router.delete("/{task_id}", status_code=200)
async def delete_task(task_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_task(user, task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found") from None


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.complete_task(user, task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found") from None
