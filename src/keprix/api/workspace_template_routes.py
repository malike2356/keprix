"""Structured workspace template and indexing routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.auth.dependencies import get_current_user
from keprix.workspace.index_generator import WorkspaceIndexer
from keprix.workspace.memory_index_bridge import MemoryIndexBridge
from keprix.workspace.template_presets import create_workspace, list_templates, workspace_root

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class CreateWorkspaceBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    template_id: str = "knowledge_pipeline"


class ReindexBody(BaseModel):
    folder: str | None = None


@router.get("/templates")
async def get_workspace_templates(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"templates": [template.to_dict() for template in list_templates()]}


@router.post("")
async def create_structured_workspace(
    body: CreateWorkspaceBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    try:
        workspace = create_workspace(body.name, body.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "workspace.created_with_template")
    return {"workspace": workspace}


@router.post("/{workspace_id}/reindex")
async def reindex_workspace(
    workspace_id: str,
    body: ReindexBody = ReindexBody(),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    root = workspace_root(workspace_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="workspace not found")
    indexer = WorkspaceIndexer(root)
    if body.folder:
        content = indexer.update_index(body.folder)
        updated = [str(root / body.folder / "index.md")]
    else:
        updated = [str(path) for path in indexer.reindex_all()]
        content = ""
    return {"updated": updated, "content": content}


@router.post("/{workspace_id}/memory/link")
async def link_workspace_file(
    workspace_id: str,
    body: dict[str, str],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = str(user.get("id") or user.get("user_id") or "default")
    path = Path(body.get("path") or "")
    if not path.is_absolute():
        path = workspace_root(workspace_id) / path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    memory_id = await MemoryIndexBridge(user_id=user_id).link_file(path, workspace_id=workspace_id)
    WorkspaceIndexer(workspace_root(workspace_id)).on_file_change(path, "linked")
    return {"memory_id": memory_id}
