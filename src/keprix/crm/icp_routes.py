"""HTTP routes for saved ICP definitions (/api/crm/icp*)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.crm import icp as icp_mod
from keprix.crm.roles import require_cap
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm", tags=["crm-icp"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(
    workspace_id: str | None,
    x_workspace_id: str | None,
    user: dict[str, Any],
) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


def _corr(request: Request) -> str:
    return request.headers.get("X-Correlation-Id") or str(uuid.uuid4())


class IcpCreateBody(BaseModel):
    name: str
    pack: str = "generic"
    include_rules: list[Any] = Field(default_factory=list)
    exclude_rules: list[Any] = Field(default_factory=list)
    geography: list[Any] = Field(default_factory=list)
    size_band: str | None = None
    keywords: list[Any] = Field(default_factory=list)
    sic_codes: list[Any] = Field(default_factory=list)
    notes: str | None = None


class IcpReviseBody(BaseModel):
    include_rules: list[Any] | None = None
    exclude_rules: list[Any] | None = None
    geography: list[Any] | None = None
    size_band: str | None = None
    keywords: list[Any] | None = None
    sic_codes: list[Any] | None = None
    notes: str | None = None
    pack: str | None = None


class IcpActivateBody(BaseModel):
    force: bool = False
    approval_id: str | None = None


@router.get("/icp")
async def list_icp(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    name: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    items = icp_mod.list_icps(store, ws, name=name)
    active = icp_mod.get_active_icp(store, ws)
    return {
        "items": items,
        "count": len(items),
        "active": active,
        "workspace_id": ws,
        "deep_links": {"ui": "/crm/icp"},
    }


@router.post("/icp", status_code=201)
async def create_icp(
    body: IcpCreateBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    try:
        row = icp_mod.create_icp(
            store,
            ws,
            name=body.name,
            pack=body.pack,
            include_rules=body.include_rules,
            exclude_rules=body.exclude_rules,
            geography=body.geography,
            size_band=body.size_band,
            keywords=body.keywords,
            sic_codes=body.sic_codes,
            notes=body.notes,
            actor_type="user",
            actor_id=_uid(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc)}) from exc
    return {"icp": row, "correlation_id": _corr(request), "deep_links": {"ui": "/crm/icp"}}


@router.get("/icp/{icp_id}")
async def get_icp(
    icp_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    row = icp_mod.get_icp(get_crm_store(), ws, icp_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "icp_not_found"})
    return {"icp": row, "workspace_id": ws}


@router.post("/icp/{icp_id}/revise", status_code=201)
async def revise_icp(
    icp_id: str,
    body: IcpReviseBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    try:
        row = icp_mod.revise_icp(
            store,
            ws,
            icp_id,
            include_rules=body.include_rules,
            exclude_rules=body.exclude_rules,
            geography=body.geography,
            size_band=body.size_band,
            keywords=body.keywords,
            sic_codes=body.sic_codes,
            notes=body.notes,
            pack=body.pack,
            actor_type="user",
            actor_id=_uid(user),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc)}) from exc
    return {"icp": row, "correlation_id": _corr(request)}


@router.get("/icp/{left_id}/diff/{right_id}")
async def diff_icp(
    left_id: str,
    right_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    left = icp_mod.get_icp(store, ws, left_id)
    right = icp_mod.get_icp(store, ws, right_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail={"error_code": "icp_not_found"})
    return icp_mod.diff_icp_versions(left, right)


@router.post("/icp/{icp_id}/activate")
async def activate_icp(
    icp_id: str,
    body: IcpActivateBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    try:
        result = icp_mod.activate_icp(
            store,
            ws,
            icp_id,
            actor_id=_uid(user),
            force=body.force,
            approval_id=body.approval_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"error_code": str(exc)}) from exc
    result["correlation_id"] = _corr(request)
    result["deep_links"] = {"ui": "/crm/icp", "approvals": "/crm"}
    return result
