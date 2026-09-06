"""Authenticated floor-plan proposal and compliance endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from .compliance import check
from .refurb import guidance
from .vision import analyze_image

router = APIRouter(prefix="/api/property/floor-plan", tags=["property-floor-plan"])


class RoomsBody(BaseModel):
    property_type: str = "hmo"
    region: str = "england"
    rooms: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/extraction-guide")
async def extraction_guide(_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "estimated_dimensions": True,
        "proposal_only": True,
        "required_room_fields": ["label", "room_type", "occupancy_type", "floor_area_sqm"],
        "next_step": "Review and correct proposed rooms before compliance or refurbishment guidance.",
    }


@router.post("/analyze-image")
async def analyze_image_route(image: UploadFile = File(...), mode: str = "boq", model: str | None = None, _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Process an uploaded plan in quarantine; never accept an arbitrary local path."""
    from keprix.security.rate_limiter import rate_limit
    actor = str(_user.get("id") or _user.get("username") or "anonymous")
    if not rate_limit("floor_plan_analyze", actor, limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail={"error": "floor_plan_rate_limited", "retry_after_seconds": 60})
    allowed = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/bmp": ".bmp"}
    suffix = allowed.get((image.content_type or "").lower())
    if not suffix:
        raise HTTPException(status_code=415, detail={"error": "unsupported_image_type"})
    from keprix.auth.config import data_dir
    import os
    import tempfile

    quarantine = Path(data_dir()) / "quarantine" / "floor-plan"
    quarantine.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="floor-plan-", suffix=suffix, dir=quarantine)
    try:
        total = 0
        with os.fdopen(fd, "wb") as target:
            while chunk := await image.read(1024 * 1024):
                total += len(chunk)
                if total > 20 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail={"error": "image_too_large", "max_bytes": 20 * 1024 * 1024})
                target.write(chunk)
        result = analyze_image(temp_name, mode=mode, model=model)
        if result.get("status") == "error":
            raise HTTPException(status_code=422, detail=result)
        return result
    finally:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass


@router.post("/compliance")
async def compliance(body: RoomsBody, _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not body.rooms:
        raise HTTPException(status_code=400, detail="At least one room is required")
    return check(body.rooms, body.property_type, body.region)


@router.post("/refurb-guidance")
async def refurb_guidance(body: RoomsBody, _user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not body.rooms:
        raise HTTPException(status_code=400, detail="At least one room is required")
    return {"property_type": body.property_type, "technical_considerations": guidance(body.rooms, body.property_type)}
