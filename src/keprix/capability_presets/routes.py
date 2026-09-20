"""FastAPI routes for capability presets."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.capability_presets import (
    PresetValidationError,
    apply_preset,
    diff_presets,
    get_active_state,
    list_available_presets,
    show_preset,
)

router = APIRouter(prefix="/api/capability-presets", tags=["capability-presets"])


class ApplyBody(BaseModel):
    name: str
    strict_plugins: bool | None = None


class DiffBody(BaseModel):
    from_name: str | None = None
    to_name: str = Field(..., min_length=1)


@router.get("")
async def list_capability_presets(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    presets = list_available_presets()
    return {
        "presets": [
            {
                "name": p["name"],
                "description": p.get("description"),
                "version": p.get("version"),
                "soft_wall": p.get("soft_wall"),
                "seams": p.get("seams"),
            }
            for p in presets
        ],
        "active": get_active_state().get("active"),
    }


@router.get("/active")
async def active_capability_preset(
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return get_active_state()


@router.get("/{name}")
async def get_capability_preset(
    name: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return show_preset(name)
    except PresetValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/apply")
async def apply_capability_preset(
    body: ApplyBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    who = str(user.get("email") or user.get("id") or "api")
    try:
        return apply_preset(
            body.name, who=who, strict_plugins=body.strict_plugins
        )
    except PresetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/diff")
async def diff_capability_presets(
    body: DiffBody,
    _user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return diff_presets(body.from_name, body.to_name)
    except PresetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
