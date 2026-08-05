"""API routes for managed AI credit wallet visibility."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.billing.wallet.enforcer import wallet_status
from keprix.billing.wallet.ledger import admin_adjust, grant_credits, purchase_credits
from keprix.billing.wallet.policy import is_hosted_deployment, resolve_policy, trusted_workspace_id
from keprix.billing.wallet.store import get_ai_credit_store

router = APIRouter(prefix="/api/billing/wallet", tags=["billing-wallet"])


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _is_admin(user: dict[str, Any]) -> bool:
    role = str(user.get("role") or user.get("roles") or "").lower()
    if role in {"admin", "owner", "superadmin"}:
        return True
    roles = user.get("roles")
    if isinstance(roles, (list, tuple, set)):
        return any(str(r).lower() in {"admin", "owner", "superadmin"} for r in roles)
    return bool(user.get("is_admin"))


class AdjustBody(BaseModel):
    credits: int
    note: str | None = None
    workspace_id: str | None = Field(
        default=None,
        description="Ignored for enforcement; admin adjust uses auth workspace only.",
    )


class PurchaseBody(BaseModel):
    credits: int = Field(..., gt=0, le=1_000_000)
    note: str | None = None


@router.get("/status")
async def get_wallet_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _user_id(user)
    # Workspace comes from auth context only (never query/body).
    auth_ws = str(user.get("workspace_id") or user.get("active_workspace_id") or "").strip() or None
    status = await wallet_status(user_id=uid, workspace_id=auth_ws)
    status["hosted"] = is_hosted_deployment()
    return status


@router.get("/ledger")
async def get_wallet_ledger(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    uid = _user_id(user)
    auth_ws = str(user.get("workspace_id") or user.get("active_workspace_id") or "").strip() or None
    ws = trusted_workspace_id(auth_workspace_id=auth_ws)
    policy = await resolve_policy(user_id=uid)
    if not policy.managed_ai_available and not is_hosted_deployment():
        return {
            "workspace_id": ws,
            "entries": [],
            "managed_ai_available": False,
            "message": "Self-hosted and Community Edition use BYOK; no managed ledger.",
        }
    entries = get_ai_credit_store().list_ledger(ws, limit=limit, offset=offset)
    return {
        "workspace_id": ws,
        "entries": [e.to_dict() for e in entries],
        "managed_ai_available": policy.managed_ai_available,
    }


@router.post("/purchase")
async def record_purchase(body: PurchaseBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Record a prepaid credit purchase after Stripe confirms payment.

    Does not create Stripe prices. Callers must use existing Verlox top-up
    price IDs from the shared credentials file.
    """
    uid = _user_id(user)
    policy = await resolve_policy(user_id=uid)
    if not policy.managed_ai_available:
        raise HTTPException(
            status_code=400,
            detail="Managed AI credits are not available on this deployment. Use BYOK.",
        )
    auth_ws = str(user.get("workspace_id") or user.get("active_workspace_id") or "").strip() or None
    ws = trusted_workspace_id(auth_workspace_id=auth_ws)
    wallet, entry = purchase_credits(
        ws,
        body.credits,
        user_id=uid,
        note=body.note,
        metadata={"source": "api_purchase"},
    )
    return {"wallet": wallet.to_dict(), "entry": entry.to_dict()}


@router.post("/admin/adjust")
async def admin_wallet_adjust(body: AdjustBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    uid = _user_id(user)
    auth_ws = str(user.get("workspace_id") or user.get("active_workspace_id") or "").strip() or None
    # Never trust body.workspace_id for which wallet to adjust.
    ws = trusted_workspace_id(auth_workspace_id=auth_ws)
    wallet, entry = admin_adjust(
        ws,
        body.credits,
        user_id=uid,
        note=body.note,
        metadata={"source": "admin_api"},
    )
    return {"wallet": wallet.to_dict(), "entry": entry.to_dict()}


@router.post("/admin/grant-trial")
async def admin_grant_trial(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    uid = _user_id(user)
    policy = await resolve_policy(user_id=uid)
    auth_ws = str(user.get("workspace_id") or user.get("active_workspace_id") or "").strip() or None
    ws = trusted_workspace_id(auth_workspace_id=auth_ws)
    if policy.trial_credits <= 0:
        raise HTTPException(status_code=400, detail="No trial credits configured for this plan")
    wallet, entry = grant_credits(
        ws,
        policy.trial_credits,
        user_id=uid,
        note="Admin trial grant",
        metadata={"kind": "trial", "plan_id": policy.plan_id},
    )
    store = get_ai_credit_store()
    state = store.get_wallet(ws)
    state.trial_granted = int(state.trial_granted or 0) + int(policy.trial_credits)
    store.save_wallet(state)
    return {"wallet": store.get_wallet(ws).to_dict(), "entry": entry.to_dict()}
