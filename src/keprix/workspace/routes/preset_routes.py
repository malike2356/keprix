"""Preset routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import PresetCreate, PresetUpdate

router = APIRouter(prefix="/api/workspace/presets", tags=["workspace-presets"])


@router.post("", status_code=201)
async def create_preset(body: PresetCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.create_preset(user, **body.model_dump())


@router.get("")
async def list_presets(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": workspace_repo.list_presets(user)}


@router.put("/{preset_id}")
async def update_preset(
    preset_id: str,
    body: PresetUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.update_preset(user, preset_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Preset not found") from None


@router.delete("/{preset_id}", status_code=200)
async def delete_preset(preset_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_preset(user, preset_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Preset not found") from None


@router.post("/{preset_id}/activate")
async def activate_preset(preset_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        preset = workspace_repo.activate_preset(user, preset_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Preset not found") from None
    prefs = workspace_repo.update_prefs(user, active_preset_id=preset_id)
    return {"preset": preset, "prefs": prefs}
