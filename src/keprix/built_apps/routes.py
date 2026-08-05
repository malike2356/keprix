"""Built app HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from keprix.api.auth import require_api_auth
from keprix.built_apps.registry import get_installed_app, list_installed_apps_summary

router = APIRouter(prefix="/api/built-apps", tags=["built-apps"])


@router.get("")
async def list_built_apps(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    return {"apps": list_installed_apps_summary()}


@router.get("/{app_id}")
async def get_built_app(app_id: str, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    manifest = get_installed_app(app_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Built app not found")
    return {"app": manifest.model_dump(exclude_none=True)}
