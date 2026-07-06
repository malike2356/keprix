"""Legal acceptance HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from keprix.api.auth import require_admin, require_api_auth
from keprix.legal.middleware import hash_user_agent, pending_policies
from keprix.legal.policy_store import get_active_policies, get_policy_text
from keprix.legal.store import get_acceptance_store
from keprix.privacy.consent import get_consent_store
from keprix.security.audit import hash_ip

router = APIRouter(prefix="/api/legal", tags=["legal"])


def _workspace_id(request: Request) -> str:
    return request.headers.get("x-workspace-id", "default").strip() or "default"


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id", "").strip() or "local"


class AcceptBody(BaseModel):
    policy_types: list[str] = Field(..., min_length=1)


class AcceptOnBehalfBody(BaseModel):
    user_id: str
    policy_types: list[str] = Field(..., min_length=1)
    reason: str = ""


@router.get("/policies")
async def list_policies() -> dict[str, Any]:
    return {"policies": [policy.to_dict() for policy in get_active_policies()]}


@router.get("/policies/{policy_type}/text")
async def policy_text(policy_type: str) -> PlainTextResponse:
    return PlainTextResponse(get_policy_text(policy_type), media_type="text/markdown")


@router.get("/status")
async def legal_status(request: Request, _user: str = Depends(require_api_auth)) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    user_id = _user_id(request)
    pending = pending_policies(workspace_id, user_id)
    return {"pending": pending, "all_accepted": len(pending) == 0}


@router.post("/accept")
async def accept_policies(
    body: AcceptBody,
    request: Request,
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    user_id = _user_id(request)
    store = get_acceptance_store()
    active = {p.policy_type: p for p in get_active_policies()}
    accepted: list[str] = []
    ip_hash = hash_ip(request.client.host if request.client else "")
    ua_hash = hash_user_agent(request.headers.get("User-Agent", ""))
    for policy_type in body.policy_types:
        policy = active.get(policy_type)
        if policy is None:
            raise HTTPException(status_code=400, detail=f"Unknown policy type: {policy_type}")
        store.record(
            workspace_id=workspace_id,
            user_id=user_id,
            policy_type=policy.policy_type,
            policy_version=policy.version,
            accepted_ip_hash=ip_hash,
            user_agent_hash=ua_hash,
            source="web_gate",
        )
        get_consent_store().record(
            user_id=user_id,
            purpose="data_processing",
            granted=True,
            ip_hash=ip_hash,
            metadata={
                "lawful_basis": "consent",
                "version": policy.version,
                "source": "legal_gate",
                "policy_type": policy.policy_type,
            },
        )
        accepted.append(policy_type)
    pending = pending_policies(workspace_id, user_id)
    from keprix.governance.audit_events import emit_audit_event

    for policy_type in accepted:
        await emit_audit_event(
            "legal_acceptance_recorded",
            workspace_id=workspace_id,
            actor_type="user",
            actor_id=user_id,
            summary=f"Legal policy accepted: {policy_type}",
            subject_type="legal_policy",
            subject_id=policy_type,
            detail={"policy_type": policy_type},
            severity="info",
        )
    return {"accepted": accepted, "all_accepted": len(pending) == 0}


@router.post("/accept-on-behalf")
async def accept_on_behalf(
    body: AcceptOnBehalfBody,
    request: Request,
    admin: str = Depends(require_admin),
) -> dict[str, Any]:
    workspace_id = _workspace_id(request)
    store = get_acceptance_store()
    active = {p.policy_type: p for p in get_active_policies()}
    accepted: list[str] = []
    ip_hash = hash_ip(request.client.host if request.client else "")
    for policy_type in body.policy_types:
        policy = active.get(policy_type)
        if policy is None:
            raise HTTPException(status_code=400, detail=f"Unknown policy type: {policy_type}")
        store.record(
            workspace_id=workspace_id,
            user_id=body.user_id,
            policy_type=policy.policy_type,
            policy_version=policy.version,
            accepted_ip_hash=ip_hash,
            source="admin_on_behalf",
        )
        accepted.append(policy_type)
    return {"accepted": accepted, "recorded_by": admin, "reason": body.reason}


@router.get("/acceptances")
async def list_acceptances(
    request: Request,
    policy_type: str | None = None,
    policy_version: str | None = None,
    _admin: str = Depends(require_admin),
) -> dict[str, Any]:
    rows = get_acceptance_store().list_for_workspace(
        _workspace_id(request),
        policy_type=policy_type,
        policy_version=policy_version,
    )
    return {"acceptances": rows}


@router.get("/acceptances/export")
async def export_acceptances(
    request: Request,
    _admin: str = Depends(require_admin),
) -> PlainTextResponse:
    csv_text = get_acceptance_store().export_csv(_workspace_id(request))
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="legal_acceptances.csv"'},
    )
