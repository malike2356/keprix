"""Internal APIs for integrations, workspace prefs, and companion pairing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.configure import companion_config_service as companion_svc
from keprix.configure import integration_config_service as integration_svc
from keprix.configure import workspace_config_service as workspace_svc

router = APIRouter(tags=["wave2-config"])


class CredsBody(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)


class WorkspaceBody(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class CompanionCreateBody(BaseModel):
    workspace_id: str = "default"
    server_url: str | None = None


class CompanionConfirmBody(BaseModel):
    pairing_id: str
    code: str
    device_name: str
    platform: str = "ios"


# --- integrations ---

@router.get("/api/internal/integrations")
async def list_integrations(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return integration_svc.list_integrations_payload()


@router.get("/api/internal/integrations/{integration_id}/requirements")
async def integration_requirements(integration_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    payload = integration_svc.requirements_payload(integration_id)
    if not payload.get("ok"):
        raise HTTPException(status_code=404, detail=payload.get("error") or "Not found")
    return payload


@router.post("/api/internal/integrations/{integration_id}/collect")
async def integration_collect(
    integration_id: str,
    body: CredsBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = integration_svc.collect_and_maybe_save(integration_id, body.credentials)
    if not result.get("ok") and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/api/internal/integrations/{integration_id}")
async def integration_configure(
    integration_id: str,
    body: CredsBody,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = integration_svc.configure_integration(integration_id, body.credentials)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed")
    return result


@router.delete("/api/internal/integrations/{integration_id}")
async def integration_remove(
    integration_id: str,
    webhook_id: str | None = None,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    result = integration_svc.remove_integration(integration_id, webhook_id=webhook_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed")
    return result


# --- workspace ---

@router.get("/api/internal/workspace")
async def workspace_list(_admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return workspace_svc.list_workspace_payload()


@router.put("/api/internal/workspace")
async def workspace_update(body: WorkspaceBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = workspace_svc.configure_workspace(body.settings)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Failed")
    return result


# --- companion ---

@router.get("/api/internal/companion")
async def companion_list(workspace_id: str = "default", _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return companion_svc.list_companion_payload(workspace_id)


@router.post("/api/internal/companion/pair")
async def companion_create(body: CompanionCreateBody, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return companion_svc.create_pairing_payload(
        workspace_id=body.workspace_id,
        server_url=body.server_url,
    )


@router.post("/api/internal/companion/confirm")
async def companion_confirm(body: CompanionConfirmBody) -> dict[str, Any]:
    result = companion_svc.confirm_pairing_payload(
        pairing_id=body.pairing_id,
        code=body.code,
        device_name=body.device_name,
        platform=body.platform,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error") or "Invalid pairing")
    return result


@router.delete("/api/internal/companion/{device_id}")
async def companion_remove(device_id: str, _admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = companion_svc.remove_device_payload(device_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Not found")
    return result
