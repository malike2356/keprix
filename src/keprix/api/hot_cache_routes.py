"""Workspace hot cache API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.workspace.hot_cache_service import HotCacheService

router = APIRouter(prefix="/api/workspaces/{workspace_id}/hot-cache", tags=["workspaces"])


class ConfigBody(BaseModel):
    enabled: bool
    workspace_path: str | None = None


class RefreshBody(BaseModel):
    workspace_path: str | None = None
    source_session_id: str | None = None
    recent_text: str = ""
    summary: str | None = None
    force: bool = False


@router.get("")
async def get_hot_cache(workspace_id: str, workspace_path: str | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return HotCacheService().read(workspace_id, workspace_path)


@router.put("/config")
async def put_hot_cache_config(workspace_id: str, body: ConfigBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"config": HotCacheService().set_config(workspace_id, body.enabled, body.workspace_path).to_dict()}


@router.post("/refresh")
async def refresh_hot_cache(workspace_id: str, body: RefreshBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return HotCacheService().refresh(
        workspace_id,
        workspace_path=body.workspace_path,
        source_session_id=body.source_session_id,
        recent_text=body.recent_text,
        summary=body.summary,
        force=body.force,
    )
