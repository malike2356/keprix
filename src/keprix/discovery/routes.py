"""HTTP routes for discovery jobs and adapters (/api/crm/discovery, /api/crm/jobs/*)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.crm.roles import require_cap
from keprix.crm.store import get_crm_store
from keprix.discovery.adapters.social import scrape_refusal_payload
from keprix.discovery.runner import get_discovery_runner

router = APIRouter(prefix="/api/crm", tags=["crm-discovery"])


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


class DiscoveryRunBody(BaseModel):
    adapter: str
    query: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    domain_pack: str = "generic"
    limits: dict[str, Any] = Field(default_factory=dict)
    list_name: str | None = None
    auto_materialize: bool = False
    run_now: bool = True
    materialize: bool | None = None
    approval_id: str | None = None
    force: bool = False
    icp_id: str | None = None
    icp_version: int | None = None


class JobActionBody(BaseModel):
    approval_id: str | None = None
    force: bool = False
    list_name: str | None = None
    materialize: bool | None = None


@router.get("/discovery/adapters")
async def list_discovery_adapters(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.discovery import bootstrap_discovery, get_discovery_registry

    bootstrap_discovery()
    reg = get_discovery_registry()
    return {
        "items": reg.list_manifests(),
        "health": reg.health_all(),
        "count": len(reg.list_names()),
        "workspace_id": _workspace(workspace_id, x_workspace_id, user),
    }


@router.get("/discovery/packs")
async def list_discovery_packs(
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.discovery.packs import list_packs

    items = list_packs()
    return {"items": items, "count": len(items)}


@router.post("/discovery/run")
async def run_discovery(
    body: DiscoveryRunBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    adapter = (body.adapter or "").strip().lower()

    # Honest scrape refusal for social platforms.
    if adapter in {"instagram_scrape", "facebook_scrape", "tiktok_scrape", "linkedin_scrape", "social_scrape"}:
        return {
            **scrape_refusal_payload(adapter),
            "correlation_id": _corr(request),
        }
    if "scrape" in adapter and adapter not in {"social_csv_export"}:
        return {
            **scrape_refusal_payload(adapter),
            "correlation_id": _corr(request),
        }

    from keprix.discovery import bootstrap_discovery

    bootstrap_discovery()
    runner = get_discovery_runner()
    params = dict(body.params or {})
    if body.icp_id:
        params["icp_id"] = body.icp_id
    if body.icp_version is not None:
        params["icp_version"] = body.icp_version
    job = runner.create_job(
        ws,
        adapter,
        query=body.query,
        params=params,
        domain_pack=body.domain_pack,
        limits=body.limits,
        list_name=body.list_name,
        auto_materialize=body.auto_materialize,
        actor_type="user",
        actor_id=_uid(user),
        icp_id=body.icp_id,
        icp_version=body.icp_version,
    )
    result: dict[str, Any] = {
        "job": job,
        "deep_links": {"job": f"/crm/jobs/{job['id']}"},
        "correlation_id": _corr(request),
    }
    if body.run_now:
        run = runner.run_job(
            ws,
            job["id"],
            materialize=body.materialize if body.materialize is not None else body.auto_materialize,
            approval_id=body.approval_id,
            force=body.force,
        )
        result.update(run)
        if run.get("deep_links"):
            result["deep_links"] = run["deep_links"]
    return result


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    ws = _workspace(workspace_id, x_workspace_id, user)
    store = get_crm_store()
    discovery = store.get_discovery_job(ws, job_id)
    if discovery:
        from keprix.discovery import bootstrap_discovery, get_discovery_registry

        bootstrap_discovery()
        adapter_health = None
        try:
            adapter_health = get_discovery_registry().health(str(discovery.get("adapter") or "")).to_dict()
        except Exception:  # noqa: BLE001
            adapter_health = None
        return {
            "kind": "discovery",
            "job": discovery,
            "adapter_health": adapter_health,
            "deep_links": {
                "job": f"/crm/jobs/{job_id}",
                "list": f"/crm/lists/{discovery['list_id']}" if discovery.get("list_id") else None,
                "discover": "/crm/discover",
            },
        }
    enrich = store.get_enrichment_job(ws, job_id)
    if enrich:
        return {"kind": "enrichment", "job": enrich, "deep_links": {"job": f"/crm/jobs/{job_id}"}}
    raise HTTPException(status_code=404, detail={"error_code": "job_not_found"})


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    runner = get_discovery_runner()
    job = runner.request_cancel(ws, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"error_code": "job_not_found"})
    return {"job": job, "correlation_id": _corr(request)}


@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: str,
    body: JobActionBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    runner = get_discovery_runner()
    try:
        result = runner.run_job(
            ws,
            job_id,
            materialize=body.materialize,
            approval_id=body.approval_id,
            force=body.force,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "job_not_found"}) from None
    result["correlation_id"] = _corr(request)
    return result


@router.post("/jobs/{job_id}/materialize")
async def materialize_job(
    job_id: str,
    body: JobActionBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    ws = _workspace(workspace_id, x_workspace_id, user)
    runner = get_discovery_runner()
    try:
        result = runner.materialize_job(
            ws,
            job_id,
            approval_id=body.approval_id,
            force=body.force,
            list_name=body.list_name,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "job_not_found"}) from None
    result["correlation_id"] = _corr(request)
    return result


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    body: JobActionBody,
    request: Request,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    ws = _workspace(workspace_id, x_workspace_id, user)
    runner = get_discovery_runner()
    try:
        result = runner.retry_dead_letter(
            ws,
            job_id,
            materialize=body.materialize,
            approval_id=body.approval_id,
            force=body.force,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail={"error_code": "job_not_found"}) from None
    result["correlation_id"] = _corr(request)
    return result
