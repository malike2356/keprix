"""Authenticated self-service workspace deletion routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from keprix.auth.dependencies import get_current_user
from keprix.workspace.deletion import cancel_deletion, get_deletion_store, request_deletion

router = APIRouter(prefix="/api/workspace/deletion", tags=["workspace-deletion"])


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "").strip()


def _owner(workspace_id: str, user: dict[str, Any]) -> str:
    owner = _user_id(user)
    if not owner or workspace_id != owner:
        raise HTTPException(status_code=403, detail="workspace_owner_required")
    return owner


@router.post("/request")
async def request(workspace_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    owner = _owner(workspace_id, user)
    return await request_deletion(workspace_id, owner)


@router.post("/cancel")
async def cancel(workspace_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _owner(workspace_id, user)
    return cancel_deletion(workspace_id)


@router.get("/status")
async def status(workspace_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _owner(workspace_id, user)
    row = get_deletion_store().get(workspace_id)
    from keprix.workspace.deletion import _status

    return _status(row, workspace_id)
