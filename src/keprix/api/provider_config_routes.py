"""Internal REST API for conversational provider configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.configure import provider_config_service as svc

router = APIRouter(tags=["provider-config"])


class ConfigureBody(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)


class DefaultBody(BaseModel):
    provider_id: str


@router.get("/api/internal/providers")
async def list_internal_providers(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return svc.list_providers_payload()


@router.get("/api/internal/providers/{provider_id}/requirements")
async def provider_requirements(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    payload = svc.requirements_payload(provider_id)
    if not payload.get("ok"):
        raise HTTPException(status_code=404, detail=payload.get("error") or "Not found")
    return payload


@router.post("/api/internal/providers/{provider_id}")
async def save_internal_provider(
    provider_id: str,
    body: ConfigureBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = svc.configure_provider(provider_id, body.credentials)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Save failed")
    result.pop("credentials", None)
    return result


@router.post("/api/internal/providers/{provider_id}/collect")
async def collect_internal_provider(
    provider_id: str,
    body: ConfigureBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = await svc.collect_and_maybe_save(provider_id, body.credentials)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Collect failed")
    result.pop("credentials", None)
    return result


@router.post("/api/internal/providers/{provider_id}/test")
async def test_internal_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return svc.test_provider_payload(provider_id)


@router.delete("/api/internal/providers/{provider_id}")
async def delete_internal_provider(provider_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = svc.remove_provider_payload(provider_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Not found")
    return result


@router.post("/api/internal/providers/default")
async def set_default_internal_provider(body: DefaultBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = svc.set_default_payload(body.provider_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed")
    return result
