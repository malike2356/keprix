"""Inbound kill switch for Scout / channel operators: POST /keprix/kill."""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from keprix.security.aiva_scout import get_aiva_scout_guard

router = APIRouter(prefix="/keprix", tags=["keprix-scout-kill"])


def _kill_token() -> str:
    return (
        os.environ.get("KEPRIX_SCOUT_KILL_TOKEN", "").strip()
        or os.environ.get("CARINA_KEPRIX_SHARED_TOKEN", "").strip()
        or os.environ.get("SCOUT_API_KEY", "").strip()
    )


def _authorize(request: Request, x_scout_kill_token: str | None) -> None:
    expected = _kill_token()
    if not expected:
        raise HTTPException(status_code=503, detail="Kill token is not configured")
    auth = request.headers.get("Authorization", "")
    bearer = ""
    if auth.lower().startswith("bearer "):
        bearer = auth[7:].strip()
    provided = (x_scout_kill_token or "").strip() or bearer
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing kill token")


@router.post("/kill")
async def activate_kill(
    request: Request,
    x_scout_kill_token: str | None = Header(default=None, alias="X-Scout-Kill-Token"),
) -> dict[str, Any]:
    """Scout dashboard / channel /kill -> suspend Keprix agent execution."""
    _authorize(request, x_scout_kill_token)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    workspace_id = str(body.get("workspace_id") or "").strip() or None
    scope = str(body.get("scope") or ("workspace" if workspace_id else "agent_global")).strip()
    reason = str(body.get("reason") or "Scout kill switch activated")
    activated_by = str(body.get("activated_by") or body.get("source") or "scout")

    try:
        result = get_aiva_scout_guard().activate_kill(
            workspace_id=workspace_id,
            scope=scope,
            reason=reason,
            activated_by=activated_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"ok": True, "kill": result}


@router.post("/resume")
async def resume_kill(
    request: Request,
    x_scout_kill_token: str | None = Header(default=None, alias="X-Scout-Kill-Token"),
) -> dict[str, Any]:
    """Clear kill switch for a workspace or globally."""
    _authorize(request, x_scout_kill_token)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    workspace_id = str(body.get("workspace_id") or "").strip() or None
    scope = str(body.get("scope") or "").strip() or None
    result = get_aiva_scout_guard().deactivate_kill(workspace_id=workspace_id, scope=scope)
    return {"ok": True, **result}


@router.get("/kill/status")
async def kill_status(
    request: Request,
    workspace_id: str | None = None,
    x_scout_kill_token: str | None = Header(default=None, alias="X-Scout-Kill-Token"),
) -> dict[str, Any]:
    _authorize(request, x_scout_kill_token)
    guard = get_aiva_scout_guard()
    status = guard.check_kill(workspace_id)
    return {
        "ok": True,
        "active": status.active,
        "scope": status.scope,
        "workspace_id": status.workspace_id or workspace_id,
        "reason": status.reason,
        "activated_by": status.activated_by,
        "activated_at": status.activated_at,
        "sensors": guard.sensors(),
        "active_kills": guard.list_active_kills(),
    }


@router.get("/scout/sensors")
async def list_sensors() -> dict[str, Any]:
    """Public sensor catalog for Scout dashboard registration (C04/K06)."""
    guard = get_aiva_scout_guard()
    return {
        "product": "keprix",
        "target": "keprix-aiva",
        "sensors": guard.sensors(),
        "monitored": True,
    }
