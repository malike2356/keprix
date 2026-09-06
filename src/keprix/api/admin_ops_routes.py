"""Platform-admin impersonation and reversible billing operations."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.auth.session import auth_manager
from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.subscriptions.lifecycle import pause_subscription, resume_subscription
from keprix.security.audit import audit_log

router = APIRouter(prefix="/api/admin", tags=["admin-ops"])


class ImpersonateBody(BaseModel):
    target_user_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)


class TargetBody(BaseModel):
    user_id: str = Field(min_length=1)


class TierBody(BaseModel):
    tier: str = Field(min_length=1)


@router.post("/impersonate")
async def impersonate(body: ImpersonateBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    target = next((row for row in auth_manager.list_users() if str(row.get("id")) == body.target_user_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="target_user_not_found")
    token = auth_manager.create_session(str(target["username"]), device_label=f"impersonation:{body.workspace_id}", ttl_seconds=900)
    await audit_log("admin_impersonation_started", user_id=admin.get("id"), event_data={"target_user_id": body.target_user_id, "workspace_id": body.workspace_id, "impersonated": True})
    return {"token": token, "token_type": "bearer", "expires_in": 900, "impersonated": True, "workspace_id": body.workspace_id, "target_user_id": body.target_user_id}


@router.post("/impersonate/end")
async def end_impersonate(body: dict[str, str], admin: dict = Depends(require_admin)) -> dict[str, Any]:
    token = str(body.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token_required")
    auth_manager.revoke_token(token)
    await audit_log("admin_impersonation_ended", user_id=admin.get("id"), event_data={"impersonated": True})
    return {"ok": True, "revoked": True}


@router.post("/subscriptions/pause")
async def pause(body: TargetBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = await pause_subscription(body.user_id)
    await audit_log("admin_subscription_paused", user_id=admin.get("id"), event_data={"target_user_id": body.user_id})
    return {"subscription": result}


@router.post("/subscriptions/resume")
async def resume(body: TargetBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = await resume_subscription(body.user_id)
    await audit_log("admin_subscription_resumed", user_id=admin.get("id"), event_data={"target_user_id": body.user_id})
    return {"subscription": result}


@router.post("/workspaces/{workspace_id}/tier")
async def assign_tier(workspace_id: str, body: TierBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    config = load_billing_config()
    if config is not None and config.plan_by_id(body.tier) is None:
        raise HTTPException(status_code=422, detail="unknown_tier")
    result = await get_billing_store().save_subscription(workspace_id, {"plan_id": body.tier, "status": "active", "tier_assigned_by": admin.get("id")})
    await audit_log("admin_tier_assigned", user_id=admin.get("id"), event_data={"workspace_id": workspace_id, "tier": body.tier})
    return {"workspace_id": workspace_id, "tier": body.tier, "subscription": result}
