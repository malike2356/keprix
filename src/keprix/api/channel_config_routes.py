"""Internal REST API for conversational channel configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.channels import channel_config_service as svc

router = APIRouter(tags=["channel-config"])


class ConfigureBody(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)


@router.get("/api/internal/channels")
async def list_internal_channels(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return svc.list_channels_payload()


@router.get("/api/internal/channels/{channel_id}/requirements")
async def channel_requirements(
    channel_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    payload = svc.requirements_payload(channel_id)
    if not payload.get("ok"):
        raise HTTPException(status_code=404, detail=payload.get("error") or "Not found")
    return payload


@router.post("/api/internal/channels/{channel_id}")
async def save_internal_channel(
    channel_id: str,
    body: ConfigureBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = await svc.configure_and_test(channel_id, body.credentials)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Save failed")
    return result


@router.delete("/api/internal/channels/{channel_id}")
async def delete_internal_channel(
    channel_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = svc.remove_channel_payload(channel_id)
    if not result.get("ok") and result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/api/internal/channels/{channel_id}/collect")
async def collect_internal_channel(
    channel_id: str,
    body: ConfigureBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = await svc.collect_and_maybe_save(channel_id, body.credentials)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Collect failed")
    result.pop("credentials", None)
    return result


@router.post("/api/internal/channels/{channel_id}/test")
async def test_internal_channel(
    channel_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    return await svc.test_channel_payload(channel_id)
