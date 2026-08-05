"""Quota API routes.

Endpoints:
  GET  /api/admin/quotas                        - list all product usages
  GET  /api/admin/quotas/{product_id}           - usage for one product
  POST /api/admin/quotas/{product_id}/reset     - manual period reset
  GET  /api/admin/quotas/scheduler              - fairness scheduler stats
  GET  /api/quotas/status                       - actor remaining quota (auth user)
  GET  /api/admin/quotas/actors/denials         - recent quota denials
  PUT  /api/admin/quotas/actors/{scope_type}/{scope_id} - override limits
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.quotas.actor_enforcer import remaining_headers
from keprix.quotas.actor_limits import normalize_limits, status_for_scope
from keprix.quotas.actor_store import get_actor_quota_store
from keprix.quotas.policy import deployment_tier
from keprix.quotas.quota_config import get_quota_config
from keprix.quotas.runtime import get_fairness_scheduler, get_quota_store
from keprix.quotas.scope import make_scope

router = APIRouter(tags=["quotas"])

_store = get_quota_store()
_scheduler = get_fairness_scheduler()


class ActorOverrideBody(BaseModel):
    limits: dict[str, Any] | None = Field(
        default=None,
        description="Normalized limits object, or null to clear override",
    )


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _is_admin(user: dict[str, Any]) -> bool:
    role = str(user.get("role") or "").lower()
    if role in {"admin", "owner", "superadmin"}:
        return True
    roles = user.get("roles")
    if isinstance(roles, (list, tuple, set)):
        return any(str(r).lower() in {"admin", "owner", "superadmin"} for r in roles)
    return bool(user.get("is_admin"))


@router.get("/api/quotas/status")
async def user_quota_status(
    response: Response,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Expose remaining actor quota for the authenticated user and workspace."""
    from keprix.quotas.actor_limits import ActorQuotaDecision

    uid = _user_id(user)
    workspace_id = str(user.get("workspace_id") or user.get("active_workspace_id") or "default")
    user_status = status_for_scope(make_scope("user", uid))
    workspace_status = status_for_scope(make_scope("workspace", workspace_id))
    decision = ActorQuotaDecision(
        allowed=True,
        period=str(user_status.get("period") or "month"),
        remaining=user_status.get("remaining"),  # type: ignore[arg-type]
    )
    for header, value in remaining_headers(decision).items():
        response.headers[header] = value
    return {
        "deployment_tier": deployment_tier(),
        "note": "Actor quotas are separate from managed AI billing credits.",
        "user": user_status,
        "workspace": workspace_status,
    }


@router.get("/api/admin/quotas")
async def list_quotas() -> dict:
    config = get_quota_config()
    products = config.list_products()
    usages = []
    for pid in products:
        usage = await _store.get_usage(pid)
        usages.append(usage.to_dict())
    return {
        "products": products,
        "usages": usages,
        "deployment_tier": deployment_tier(),
        "note": "Product quotas are separate from managed AI billing credits.",
    }


@router.get("/api/admin/quotas/scheduler")
async def get_scheduler_stats() -> dict:
    return _scheduler.stats()


@router.get("/api/admin/quotas/actors/denials")
async def list_actor_denials(
    limit: int = 50,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    return {"items": get_actor_quota_store().list_denials(limit=limit)}


@router.get("/api/admin/quotas/actors/{scope_type}/{scope_id}")
async def get_actor_quota(
    scope_type: str,
    scope_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    if scope_type not in {"workspace", "agent", "api_token", "user", "product"}:
        raise HTTPException(status_code=400, detail="Invalid scope_type")
    scope = make_scope(scope_type, scope_id)  # type: ignore[arg-type]
    status = status_for_scope(scope)
    status["override"] = get_actor_quota_store().get_override(scope)
    return status


@router.put("/api/admin/quotas/actors/{scope_type}/{scope_id}")
async def set_actor_quota_override(
    scope_type: str,
    scope_id: str,
    body: ActorOverrideBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    if scope_type not in {"workspace", "agent", "api_token", "user", "product"}:
        raise HTTPException(status_code=400, detail="Invalid scope_type")
    try:
        normalized = normalize_limits(body.limits) if body.limits is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    scope = make_scope(scope_type, scope_id)  # type: ignore[arg-type]
    saved = get_actor_quota_store().set_override(scope, normalized)
    return {"scope": scope.to_dict(), "limits": saved}


@router.get("/api/admin/quotas/{product_id}")
async def get_quota(product_id: str) -> dict:
    config = get_quota_config()
    quota = await config.get_quota(product_id)
    usage = await _store.get_usage(product_id)
    return {
        "product_id": product_id,
        "period": quota.period,
        "burst_allowance": quota.burst_allowance,
        "usage": usage.to_dict(),
    }


@router.post("/api/admin/quotas/{product_id}/reset")
async def reset_quota(product_id: str) -> dict:
    await _store.reset_period(product_id)
    return {"product_id": product_id, "status": "reset"}
