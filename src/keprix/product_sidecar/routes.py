"""Northbound product sidecar HTTP API: /v1/products/{product_key}."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.product_sidecar.auth import get_token_service, grants_for_product
from keprix.product_sidecar.invoke import InvokeError, invoke_node
from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.state import (
    get_approval_store,
    get_circuit,
    get_event_store,
    get_job_store,
    get_kill_switches,
    get_memory_store,
    get_shadow_store,
    input_hash,
)
from keprix.product_sidecar.types import RequestContext

router = APIRouter(prefix="/v1/products", tags=["product-sidecar"])

SUPPORTED = frozenset({"carina", "aiva"})


class SessionCreate(BaseModel):
    workspace_id: str
    actor_id: str = "operator"
    purpose: str = "session"
    grants: list[str] = Field(default_factory=list)


class InvokeBody(BaseModel):
    node: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None
    shadow: bool = False
    idempotency_key: str | None = None


class JobCreate(BaseModel):
    node: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str
    idempotency_key: str = ""


class EventEnvelope(BaseModel):
    id: str
    type: str
    source: str
    subject: str | None = None
    workspace_id: str | None = None
    deployment: str = "local"
    data: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    approved: bool
    workspace_id: str
    actor_id: str
    input_hash: str | None = None


class TokenExchangeBody(BaseModel):
    product: str
    workspace_id: str
    actor_id: str
    purpose: str = "invoke"
    admin: bool = False
    session_id: str = ""
    ttl_seconds: int = 300


def _product_or_404(product_key: str) -> None:
    if product_key not in SUPPORTED:
        raise HTTPException(status_code=404, detail="unknown product_key")


def _correlation(request: Request, header_value: str | None) -> str:
    return (
        (header_value or "").strip()
        or getattr(request.state, "request_id", None)
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )


def _auth_ctx(
    request: Request,
    product_key: str,
    authorization: str | None,
    correlation_id: str,
) -> RequestContext:
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": "missing bearer", "code": "denied"})
    try:
        return get_token_service().authenticate_request(
            authorization=authorization,
            product=product_key,
            correlation_id=correlation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"error": str(exc), "code": str(exc)}) from exc


@router.get("/{product_key}/health")
async def product_health(product_key: str) -> dict[str, Any]:
    _product_or_404(product_key)
    pack = get_product_pack_registry().get(product_key)
    if pack is None:
        raise HTTPException(status_code=404, detail="pack missing")
    kills = get_kill_switches()
    return {
        "status": "ok" if pack.enabled else "disabled",
        "product": product_key,
        "pack_version": pack.version,
        "contract_version": pack.contract_version,
        "enabled": pack.enabled,
        "node_counts": pack.node_status_counts(),
        "circuit": get_circuit().state(),
        "force_carina": kills.force_carina,
        "outbound_kill": kills.outbound_kill,
        "shared_token_compat": "deprecated",
        "wrapper_of": pack.wrapper_of,
    }


@router.get("/{product_key}/capabilities")
async def product_capabilities(product_key: str) -> dict[str, Any]:
    _product_or_404(product_key)
    pack = get_product_pack_registry().require(product_key)
    nodes = []
    for node in pack.nodes.values():
        nodes.append(
            {
                "key": node.key,
                "title": node.title,
                "domain": node.domain,
                "risk": node.risk.value,
                "status": node.status.value,
                "soft_wall": node.soft_wall,
                "sync": node.sync,
                "required_grants": list(node.required_grants),
                "guidance": node.operator_guidance,
                "aiva_sku_ok": node.aiva_sku_ok,
                "carina_admin_only": node.carina_admin_only,
            }
        )
    return {
        "product": product_key,
        "contract_version": pack.contract_version,
        "pack_version": pack.version,
        "enabled": pack.enabled,
        "shared_token_compat": "deprecated",
        "nodes": sorted(nodes, key=lambda n: n["key"]),
    }


@router.get("/{product_key}/manifest")
async def product_manifest(product_key: str) -> dict[str, Any]:
    _product_or_404(product_key)
    pack = get_product_pack_registry().require(product_key)
    return {
        "product_key": pack.product_key,
        "pack_id": pack.pack_id,
        "version": pack.version,
        "title": pack.title,
        "contract_version": pack.contract_version,
        "checksum": pack.checksum,
        "wrapper_of": pack.wrapper_of,
        "connector": pack.connector,
        "policies": pack.policies,
        "memory_namespace": pack.memory_namespace,
        "playbooks": list(pack.playbooks),
        "events": list(pack.events),
        "nodes": sorted(pack.nodes.keys()),
    }


@router.post("/{product_key}/sessions")
async def create_session(
    product_key: str,
    body: SessionCreate,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    corr = _correlation(request, x_correlation_id)
    _auth_ctx(request, product_key, authorization, corr)
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    grants = set(body.grants) or set(grants_for_product(product_key))
    token, claims = get_token_service().mint(
        product=product_key,
        workspace_id=body.workspace_id,
        actor_id=body.actor_id,
        grants=grants,
        purpose=body.purpose,
        session_id=session_id,
    )
    return {
        "session_id": session_id,
        "access_token": token,
        "expires_at": claims.exp,
        "correlation_id": corr,
    }


@router.post("/{product_key}/token/exchange")
async def token_exchange(product_key: str, body: TokenExchangeBody, request: Request) -> dict[str, Any]:
    """Bootstrap shared token -> short-lived product token."""
    _product_or_404(product_key)
    auth = request.headers.get("Authorization", "")
    bootstrap_ctx = _auth_ctx(request, product_key, auth, _correlation(request, None))
    if bootstrap_ctx.token_mode not in {"shared_compat", "exchange"}:
        raise HTTPException(status_code=401, detail="bootstrap required")
    grants = grants_for_product(product_key, admin=body.admin)
    token, claims = get_token_service().mint(
        product=product_key,
        workspace_id=body.workspace_id,
        actor_id=body.actor_id,
        grants=grants,
        purpose=body.purpose,
        session_id=body.session_id,
        ttl_seconds=body.ttl_seconds,
    )
    return {"access_token": token, "expires_at": claims.exp, "grants": sorted(grants)}


@router.post("/{product_key}/invoke")
async def invoke(
    product_key: str,
    body: InvokeBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    corr = _correlation(request, x_correlation_id)
    if not corr:
        raise HTTPException(status_code=422, detail="correlation id required")
    ctx = _auth_ctx(request, product_key, authorization, corr)
    if body.workspace_id:
        if ctx.workspace_id and ctx.workspace_id != body.workspace_id and "*" not in ctx.grants:
            raise HTTPException(
                status_code=403,
                detail={"error": "cross_tenant", "code": "denied"},
            )
        ctx.workspace_id = body.workspace_id
    ctx.shadow = bool(body.shadow)
    if body.idempotency_key:
        body.input = {**body.input, "idempotency_key": body.idempotency_key}
    try:
        return await invoke_node(ctx, node_key=body.node, input_payload=body.input)
    except InvokeError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.as_dict()) from exc


@router.post("/{product_key}/jobs")
async def create_job(
    product_key: str,
    body: JobCreate,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    corr = _correlation(request, x_correlation_id)
    ctx = _auth_ctx(request, product_key, authorization, corr)
    ctx.workspace_id = body.workspace_id
    result = await invoke_node(ctx, node_key=body.node, input_payload={**body.input, "idempotency_key": body.idempotency_key})
    return result


@router.get("/{product_key}/jobs/{job_id}")
async def get_job(
    product_key: str,
    job_id: str,
    workspace_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    ctx = _auth_ctx(request, product_key, authorization, _correlation(request, None))
    if ctx.workspace_id and ctx.workspace_id != workspace_id and "*" not in ctx.grants:
        raise HTTPException(status_code=403, detail={"code": "denied"})
    job = get_job_store().get(job_id, workspace_id=workspace_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job": job}


@router.post("/{product_key}/jobs/{job_id}/cancel")
async def cancel_job(
    product_key: str,
    job_id: str,
    request: Request,
    workspace_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    _auth_ctx(request, product_key, authorization, _correlation(request, None))
    job = get_job_store().cancel(job_id, workspace_id=workspace_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    # Second cancel is idempotent
    job2 = get_job_store().cancel(job_id, workspace_id=workspace_id)
    return {"job": job2, "idempotent": True}


@router.post("/{product_key}/events")
async def ingest_event(
    product_key: str,
    body: EventEnvelope,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    _auth_ctx(request, product_key, authorization, _correlation(request, None))
    envelope = body.model_dump()
    envelope["product"] = product_key
    return get_event_store().ingest(envelope)


@router.post("/{product_key}/approvals/{approval_id}/decision")
async def approval_decision(
    product_key: str,
    approval_id: str,
    body: ApprovalDecision,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _product_or_404(product_key)
    _auth_ctx(request, product_key, authorization, _correlation(request, None))
    try:
        row = get_approval_store().decide(
            approval_id,
            workspace_id=body.workspace_id,
            approved=body.approved,
            actor_id=body.actor_id,
            input_hash=body.input_hash,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": str(exc), "code": "denied"}) from exc
    return {"approval": row}


@router.get("/{product_key}/metrics")
async def metrics(product_key: str) -> dict[str, Any]:
    _product_or_404(product_key)
    pack = get_product_pack_registry().require(product_key)
    kills = get_kill_switches()
    return {
        "product": product_key,
        "enabled": pack.enabled,
        "node_counts": pack.node_status_counts(),
        "circuit": get_circuit().state(),
        "shadow_global": kills.shadow_enabled_global,
        "primary_workspaces": sorted(kills.primary_workspaces),
        "force_carina": kills.force_carina,
    }


@router.get("/{product_key}/shadow/comparisons")
async def shadow_comparisons(
    product_key: str,
    workspace_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    limit: int = 50,
) -> dict[str, Any]:
    _product_or_404(product_key)
    ctx = _auth_ctx(request, product_key, authorization, _correlation(request, None))
    if ctx.workspace_id and ctx.workspace_id != workspace_id and "*" not in ctx.grants:
        raise HTTPException(status_code=403, detail={"code": "denied"})
    return {
        "workspace_id": workspace_id,
        "comparisons": get_shadow_store().list_for_workspace(workspace_id, limit=limit),
    }


@router.post("/{product_key}/admin/kill")
async def admin_kill(
    product_key: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Operator kill switches (pack / outbound / force_carina / node)."""
    _product_or_404(product_key)
    ctx = _auth_ctx(request, product_key, authorization, _correlation(request, None))
    if "ops:read" not in ctx.grants and "*" not in ctx.grants:
        raise HTTPException(status_code=403, detail={"code": "denied"})
    body = await request.json()
    action = str(body.get("action") or "")
    kills = get_kill_switches()
    registry = get_product_pack_registry()
    if action == "disable_pack":
        registry.disable(product_key)
    elif action == "enable_pack":
        registry.enable(product_key)
    elif action == "force_carina":
        kills.force_carina = bool(body.get("value", True))
    elif action == "outbound_kill":
        kills.outbound_kill = bool(body.get("value", True))
    elif action == "disable_node":
        registry.disable_node(product_key, str(body.get("node") or ""))
    elif action == "enable_node":
        registry.enable_node(product_key, str(body.get("node") or ""))
    elif action == "set_primary_workspace":
        kills.primary_workspaces.add(str(body.get("workspace_id") or ""))
    elif action == "retention_delete":
        removed = get_memory_store().delete_workspace(
            product=product_key, workspace_id=str(body.get("workspace_id") or "")
        )
        return {"ok": True, "removed": removed}
    else:
        raise HTTPException(status_code=422, detail="unknown action")
    return {"ok": True, "action": action}


# Export helpers used by legacy bridge shim
def map_legacy_agent_run_to_invoke_payload(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "node": "agent.run",
        "workspace_id": body.get("workspace_id"),
        "input": body,
    }


__all__ = ["router", "input_hash", "map_legacy_agent_run_to_invoke_payload"]
