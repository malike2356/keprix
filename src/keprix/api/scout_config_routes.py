"""Internal REST API for conversational Scout pairing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.configure import scout_config_service as svc

router = APIRouter(tags=["scout-config"])


class ConfigureBody(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)


class DisconnectBody(BaseModel):
    accept_responsibility: bool = False


@router.get("/api/internal/scout")
async def scout_status(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return await svc.scout_status_payload()


@router.get("/api/internal/scout/requirements")
async def scout_requirements(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return svc.scout_requirements_payload()


@router.post("/api/internal/scout/collect")
async def scout_collect(body: ConfigureBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = await svc.scout_collect(body.credentials)
    if not result.get("ok") and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    result.pop("credentials", None)
    return result


@router.post("/api/internal/scout")
async def scout_connect(body: ConfigureBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    result = await svc.scout_connect(body.credentials, user_id=user_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Connect failed")
    result.pop("credentials", None)
    return result


@router.delete("/api/internal/scout")
async def scout_disconnect(body: DisconnectBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    result = await svc.scout_disconnect(
        user_id=user_id,
        accept_responsibility=body.accept_responsibility,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Disconnect failed")
    return result
