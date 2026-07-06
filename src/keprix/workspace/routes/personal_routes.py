"""Profile and preferences routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from keprix.auth.dependencies import get_current_user
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import PrefsUpdate, ProfileUpdate

router = APIRouter(prefix="/api/workspace", tags=["workspace-personal"])


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.get_profile(user)


@router.put("/profile")
async def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.update_profile(user, **body.model_dump(exclude_none=True))


@router.get("/prefs")
async def get_prefs(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.get_prefs(user)


@router.put("/prefs")
async def update_prefs(body: PrefsUpdate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return workspace_repo.update_prefs(user, **body.model_dump(exclude_none=True))
