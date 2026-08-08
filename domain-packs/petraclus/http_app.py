"""Standalone FastAPI sidecar for the Petraclus product contract.

Run:
    cd /opt/lampp/htdocs/verlox/keprix/domain-packs/petraclus
    python3 -m uvicorn http_app:app --host 0.0.0.0 --port 3362

Fixture product API is mounted at /fixture-product.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

import tools.register  # noqa: F401
from ai_queue.degraded import degraded_queue
from connector.fixture_product_api import fixture_app, reset_fixture_state
from nodes.catalog import all_nodes
from provisioning import (
    airgap_bundle_plan,
    plan_provision,
    provision,
    rollback,
    upgrade_validate,
)
from tools import handlers
from tools.registry import registry

APP_NAME = os.getenv("PETRACLUS_KEPRIX_SIDECAR_NAME", "Keprix Petraclus Sidecar")
SHARED_TOKEN = os.getenv("PETRACLUS_SHARED_TOKEN", os.getenv("PETRACLUS_SIDECAR_TOKEN", ""))
PRODUCT_KEY = "petraclus"
CONTRACT_VERSION = "1.0.0"
PACK_VERSION = "0.1.0"
PLATFORM_MODE = os.getenv("PETRACLUS_PLATFORM_MODE", "FULL")

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
    workspace_id: str
    actor_id: str
    purpose: str = "security_assist"
    grants: list[str] = Field(default_factory=list)
    edition: str = "community"
    role: str = "analyst"


class InvokeIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None
    actor_id: str | None = None
    purpose: str = "invoke"
    session_id: str | None = None
    idempotency_key: str | None = None
    grants: list[str] = Field(default_factory=list)
    edition: str | None = None
    role: str | None = None


class JobIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str
    actor_id: str = "system"
    idempotency_key: str | None = None


class EventIn(BaseModel):
    id: str
    type: str
    source: str = "petraclus"
    subject: str | None = None
    workspace_id: str | None = None
    tenant: str | None = None
    time: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    deployment: str = "local"


class ApprovalIn(BaseModel):
    approved: bool
    actor_id: str
    input_hash: str | None = None
    workspace_id: str | None = None


class ProvisionIn(BaseModel):
    deployment: str = "local"
    workspace_id: str
    mode: str = "local_community"
    edition: str = "community"
    dry_run: bool = False
    activate: bool = False


@app.get("/health")
@app.get("/v1/products/petraclus/health")
async def health() -> dict[str, Any]:
    degraded = PLATFORM_MODE.upper() == "DEGRADED"
    return {
        "status": "ok" if not degraded else "degraded",
        "sidecar": "keprix-petraclus",
        "pack": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "mode": PLATFORM_MODE,
        "port": 3362,
        "dependencies": {
            "fixture_product_api": "mounted",
            "product_api": "ok",
            "model": "degraded" if degraded else "ok",
        },
        "degraded": degraded,
        "licence_authority": "keys.petraclus.uk",
        "at": _now(),
    }


@app.get("/v1/products/petraclus/capabilities")
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
                "version": n.get("version"),
                "status": n["status"],
                "risk": n["risk"],
                "domain": n["domain"],
                "soft_wall": n.get("soft_wall", False),
                "required_grants": list(n.get("required_grants") or []),
                "sync": n.get("sync", True),
                "edition_min": n.get("edition_min"),
                "requires_target_grant": n.get("requires_target_grant", False),
                "requires_approval": n.get("requires_approval", False),
                "live": n["status"] == "live",
            }
            for n in nodes.values()
        ],
        "tools": registry.tool_names(),
        "forbidden_nodes": [
            "shell",
            "arbitrary_http",
            "nmap_freeform",
            "exploit_run",
            "credential_read",
            "unrestricted_file_read",
            "remediation_execute",
        ],
        "loaded_at": _now(),
    }


@app.get("/v1/products/petraclus/manifest")
async def manifest() -> dict[str, Any]:
    return {
        "pack_id": "petraclus",
        "version": PACK_VERSION,
        "product_compatibility": [">=0.1.0"],
        "contract_version": CONTRACT_VERSION,
        "policy": {
            "default_deny_connector": True,
            "no_sql": True,
            "exploit_automation": False,
            "licence_authority": "keys.petraclus.uk",
        },
        "migrations": [],
        "checksum_hint": "see provision receipt",
    }


@app.post("/v1/products/petraclus/sessions")
async def create_session(body: SessionIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    row = {
        "session_id": session_id,
        "workspace_id": body.workspace_id,
        "actor_id": body.actor_id,
        "purpose": body.purpose,
        "grants": body.grants or ["node:*"],
        "edition": body.edition,
        "role": body.role,
        "created_at": _now(),
    }
    _SESSIONS[session_id] = row
    return row


@app.post("/v1/products/petraclus/invoke")
async def invoke(body: InvokeIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["invokes"] += 1
    nodes = all_nodes()
    if body.capability not in nodes and body.capability not in registry.tool_names():
        _METRICS["denials"] += 1
        raise HTTPException(status_code=404, detail="unknown_capability")
    session = _SESSIONS.get(body.session_id or "") if body.session_id else None
    payload = dict(body.input)
    payload.setdefault("workspace_id", body.workspace_id or (session or {}).get("workspace_id"))
    payload.setdefault("actor_id", body.actor_id or (session or {}).get("actor_id"))
    payload.setdefault("purpose", body.purpose or (session or {}).get("purpose") or "invoke")
    payload.setdefault("grants", body.grants or (session or {}).get("grants") or ["node:*", "mutate"])
    payload.setdefault("edition", body.edition or (session or {}).get("edition"))
    payload.setdefault("role", body.role or (session or {}).get("role"))
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


@app.post("/v1/products/petraclus/jobs")
async def start_job(body: JobIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["jobs"] += 1
    if body.idempotency_key:
        for job in _JOBS.values():
            if job.get("idempotency_key") == body.idempotency_key and job["workspace_id"] == body.workspace_id:
                return job
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    try:
        result = _dispatch(
            body.capability,
            {**body.input, "workspace_id": body.workspace_id, "grants": ["node:*", "mutate"], "purpose": "job"},
        )
        status = "completed"
    except HTTPException as exc:
        result = {"error": exc.detail}
        status = "failed"
    row = {
        "job_id": job_id,
        "status": status,
        "progress": 100 if status == "completed" else 0,
        "capability": body.capability,
        "workspace_id": body.workspace_id,
        "result": result,
        "idempotency_key": body.idempotency_key,
        "created_at": _now(),
    }
    _JOBS[job_id] = row
    return row


@app.get("/v1/products/petraclus/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job


@app.post("/v1/products/petraclus/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    if job["status"] in {"cancelled", "completed", "failed"}:
        return job
    job["status"] = "cancelled"
    return job


@app.post("/v1/products/petraclus/events")
async def ingest_event(body: EventIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    _METRICS["events"] += 1
    workspace = body.workspace_id or body.tenant or ""
    key = f"{body.source}:{body.deployment}:{body.id}"
    if key in _EVENTS_SEEN:
        return {"accepted": True, "deduped": True, "id": body.id, "workspace_id": workspace}
    _EVENTS_SEEN.add(key)
    return {"accepted": True, "deduped": False, "id": body.id, "workspace_id": workspace}


@app.get("/v1/products/petraclus/events/stream")
async def events_stream() -> dict[str, Any]:
    return {"protocol": "sse", "status": "stub", "note": "Use product outbox + ack for MVP"}


@app.post("/v1/products/petraclus/approvals/{approval_id}/decision")
async def approval_decision(
    approval_id: str,
    body: ApprovalIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_token(authorization)
    row = {
        "approval_id": approval_id,
        "workspace_id": body.workspace_id or "",
        "input_hash": body.input_hash,
        "status": "approved" if body.approved else "rejected",
        "actor_id": body.actor_id,
        "decided_at": _now(),
    }
    _APPROVALS[approval_id] = row
    handlers.register_local_approval(
        approval_id,
        workspace_id=body.workspace_id or "",
        input_hash=str(body.input_hash or ""),
        approved=bool(body.approved),
    )
    return row


@app.get("/v1/products/petraclus/metrics")
async def metrics() -> dict[str, Any]:
    return {"product": PRODUCT_KEY, **_METRICS, "sessions": len(_SESSIONS), "jobs": len(_JOBS)}


@app.post("/v1/products/petraclus/provision")
async def provision_endpoint(body: ProvisionIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    return provision(
        deployment=body.deployment,
        workspace_id=body.workspace_id,
        mode=body.mode,
        edition=body.edition,
        dry_run=body.dry_run,
        activate=body.activate,
    )


@app.get("/v1/products/petraclus/provision/plan")
async def provision_plan(
    workspace_id: str,
    deployment: str = "local",
    mode: str = "local_community",
    edition: str = "community",
) -> dict[str, Any]:
    return plan_provision(deployment=deployment, workspace_id=workspace_id, mode=mode, edition=edition)


@app.get("/v1/products/petraclus/airgap/bundle")
async def airgap_bundle() -> dict[str, Any]:
    return airgap_bundle_plan()


@app.post("/v1/products/petraclus/queue")
async def enqueue_degraded(request: Request) -> dict[str, Any]:
    body = await request.json()
    return degraded_queue.enqueue(
        workspace_id=str(body["workspace_id"]),
        actor_id=str(body.get("actor_id") or "system"),
        node_key=str(body["node_key"]),
        payload=dict(body.get("payload") or {}),
        priority=int(body.get("priority") or 50),
        dedupe_key=str(body.get("dedupe_key") or ""),
        authority_version=str(body.get("authority_version") or ""),
        grant_id=body.get("grant_id"),
        approval_id=body.get("approval_id"),
    )


@app.get("/v1/products/petraclus/queue")
async def list_queue(workspace_id: str) -> dict[str, Any]:
    return {"items": degraded_queue.list_visible(workspace_id)}


@app.post("/v1/products/petraclus/upgrade/validate")
async def upgrade_validate_endpoint(request: Request) -> dict[str, Any]:
    body = await request.json()
    return upgrade_validate(
        enable_risky_nodes=bool(body.get("enable_risky_nodes")),
        enable_node=body.get("enable_node"),
    )


@app.post("/v1/products/petraclus/rollback")
async def rollback_endpoint(request: Request) -> dict[str, Any]:
    body = await request.json()
    return rollback(to_pack_version=str(body.get("to_pack_version") or "0.0.1"))


@app.on_event("startup")
async def _startup() -> None:
    reset_fixture_state()
    degraded_queue.reset()
    handlers.clear_handler_logs()
