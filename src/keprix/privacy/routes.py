"""Privacy and GDPR HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from keprix.privacy.consent import get_consent_store
from keprix.privacy.dsar import get_dsar_store
from keprix.privacy.erasure import erase_user_data
from keprix.privacy.retention import (
    apply_retention_policies,
    get_last_retention_run,
    get_retention_policies,
    set_retention_policy,
)
from keprix.security.audit import hash_ip

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


def _user_id(request: Request) -> str:
    header = request.headers.get("x-user-id", "").strip()
    return header or "local"


class ConsentBody(BaseModel):
    purpose: str = Field(..., min_length=1)
    granted: bool


class DsarBody(BaseModel):
    request_type: str = "access"


class ErasureBody(BaseModel):
    scope: str = "full"
    confirm: bool = False
    dry_run: bool = False


class RetentionBody(BaseModel):
    retain_days: int = Field(..., ge=-1)
    action: str = Field(default="anonymise")


@router.post("/consent")
async def record_consent(body: ConsentBody, request: Request) -> dict[str, Any]:
    user = _user_id(request)
    ip_hash = hash_ip(request.client.host if request.client else "")
    row = get_consent_store().record(
        user_id=user,
        purpose=body.purpose,
        granted=body.granted,
        ip_hash=ip_hash,
    )
    return {"consent": row}


@router.get("/consent")
async def list_consents(request: Request) -> dict[str, Any]:
    user = _user_id(request)
    return {"consents": get_consent_store().list_for_user(user)}


@router.post("/dsar")
async def create_dsar(body: DsarBody, request: Request) -> dict[str, Any]:
    user = _user_id(request)
    row = get_dsar_store().create(user_id=user, request_type=body.request_type)
    from keprix.governance.audit_events import emit_audit_event

    workspace_id = request.headers.get("x-workspace-id", "default").strip() or "default"
    await emit_audit_event(
        "gdpr_dsar_requested",
        workspace_id=workspace_id,
        actor_type="user",
        actor_id=user,
        summary="Data subject access request created",
        subject_type="dsar",
        subject_id=str(row.get("id")),
        severity="notice",
    )
    return {"request": row}


@router.get("/dsar")
async def list_dsar(request: Request) -> dict[str, Any]:
    user = _user_id(request)
    return {"requests": get_dsar_store().list_for_user(user)}


@router.post("/dsar/{request_id}/fulfill")
async def fulfill_dsar(request_id: str) -> dict[str, Any]:
    try:
        row = await get_dsar_store().fulfill(request_id)
    except KeyError as exc:
        raise HTTPException(404, "DSAR not found") from exc
    return {"request": row}


@router.get("/dsar/{request_id}/download")
async def download_dsar(request_id: str) -> FileResponse:
    row = get_dsar_store().get(request_id)
    if row is None or not row.get("export_path"):
        raise HTTPException(404, "Export not ready")
    path = Path(row["export_path"])
    if not path.exists():
        raise HTTPException(404, "Export file missing")
    return FileResponse(path, filename=path.name, media_type="application/json")


@router.post("/erase")
async def erase_data(body: ErasureBody, request: Request) -> dict[str, Any]:
    if not body.dry_run and not body.confirm:
        raise HTTPException(400, "Set confirm=true to erase data")
    user = _user_id(request)
    return await erase_user_data(user, scope=body.scope, dry_run=body.dry_run)


@router.get("/retention")
async def list_retention_policies() -> dict[str, Any]:
    return {
        "policies": get_retention_policies(),
        "last_retention_run": get_last_retention_run(),
    }


@router.put("/retention/{data_category}")
async def update_retention_policy(data_category: str, body: RetentionBody) -> dict[str, Any]:
    try:
        row = set_retention_policy(
            data_category,
            retain_days=body.retain_days,
            action=body.action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "policy": row}


@router.post("/retention/run")
async def run_retention() -> dict[str, Any]:
    return await apply_retention_policies()


@router.get("/health")
async def gdpr_health() -> dict[str, Any]:
    dsar_store = get_dsar_store()
    return {
        "status": "ok",
        "last_retention_run": get_last_retention_run(),
        "pending_dsars": dsar_store.count_pending(),
        "pending_erasures": 0,
    }
