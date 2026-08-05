"""Client approval and token security admin API.

Endpoints:
  GET    /api/security/clients
  POST   /api/security/clients/approve
  POST   /api/security/clients/deny
  POST   /api/security/clients/revoke
  GET    /api/security/tokens/suspensions
  POST   /api/security/tokens/suspend
  POST   /api/security/tokens/unsuspend
  GET    /api/security/tokens/alerts
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.security.client_approval.store import get_client_approval_store
from keprix.security.token_security.alerting import get_alert_manager
from keprix.security.token_security.monitor import get_token_security_monitor

router = APIRouter(prefix="/api/security", tags=["security"])

ClientDecision = Literal["approved", "denied", "revoked"]


def _is_owner(user: dict[str, Any]) -> bool:
    role = str(user.get("role") or "").lower()
    if role in {"admin", "owner", "superadmin", "developer"}:
        return True
    roles = user.get("roles")
    if isinstance(roles, (list, tuple, set)):
        return any(str(r).lower() in {"admin", "owner", "superadmin", "developer"} for r in roles)
    return bool(user.get("is_admin"))


def _require_owner(user: dict[str, Any]) -> None:
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail="Owner or developer access required")


class ClientDecisionBody(BaseModel):
    fingerprint: str
    token_id: str
    note: str | None = None
    approval_days: int = Field(default=30, ge=1, le=365)


class TokenSuspendBody(BaseModel):
    token_id: str
    reason: str = "manual_suspend"


class TokenUnsuspendBody(BaseModel):
    token_id: str


@router.get("/clients")
async def list_clients(
    status: str | None = Query(default=None),
    token_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    store = get_client_approval_store()
    status_filter = status if status in {"pending", "approved", "denied", "revoked", "expired"} else None
    clients = store.list(status=status_filter, token_id=token_id, limit=limit)  # type: ignore[arg-type]
    return {
        "clients": [c.to_dict() for c in clients],
        "counts": {
            "pending": len(store.list(status="pending", limit=500)),
            "approved": len(store.list(status="approved", limit=500)),
            "denied": len(store.list(status="denied", limit=500)),
            "revoked": len(store.list(status="revoked", limit=500)),
            "expired": len(store.list(status="expired", limit=500)),
        },
    }


@router.post("/clients/approve")
async def approve_client(
    body: ClientDecisionBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    decided_by = str(user.get("id") or user.get("email") or user.get("username") or "owner")
    record = get_client_approval_store().decide(
        body.fingerprint,
        body.token_id,
        status="approved",
        decided_by=decided_by,
        note=body.note,
        approval_days=body.approval_days,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": record.to_dict()}


@router.post("/clients/deny")
async def deny_client(
    body: ClientDecisionBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    decided_by = str(user.get("id") or user.get("email") or user.get("username") or "owner")
    record = get_client_approval_store().decide(
        body.fingerprint,
        body.token_id,
        status="denied",
        decided_by=decided_by,
        note=body.note,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": record.to_dict()}


@router.post("/clients/revoke")
async def revoke_client(
    body: ClientDecisionBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    decided_by = str(user.get("id") or user.get("email") or user.get("username") or "owner")
    record = get_client_approval_store().decide(
        body.fingerprint,
        body.token_id,
        status="revoked",
        decided_by=decided_by,
        note=body.note,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": record.to_dict()}


@router.get("/tokens/suspensions")
async def list_suspensions(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _require_owner(user)
    return {"suspensions": get_token_security_monitor().list_suspensions()}


@router.post("/tokens/suspend")
async def suspend_token(
    body: TokenSuspendBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    created_by = str(user.get("id") or user.get("email") or "owner")
    get_token_security_monitor().suspend(body.token_id, reason=body.reason, created_by=created_by)
    return {"ok": True, "token_id": body.token_id, "suspended": True}


@router.post("/tokens/unsuspend")
async def unsuspend_token(
    body: TokenUnsuspendBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    created_by = str(user.get("id") or user.get("email") or "owner")
    ok = get_token_security_monitor().unsuspend(body.token_id, created_by=created_by)
    if not ok:
        raise HTTPException(status_code=404, detail="No active suspension for token")
    return {"ok": True, "token_id": body.token_id, "suspended": False}


@router.get("/tokens/alerts")
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _require_owner(user)
    return {"alerts": get_alert_manager().recent(limit=limit)}
