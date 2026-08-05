"""Tool ACL API routes (product ACL + resource-scoped grants).

Endpoints:
  GET  /api/security/acl/products
  GET  /api/security/acl/products/{product_id}
  POST /api/security/acl/check
  GET  /api/security/acl/audit
  GET  /api/security/acl/resources/catalog
  GET  /api/security/acl/resources/grants
  PUT  /api/security/acl/resources/grants
  DELETE /api/security/acl/resources/grants
  POST /api/security/acl/resources/check
  POST /api/security/acl/resources/broad
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.security.resource_scopes.enforce import check_resource_acl
from keprix.security.resource_scopes.extract import extract_resources
from keprix.security.resource_scopes.grants import ResourceGrant, get_resource_grant_store
from keprix.security.resource_scopes.registry import list_services
from keprix.security.tool_acl import ACLDecision, get_tool_acl
from keprix.security.tool_acl_audit import get_acl_audit_log

router = APIRouter(prefix="/api/security/acl", tags=["security"])

ActorType = Literal["agent", "api_token", "user", "workspace", "product"]


class ACLCheckRequest(BaseModel):
    product_id: str
    tool_name: str


class ACLCheckResponse(BaseModel):
    product_id: str
    tool_name: str
    decision: str
    allowed: bool


class ResourceGrantBody(BaseModel):
    actor_type: ActorType
    actor_id: str
    service: str
    kind: str
    resource_id: str
    actions: list[str] = Field(default_factory=lambda: ["read", "write"])


class ResourceRevokeBody(BaseModel):
    actor_type: ActorType
    actor_id: str
    service: str
    kind: str
    resource_id: str


class ResourceCheckBody(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    actor_type: ActorType | None = None
    actor_id: str | None = None


class BroadGrantBody(BaseModel):
    actor_type: ActorType
    actor_id: str
    service: str
    note: str | None = None


def _is_admin(user: dict[str, Any]) -> bool:
    role = str(user.get("role") or "").lower()
    if role in {"admin", "owner", "superadmin"}:
        return True
    roles = user.get("roles")
    if isinstance(roles, (list, tuple, set)):
        return any(str(r).lower() in {"admin", "owner", "superadmin"} for r in roles)
    return bool(user.get("is_admin"))


@router.get("/products")
async def list_products() -> dict:
    acl = get_tool_acl()
    return {
        "products": acl.list_registered_products(),
        "base_product": acl.BASE_PRODUCT,
    }


@router.get("/products/{product_id}")
async def get_product_acl(product_id: str) -> dict:
    acl = get_tool_acl()
    snap = acl.snapshot()
    if product_id != acl.BASE_PRODUCT and product_id not in snap:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found in ACL")
    config = snap.get(product_id, {"allowed_tools": ["*"], "denied_tools": []})
    return {
        "product_id": product_id,
        "is_base_product": product_id == acl.BASE_PRODUCT,
        "allowed_tools": config["allowed_tools"],
        "denied_tools": config["denied_tools"],
    }


@router.post("/check")
async def check_tool_access(body: ACLCheckRequest) -> ACLCheckResponse:
    acl = get_tool_acl()
    decision = acl.check(body.product_id, body.tool_name)
    allowed = decision == ACLDecision.ALLOWED
    return ACLCheckResponse(
        product_id=body.product_id,
        tool_name=body.tool_name,
        decision=decision.value,
        allowed=allowed,
    )


@router.get("/audit")
async def get_audit_tail(
    n: int = Query(default=50, ge=1, le=500),
    product_id: str | None = Query(default=None),
) -> dict:
    audit = get_acl_audit_log()
    entries = audit.tail(n=max(n, 500) if product_id else n)
    if product_id:
        entries = [e for e in entries if e.get("product_id") == product_id]
        entries = entries[-n:]
    return {"count": len(entries), "entries": entries}


@router.get("/resources/catalog")
async def resource_catalog() -> dict[str, Any]:
    return {"services": list_services()}


@router.get("/resources/grants")
async def list_resource_grants(
    actor_type: ActorType,
    actor_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    store = get_resource_grant_store()
    grants = [g.to_dict() for g in store.list_grants(actor_type, actor_id)]
    broad = store.list_broad_grants(actor_type, actor_id)
    return {
        "actor_type": actor_type,
        "actor_id": actor_id,
        "grants": grants,
        "broad_grants": broad,
        "note": "Empty grants for a service mean unrestricted (legacy broad access). Exact grants narrow access.",
    }


@router.put("/resources/grants")
async def upsert_resource_grant(
    body: ResourceGrantBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required to approve resources")
    grant = ResourceGrant(
        actor_type=body.actor_type,
        actor_id=body.actor_id,
        service=body.service.lower(),
        kind=body.kind,
        resource_id=body.resource_id.strip(),
        actions=list(body.actions or ["read", "write"]),
    )
    if not grant.resource_id:
        raise HTTPException(status_code=400, detail="resource_id is required")
    saved = get_resource_grant_store().upsert_grant(grant)
    return {"grant": saved.to_dict()}


@router.delete("/resources/grants")
async def revoke_resource_grant(
    body: ResourceRevokeBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    ok = get_resource_grant_store().revoke_grant(
        body.actor_type,
        body.actor_id,
        body.service,
        body.kind,
        body.resource_id,
    )
    return {"revoked": ok}


@router.post("/resources/broad")
async def record_broad_grant(
    body: BroadGrantBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark a legacy broad (unrestricted) service grant so it stays visible while narrowing."""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Admin role required")
    get_resource_grant_store().record_broad_grant(
        body.actor_type,
        body.actor_id,
        body.service,
        note=body.note,
    )
    return {"status": "recorded", "service": body.service.lower()}


@router.post("/resources/check")
async def check_resource_access(body: ResourceCheckBody) -> dict[str, Any]:
    extraction = extract_resources(body.tool_name, body.args)
    decision = check_resource_acl(
        body.tool_name,
        body.args,
        actor_type=body.actor_type,
        actor_id=body.actor_id,
    )
    return {
        "extraction": extraction.to_dict(),
        "decision": decision.to_dict(),
        "allowed": decision.allowed,
    }
