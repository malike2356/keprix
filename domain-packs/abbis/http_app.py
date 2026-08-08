"""Standalone FastAPI sidecar for the ABBIS product contract.

Run:
    cd /opt/lampp/htdocs/verlox/keprix/domain-packs/abbis
    python3 -m uvicorn http_app:app --host 0.0.0.0 --port 3360

Also mounts fixture product API under the same process for local development:
    /api/keprix/v1/*
"""

from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

import tools.register  # noqa: F401
from channels import ingest_channel_message, rag_retrieve, voice_workflow_contract
from connector.fixture_product_api import fixture_app, reset_fixture_state
from nodes.catalog import all_nodes
from provisioning import plan_provision, provision, rollback, upgrade_validate
from ai_queue.degraded import degraded_queue
from tools.registry import registry

APP_NAME = os.getenv("ABBIS_KEPRIX_SIDECAR_NAME", "Keprix ABBIS Sidecar")
SHARED_TOKEN = os.getenv("ABBIS_SHARED_TOKEN", os.getenv("ABBIS_SIDECAR_TOKEN", ""))
PRODUCT_KEY = "abbis"
CONTRACT_VERSION = "1.0.0"
PACK_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=PACK_VERSION)
app.mount("/fixture-product", fixture_app)

_SESSIONS: dict[str, dict[str, Any]] = {}
_JOBS: dict[str, dict[str, Any]] = {}
_EVENTS_SEEN: set[str] = set()
_APPROVALS: dict[str, dict[str, Any]] = {}
_METRICS = {"invokes": 0, "denials": 0, "jobs": 0, "events": 0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_token(authorization: str | None) -> None:
    if not SHARED_TOKEN:
        return
    expected = f"Bearer {SHARED_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid sidecar token")


def _dispatch(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = registry.dispatch(tool, payload)
    data = json.loads(raw)
    if data.get("status") == "error" or data.get("error"):
        raise HTTPException(status_code=400, detail=data.get("error") or data)
    return data


class SessionIn(BaseModel):
    tenant_id: str
    actor_id: str
    stakeholder: str = "S07"
    purpose: str = "field_assist"
    accessories: list[str] = Field(default_factory=list)
    grants: list[str] = Field(default_factory=list)
    locale: str = "en"
    channel: str = "web"


class InvokeIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None
    actor_id: str | None = None
    stakeholder: str | None = None
    purpose: str = "invoke"
    session_id: str | None = None
    idempotency_key: str | None = None
    accessories: list[str] = Field(default_factory=list)
    grants: list[str] = Field(default_factory=list)


class JobIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str
    actor_id: str = "system"
    idempotency_key: str | None = None


class EventIn(BaseModel):
    id: str
    type: str
    source: str = "abbis"
    subject: str | None = None
    tenant: str
    time: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    deployment: str = "local"


class ApprovalIn(BaseModel):
    approved: bool
    actor_id: str
    input_hash: str | None = None
    workspace_id: str | None = None


class ChannelIn(BaseModel):
    channel: str
    delivery_id: str
    external_id: str
    text: str
    intent: str = "read"
    confirmed: bool = False
    links: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ProvisionIn(BaseModel):
    deployment: str = "local"
    tenant_id: str
    stakeholder: str = "S07"
    accessories: list[str] = Field(default_factory=list)
    dry_run: bool = False
    activate: bool = False


for _model in (
    SessionIn,
    InvokeIn,
    JobIn,
    EventIn,
    ApprovalIn,
    ChannelIn,
    ProvisionIn,
):
    _model.model_rebuild()


@app.get("/health")
@app.get("/v1/products/abbis/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "sidecar": "keprix-abbis",
        "pack": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "mode": os.getenv("ABBIS_PLATFORM_MODE", "FULL"),
        "dependencies": {
            "calculators": "ok",
            "fixture_product_api": "mounted",
            "channels": "ok",
        },
        "degraded": False,
        "operator": "ghanaian_operating_company",
        "association": "BDAG",
        "at": _now(),
    }


@app.get("/v1/products/abbis/capabilities")
async def capabilities() -> dict[str, Any]:
    nodes = all_nodes()
    return {
        "contract_version": CONTRACT_VERSION,
        "product": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "profile": "keprix",
        "nodes": [
            {
                "key": n["key"],
                "title": n["title"],
                "status": n["status"],
                "risk": n["risk"],
                "domain": n["domain"],
                "soft_wall": n.get("soft_wall", False),
                "national": n.get("national", False),
                "live": n["status"] == "live",
            }
            for n in nodes.values()
        ],
        "tools": registry.tool_names(),
        "loaded_at": _now(),
    }


@app.get("/v1/products/abbis/manifest")
async def manifest() -> dict[str, Any]:
    return {
        "pack_id": "abbis",
        "version": PACK_VERSION,
        "product_compatibility": [">=0.1.0"],
        "contract_version": CONTRACT_VERSION,
        "mesh_version": "abbis-mesh@1.0.0",
        "policy": {
            "default_deny_connector": True,
            "no_sql": True,
            "localisation_via": "abbis",
            "operator": "ghanaian_operating_company",
            "association": "BDAG",
        },
        "migrations": [],
        "checksum_hint": "see provision receipt",
    }


@app.post("/v1/products/abbis/sessions")
async def create_session(body: SessionIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    row = {
        "session_id": session_id,
        "tenant_id": body.tenant_id,
        "actor_id": body.actor_id,
        "stakeholder": body.stakeholder,
        "purpose": body.purpose,
        "accessories": body.accessories,
        "grants": body.grants or ["*"],
        "locale": body.locale,
        "channel": body.channel,
        "created_at": _now(),
    }
    _SESSIONS[session_id] = row
    return row


@app.post("/v1/products/abbis/invoke")
async def invoke(body: InvokeIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["invokes"] += 1
    nodes = all_nodes()
    if body.capability not in nodes and body.capability not in registry.tool_names():
        _METRICS["denials"] += 1
        raise HTTPException(status_code=404, detail="unknown_capability")
    session = _SESSIONS.get(body.session_id or "") if body.session_id else None
    payload = dict(body.input)
    payload.setdefault("tenant_id", body.tenant_id or (session or {}).get("tenant_id"))
    payload.setdefault("actor_id", body.actor_id or (session or {}).get("actor_id"))
    payload.setdefault("stakeholder", body.stakeholder or (session or {}).get("stakeholder"))
    payload.setdefault("purpose", body.purpose)
    payload.setdefault("accessories", body.accessories or (session or {}).get("accessories") or [])
    payload.setdefault("grants", body.grants or (session or {}).get("grants") or ["*"])
    try:
        result = _dispatch(body.capability, payload)
    except HTTPException:
        _METRICS["denials"] += 1
        raise
    return {
        "capability": body.capability,
        "result": result,
        "idempotency_key": body.idempotency_key,
        "at": _now(),
    }


@app.post("/v1/products/abbis/jobs")
async def start_job(body: JobIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["jobs"] += 1
    if body.idempotency_key:
        for job in _JOBS.values():
            if job.get("idempotency_key") == body.idempotency_key and job["tenant_id"] == body.tenant_id:
                return job
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    try:
        result = _dispatch(body.capability, {**body.input, "tenant_id": body.tenant_id, "grants": ["*"]})
        status = "completed"
    except HTTPException as exc:
        result = {"error": exc.detail}
        status = "failed"
    row = {
        "job_id": job_id,
        "status": status,
        "progress": 100 if status == "completed" else 0,
        "capability": body.capability,
        "tenant_id": body.tenant_id,
        "result": result,
        "idempotency_key": body.idempotency_key,
        "created_at": _now(),
    }
    _JOBS[job_id] = row
    return row


@app.get("/v1/products/abbis/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job


@app.post("/v1/products/abbis/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    if job["status"] in {"cancelled", "completed", "failed"}:
        return job
    job["status"] = "cancelled"
    return job


@app.post("/v1/products/abbis/events")
async def ingest_event(body: EventIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["events"] += 1
    key = f"{body.source}:{body.deployment}:{body.id}"
    if key in _EVENTS_SEEN:
        return {"accepted": True, "deduped": True, "id": body.id}
    _EVENTS_SEEN.add(key)
    return {"accepted": True, "deduped": False, "id": body.id}


@app.get("/v1/products/abbis/events/stream")
async def events_stream() -> dict[str, Any]:
    return {"protocol": "sse", "status": "stub", "note": "Use product outbox + ack for MVP"}


@app.post("/v1/products/abbis/approvals/{approval_id}/decision")
async def approval_decision(
    approval_id: str,
    body: ApprovalIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_token(authorization)
    row = _APPROVALS.get(approval_id) or {
        "approval_id": approval_id,
        "workspace_id": body.workspace_id or "",
        "input_hash": body.input_hash,
        "status": "pending",
    }
    row["status"] = "approved" if body.approved else "rejected"
    row["actor_id"] = body.actor_id
    row["decided_at"] = _now()
    _APPROVALS[approval_id] = row
    return row


@app.get("/v1/products/abbis/metrics")
async def metrics() -> dict[str, Any]:
    return {"product": PRODUCT_KEY, **_METRICS, "sessions": len(_SESSIONS), "jobs": len(_JOBS)}


@app.post("/v1/products/abbis/channels/ingest")
async def channel_ingest(body: ChannelIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    return ingest_channel_message(
        channel=body.channel,
        delivery_id=body.delivery_id,
        external_id=body.external_id,
        text=body.text,
        links=body.links,
        intent=body.intent,
        confirmed=body.confirmed,
    )


@app.get("/v1/products/abbis/workflows/{workflow_id}")
async def workflow(workflow_id: str) -> dict[str, Any]:
    try:
        return voice_workflow_contract(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown_workflow") from exc


@app.post("/v1/products/abbis/rag/search")
async def rag_search(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    body = await request.json()
    hits = rag_retrieve(
        query=str(body.get("query") or ""),
        tenant_id=str(body.get("tenant_id") or ""),
        accessory=str(body.get("accessory") or "field.operations"),
        corpora=list(body.get("corpora") or []),
    )
    return {"hits": hits}


@app.post("/v1/products/abbis/provision")
async def provision_endpoint(body: ProvisionIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    return provision(
        deployment=body.deployment,
        tenant_id=body.tenant_id,
        stakeholder=body.stakeholder,
        accessories=body.accessories or None,
        dry_run=body.dry_run,
        activate=body.activate,
    )


@app.get("/v1/products/abbis/provision/plan")
async def provision_plan(
    tenant_id: str,
    stakeholder: str = "S07",
    deployment: str = "local",
) -> dict[str, Any]:
    return plan_provision(deployment=deployment, tenant_id=tenant_id, stakeholder=stakeholder)


@app.post("/v1/products/abbis/queue")
async def enqueue_degraded(request: Request) -> dict[str, Any]:
    body = await request.json()
    return degraded_queue.enqueue(
        tenant_id=str(body["tenant_id"]),
        actor_id=str(body.get("actor_id") or "system"),
        node_key=str(body["node_key"]),
        payload=dict(body.get("payload") or {}),
        priority=int(body.get("priority") or 50),
        dedupe_key=str(body.get("dedupe_key") or ""),
        authority_version=str(body.get("authority_version") or ""),
        record_version=body.get("record_version"),
        approval_id=body.get("approval_id"),
        low_bandwidth=bool(body.get("low_bandwidth")),
    )


@app.get("/v1/products/abbis/queue/{tenant_id}")
async def list_queue(tenant_id: str) -> dict[str, Any]:
    return {"items": degraded_queue.list_visible(tenant_id)}


@app.post("/v1/products/abbis/queue/{item_id}/replay")
async def replay_queue(item_id: str, request: Request) -> dict[str, Any]:
    body = await request.json()
    return degraded_queue.replay(
        item_id,
        current_authority_version=str(body.get("current_authority_version") or ""),
        current_record_version=body.get("current_record_version"),
        approval_still_valid=bool(body.get("approval_still_valid", True)),
        permissions_ok=bool(body.get("permissions_ok", True)),
    )


@app.post("/v1/products/abbis/upgrade/validate")
async def upgrade_validate_endpoint(request: Request) -> dict[str, Any]:
    body = await request.json()
    return upgrade_validate(
        enable_accessory=body.get("enable_accessory"),
        enable_national=bool(body.get("enable_national")),
    )


@app.post("/v1/products/abbis/rollback")
async def rollback_endpoint(request: Request) -> dict[str, Any]:
    body = await request.json()
    return rollback(to_pack_version=str(body.get("to_pack_version") or "0.0.1"))


# Convenience tool routes (Clinicom-style)
@app.post("/abbis/tools/{tool_name}")
async def tool_route(tool_name: str, request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    payload = await request.json()
    return _dispatch(tool_name, payload)


@app.on_event("startup")
async def _startup() -> None:
    reset_fixture_state()
    degraded_queue.reset()
