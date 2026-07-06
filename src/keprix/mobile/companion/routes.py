"""Companion pairing routes (Prompt 25)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.mobile.companion.pairing import (
    get_companion_store,
    lan_ip_candidates,
    pairing_qr_payload,
    pairing_qr_png_data_uri,
)


router = APIRouter(prefix="/api/companion", tags=["companion"])


class PairConfirmBody(BaseModel):
    pairing_id: str
    code: str = Field(..., min_length=4, max_length=12)
    device_name: str = Field(..., min_length=1, max_length=120)
    platform: str = Field(default="ios", pattern="^(ios|android|macos|windows)$")


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


@router.post("/pair")
async def initiate_pairing(
    workspace_id: str = "default",
    server_url: str | None = None,
    _admin: dict = Depends(require_admin),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    pairing = get_companion_store().create_pairing(workspace_id, created_by=_user_id(user))
    host = lan_ip_candidates()[0] if lan_ip_candidates() else "127.0.0.1"
    resolved_url = (server_url or f"http://{host}:8000").rstrip("/")
    payload = pairing_qr_payload(
        server_url=resolved_url,
        pairing_id=str(pairing["pairing_id"]),
        code=str(pairing["code"]),
    )
    return {
        "pairing_id": pairing["pairing_id"],
        "code": pairing["code"],
        "expires_at": pairing["expires_at"],
        "qr_payload": payload,
        "qr": pairing_qr_png_data_uri(payload),
    }


@router.post("/pair/confirm")
async def confirm_pairing(body: PairConfirmBody) -> dict[str, Any]:
    result = get_companion_store().confirm_pairing(
        body.pairing_id,
        code=body.code.upper(),
        device_name=body.device_name,
        platform=body.platform,
    )
    if result is None:
        raise HTTPException(status_code=422, detail="Invalid or expired pairing code")
    return result


@router.get("/paired")
async def list_paired_devices(
    workspace_id: str = "default",
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    devices = get_companion_store().list_paired(workspace_id)
    return {"devices": devices}


@router.delete("/paired/{device_id}")
async def unpair_device(
    device_id: str,
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not get_companion_store().unpair(device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"removed": True, "device_id": device_id}
