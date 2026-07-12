"""Agent OS client kit and simplified mode routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from keprix.agent_os.client_kit_exporter import ClientKitExporter
from keprix.agent_os.client_kit_importer import ClientKitImporter
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.simplified_mode import SimplifiedModeConfig, blocked_path, get_simplified_mode, set_simplified_mode
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class ExportBody(BaseModel):
    name: str = Field(default="client", min_length=1)
    include_workspace_template: bool = True


class SimplifiedBody(BaseModel):
    simplified_mode: bool = False
    hide_terminal_coding: bool = True
    documents_read_only: bool = False
    allowed_paths: list[str] = Field(default_factory=lambda: ["/agent-os", "/agent-apps", "/chat", "/documents", "/home", "/launcher", "/settings"])


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _require_admin(user: dict[str, Any]) -> None:
    if str(user.get("role") or "user") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin role required")


@router.get("/client-kit/preview")
async def preview_client_kit(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    return ClientKitExporter().preview(user_id=str(user.get("id") or "default"))


@router.post("/client-kit/export")
async def export_client_kit(body: ExportBody, user: dict = Depends(get_current_user)) -> FileResponse:
    _guard_enabled()
    result = ClientKitExporter().export(
        name=body.name,
        user_id=str(user.get("id") or "default"),
        include_workspace_template=body.include_workspace_template,
    )
    record_onboarding_event_for_user(user, "client_kit.exported")
    return FileResponse(
        path=str(result.path),
        filename=result.path.name,
        media_type="application/zip",
        background=BackgroundTask(lambda: result.path.unlink(missing_ok=True)),
    )


@router.post("/client-kit/import")
async def import_client_kit(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _require_admin(user)
    suffix = Path(file.filename or "client-kit.zip").suffix or ".zip"
    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_path = Path(temp.name)
    try:
        temp.write(await file.read())
        temp.close()
        imported = ClientKitImporter().import_zip(temp_path)
        return {"imported": imported}
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/simplified-mode")
async def get_simplified(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return get_simplified_mode().to_dict()


@router.put("/simplified-mode")
async def update_simplified(body: SimplifiedBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _require_admin(user)
    return set_simplified_mode(SimplifiedModeConfig(**body.model_dump())).to_dict()


@router.get("/simplified-mode/guard")
async def simplified_guard(path: str = Query(..., min_length=1), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    blocked = blocked_path(path)
    return {"blocked": blocked, "redirect": "/agent-os" if blocked else None}
