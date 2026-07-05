"""Assistant routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import AssistantCreate, AssistantUpdate

router = APIRouter(prefix="/api/workspace/assistants", tags=["workspace-assistants"])


@router.post("", status_code=201)
async def create_assistant(body: AssistantCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.create_assistant(user, **body.model_dump())


@router.get("")
async def list_assistants(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": workspace_repo.list_assistants(user)}


@router.put("/{assistant_id}")
async def update_assistant(
    assistant_id: str,
    body: AssistantUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.update_assistant(user, assistant_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Assistant not found") from None


@router.delete("/{assistant_id}", status_code=200)
async def delete_assistant(assistant_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_assistant(user, assistant_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Assistant not found") from None
