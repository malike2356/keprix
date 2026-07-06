"""Governance bridge HTTP routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.governance.client import get_governance_client
from keprix.governance.enrollment import GovernanceEnrollmentError
from keprix.governance.event_reporter import queue_audit_event
from keprix.governance.policy_receiver import apply_policy
from keprix.governance.signing import verify_signature
from keprix.governance.store import get_governance_store
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/governance", tags=["governance"])


class GovernanceConnectBody(BaseModel):
    provider_endpoint: str = Field(..., min_length=8)
    api_key: str = Field(..., min_length=8)


class GovernanceDisconnectBody(BaseModel):
    accept_responsibility: bool = False


class GovernanceWebhookBody(BaseModel):
    type: str
    policy_type: str | None = None
    policy_value: dict[str, Any] | None = None
    directive_type: str | None = None
    payload: dict[str, Any] | None = None


@router.get("/status")
async def governance_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await get_governance_client().status()


@router.post("/connect")
async def governance_connect(body: GovernanceConnectBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    try:
        config = await get_governance_client().connect(
            user_id=user_id,
            provider_endpoint=body.provider_endpoint.strip(),
            api_key=body.api_key.strip(),
        )
    except GovernanceEnrollmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "config": config}


@router.post("/disconnect")
async def governance_disconnect(body: GovernanceDisconnectBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    if not body.accept_responsibility:
        raise HTTPException(
            status_code=400,
            detail="You must confirm: I accept responsibility for ungoverned operation.",
        )
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    config = await get_governance_client().disconnect(user_id=user_id, accept_responsibility=True)
    return {"ok": True, "config": config}


@router.post("/webhook")
async def governance_webhook(request: Request) -> dict[str, Any]:
    raw = await request.body()
    cfg = await get_governance_store().get_config()
    if not cfg.get("enabled"):
        raise HTTPException(status_code=403, detail="Governance is not enabled")
    api_key = await get_governance_client().resolve_api_key(user_id="system")
    if not api_key:
        raise HTTPException(status_code=403, detail="Governance API key unavailable")
    signature = request.headers.get("x-governance-signature") or request.headers.get("X-Governance-Signature")
    if not verify_signature(api_key, raw, signature):
        raise HTTPException(status_code=401, detail="Invalid Governance signature")

    payload = json.loads(raw.decode("utf-8"))
    event_type = str(payload.get("type") or payload.get("event") or "")
    if event_type == "policy":
        policy_type = str(payload.get("policy_type") or "")
        policy_value = dict(payload.get("policy_value") or payload.get("value") or {})
        row = await apply_policy(policy_type, policy_value)
        await queue_audit_event(
            "governance_policy_applied",
            {"policy_type": policy_type, "policy_id": row.get("id")},
        )
        return {"ok": True, "applied": row}
    if event_type == "kill":
        directive = str(payload.get("directive_type") or payload.get("directive") or "")
        await apply_policy(directive, dict(payload.get("payload") or {}))
        await queue_audit_event("governance_kill_directive", {"directive": directive})
        return {"ok": True, "directive": directive}
    raise HTTPException(status_code=400, detail="Unsupported webhook event")


@router.get("/events")
async def governance_events(admin: dict = Depends(require_admin), limit: int = 50) -> dict[str, Any]:
    items = await get_governance_store().list_recent_events(limit=limit)
    return {"items": items}


@router.post("/heartbeat")
async def heartbeat(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    return await get_governance_client().heartbeat(user_id=user_id)


@router.post("/events/flush")
async def flush_events_route(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    user_id = str(admin.get("id") or admin.get("username") or "admin")
    return await get_governance_client().flush_events(user_id=user_id)
