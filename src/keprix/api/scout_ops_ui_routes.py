"""Session-auth Scout kill / sensors panel for standalone Web UI operators."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from keprix.api.auth import require_api_auth
from keprix.security.aiva_scout import get_aiva_scout_guard

router = APIRouter(prefix="/api/scout-ops", tags=["scout-ops-ui"])


def _workspace(workspace_id: str | None, x_workspace_id: str | None) -> str | None:
    raw = (workspace_id or x_workspace_id or "").strip()
    return raw or None


@router.get("/kill/status")
async def kill_status(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    guard = get_aiva_scout_guard()
    status = guard.check_kill(ws)
    return {
        "ok": True,
        "active": status.active,
        "scope": status.scope,
        "workspace_id": status.workspace_id or ws,
        "reason": status.reason,
        "activated_by": status.activated_by,
        "activated_at": status.activated_at,
        "sensors": guard.sensors(),
        "active_kills": guard.list_active_kills(),
    }


@router.post("/kill")
async def activate_kill(
    body: dict[str, Any],
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    workspace_id = str(body.get("workspace_id") or "").strip() or _workspace(None, x_workspace_id)
    scope = str(body.get("scope") or ("workspace" if workspace_id else "agent_global")).strip()
    reason = str(body.get("reason") or "Operator kill switch activated from Keprix Web UI")
    activated_by = str(body.get("activated_by") or _user or "web-ui")
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
    body: dict[str, Any] | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    body = body or {}
    workspace_id = str(body.get("workspace_id") or "").strip() or _workspace(None, x_workspace_id)
    scope = str(body.get("scope") or "").strip() or None
    result = get_aiva_scout_guard().deactivate_kill(workspace_id=workspace_id, scope=scope)
    return {"ok": True, **result}


@router.get("/sensors")
async def list_sensors(_user: str = Depends(require_api_auth)) -> dict[str, Any]:
    guard = get_aiva_scout_guard()
    return {
        "product": "keprix",
        "target": "keprix-standalone",
        "sensors": guard.sensors(),
        "monitored": True,
    }
