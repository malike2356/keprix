"""Tenant admin API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.tenancy.store import TenantConflictError, TenantNotFoundError, get_tenant_store

router = APIRouter(prefix="/api/tenants", tags=["tenancy"])


class CreateTenantBody(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=200)
    owner_user_id: str | None = None


class UpdateTenantBody(BaseModel):
    slug: str | None = None
    display_name: str | None = None
    status: str | None = None
    owner_user_id: str | None = None


class MembershipBody(BaseModel):
    user_id: str = Field(min_length=1)
    role: str = "member"


@router.get("")
async def list_tenants(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_tenant_store()
    tenants = store.list_tenants()
    return {"tenants": [t.to_dict() for t in tenants], "count": len(tenants)}


@router.post("")
async def create_tenant(body: CreateTenantBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    store = get_tenant_store()
    owner = body.owner_user_id or str(admin.get("id") or admin.get("username") or "admin")
    try:
        tenant = store.create(
            slug=body.slug,
            display_name=body.display_name,
            owner_user_id=owner,
        )
    except TenantConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tenant": tenant.to_dict()}


@router.get("/me")
async def my_tenants(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = get_tenant_store()
    user_id = str(user.get("id") or user.get("username") or "")
    memberships = store.list_memberships(user_id=user_id)
    tenants = []
    for m in memberships:
        tenant = store.get(m.tenant_id)
        if tenant:
            tenants.append({**tenant.to_dict(), "role": m.role})
    if not tenants:
        local = store.ensure_default(owner_user_id=user_id or "local")
        tenants.append({**local.to_dict(), "role": "owner"})
    return {"tenants": tenants, "count": len(tenants)}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    tenant = get_tenant_store().resolve_ref(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"tenant": tenant.to_dict()}


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    body: UpdateTenantBody,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    store = get_tenant_store()
    tenant = store.resolve_ref(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        updated = store.update(tenant.id, **body.model_dump(exclude_none=True))
    except TenantConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tenant": updated.to_dict()}


@router.post("/{tenant_id}/memberships")
async def add_membership(
    tenant_id: str,
    body: MembershipBody,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    store = get_tenant_store()
    tenant = store.resolve_ref(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        membership = store.add_membership(tenant.id, body.user_id, role=body.role)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"membership": membership.to_dict()}
