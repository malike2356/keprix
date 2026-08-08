"""Standalone FastAPI sidecar for the Fleetz product contract.

Run:
    cd /opt/lampp/htdocs/verlox/keprix/domain-packs/fleetz
    uvicorn http_app:app --host 0.0.0.0 --port 3354
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

import tools.register  # noqa: F401
from tools.contract import (
    CONTRACT_VERSION,
    PACK_VERSION,
    PRODUCT_KEY,
    capabilities_payload,
    canonical_tool_name,
    pack_manifest,
    provider_health,
)
from tools.registry import registry
from tools.safety import assert_no_vehicle_command

APP_NAME = os.getenv("FLEETZ_KEPRIX_SIDECAR_NAME", "Keprix Fleetz Sidecar")
SHARED_TOKEN = os.getenv("FLEETZ_SHARED_TOKEN", os.getenv("FLEETZ_SIDECAR_TOKEN", ""))

app = FastAPI(title=APP_NAME, version=PACK_VERSION)

_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}
_jobs: dict[str, dict[str, Any]] = {}
_events_seen: set[str] = set()
_approvals: dict[str, dict[str, Any]] = {}
_kill_switch = {"enabled": False, "reason": None}
_metrics = {
    "invokes_total": 0,
    "invokes_error": 0,
    "fallback_total": 0,
    "stale_refusals": 0,
    "command_denials": 0,
    "latency_ms_sum": 0.0,
    "latency_ms_count": 0,
    "by_tool": {},
}

PRODUCT_PREFIX = f"/v1/products/{PRODUCT_KEY}"


class InvokeIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    purpose: str = "fleet_ops"
    correlation_id: str | None = None
    fleet_id: str | None = None
    organisation_id: str | None = None
    session_id: str | None = None
    actor_id: str | None = None
    idempotency_key: str | None = None


class SessionCreateIn(BaseModel):
    fleet_id: str | None = None
    organisation_id: str | None = None
    actor_id: str | None = None
    purpose: str = "fleet_ops"
    grants: list[str] = Field(default_factory=list)


class ProductEventIn(BaseModel):
    id: str
    type: str
    source: str = "fleetz"
    subject: str | None = None
    fleet_id: str | None = None
    organisation_id: str | None = None
    occurred_at: str | None = None
    correlation_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    sensitivity: str = "minimised"


class ApprovalDecisionIn(BaseModel):
    decision: str
    actor_id: str | None = None
    reason: str | None = None


class ToolIn(BaseModel):
    fleet_id: str | None = None
    vehicle_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


for _model in (InvokeIn, SessionCreateIn, ProductEventIn, ApprovalDecisionIn, ToolIn):
    _model.model_rebuild()


def _check_token(authorization: str | None) -> None:
    if not SHARED_TOKEN:
        return
    if authorization != f"Bearer {SHARED_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid sidecar token")


def _record_metrics(tool: str, latency_ms: float, *, error: bool, result: dict[str, Any] | None) -> None:
    with _lock:
        _metrics["invokes_total"] += 1
        if error:
            _metrics["invokes_error"] += 1
        _metrics["latency_ms_sum"] += latency_ms
        _metrics["latency_ms_count"] += 1
        by_tool = _metrics["by_tool"].setdefault(tool, {"count": 0, "errors": 0})
        by_tool["count"] += 1
        if error:
            by_tool["errors"] += 1
        if result:
            source = str(result.get("source") or "")
            if "fixture" in source or "stub" in source:
                _metrics["fallback_total"] += 1
            if result.get("reason") == "stale_telemetry" or result.get("status") == "refused":
                _metrics["stale_refusals"] += 1
            if result.get("error") == "vehicle_command_disabled":
                _metrics["command_denials"] += 1


def _dispatch(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    if _kill_switch["enabled"]:
        raise HTTPException(status_code=503, detail=f"kill_switch:{_kill_switch.get('reason') or 'enabled'}")
    started = time.perf_counter()
    registry_name = canonical_tool_name(tool)
    denied = assert_no_vehicle_command(registry_name)
    if denied:
        _record_metrics(registry_name, 0.0, error=True, result=denied)
        raise HTTPException(status_code=403, detail=denied)
    error = False
    data: dict[str, Any] | None = None
    try:
        raw = registry.dispatch(registry_name, payload)
        data = json.loads(raw)
        if data.get("status") == "error" or data.get("error"):
            error = True
            raise HTTPException(status_code=400, detail=data.get("error") or "Tool dispatch failed")
        return data
    finally:
        _record_metrics(registry_name, (time.perf_counter() - started) * 1000.0, error=error, result=data)


@app.get("/health")
async def health() -> dict[str, Any]:
    health_info = provider_health()
    degraded = health_info["status"] != "live"
    return {
        "status": "degraded" if degraded else "ok",
        "ready": not _kill_switch["enabled"],
        "sidecar": "keprix-fleetz",
        "pack": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "provider": health_info,
        "degraded": degraded,
        "kill_switch": _kill_switch,
        "vehicle_commands": "disabled",
    }


@app.get("/fleetz/capabilities")
async def fleetz_capabilities() -> dict[str, Any]:
    return capabilities_payload()


@app.post("/fleetz/tools/{tool_name}")
async def fleetz_tool(
    tool_name: str,
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_token(authorization)
    return _dispatch(tool_name, payload)


@app.get(f"{PRODUCT_PREFIX}/health")
async def product_health() -> dict[str, Any]:
    return await health()


@app.get(f"{PRODUCT_PREFIX}/capabilities")
async def product_capabilities() -> dict[str, Any]:
    return capabilities_payload()


@app.get(f"{PRODUCT_PREFIX}/manifest")
async def product_manifest() -> dict[str, Any]:
    return pack_manifest()


@app.post(f"{PRODUCT_PREFIX}/sessions")
async def product_sessions(payload: SessionCreateIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    session_id = str(uuid.uuid4())
    record = {
        "session_id": session_id,
        "fleet_id": payload.fleet_id,
        "organisation_id": payload.organisation_id,
        "actor_id": payload.actor_id,
        "purpose": payload.purpose,
        "grants": payload.grants,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _sessions[session_id] = record
    return record


@app.post(f"{PRODUCT_PREFIX}/invoke")
async def product_invoke(payload: InvokeIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    registry_name = canonical_tool_name(payload.capability)
    if registry_name not in set(registry.tool_names()):
        raise HTTPException(status_code=404, detail="Unknown or unregistered capability")
    inp = dict(payload.input)
    if payload.fleet_id and "fleet_id" not in inp:
        inp["fleet_id"] = payload.fleet_id
    if payload.idempotency_key and "idempotency_key" not in inp:
        inp["idempotency_key"] = payload.idempotency_key
    result = _dispatch(registry_name, inp)
    return {
        "capability": registry_name,
        "correlation_id": payload.correlation_id or str(uuid.uuid4()),
        "fleet_id": payload.fleet_id or inp.get("fleet_id"),
        "session_id": payload.session_id,
        "actor_id": payload.actor_id,
        "purpose": payload.purpose,
        "result": result,
        "proposal_only": True,
        "vehicle_command": False,
        "acceptance_required": True,
    }


@app.post(f"{PRODUCT_PREFIX}/jobs")
async def product_jobs(payload: InvokeIn, authorization: str | None = Header(default=None)) -> JSONResponse:
    _check_token(authorization)
    job_id = str(uuid.uuid4())
    try:
        result = await product_invoke(payload, authorization)
        status = "succeeded"
        error = None
    except HTTPException as exc:
        result = None
        status = "failed"
        error = exc.detail
    record = {
        "job_id": job_id,
        "status": status,
        "progress": 100 if status == "succeeded" else 0,
        "result": result,
        "error": error,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cancel_requested": False,
    }
    with _lock:
        _jobs[job_id] = record
    return JSONResponse(status_code=202, content=record, headers={"Location": f"{PRODUCT_PREFIX}/jobs/{job_id}"})


@app.get(f"{PRODUCT_PREFIX}/jobs/{{job_id}}")
async def product_job_status(job_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@app.post(f"{PRODUCT_PREFIX}/jobs/{{job_id}}/cancel")
async def product_job_cancel(job_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Unknown job")
        job["cancel_requested"] = True
        if job["status"] not in {"succeeded", "failed", "cancelled"}:
            job["status"] = "cancelled"
    return job


@app.post(f"{PRODUCT_PREFIX}/events")
async def product_events(payload: ProductEventIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    event_key = f"{payload.source}:{payload.id}"
    with _lock:
        duplicate = event_key in _events_seen
        if not duplicate:
            _events_seen.add(event_key)
    # Coalesce hint for storms: clients may batch; never one model call per raw point
    return {
        "accepted": True,
        "duplicate": duplicate,
        "id": payload.id,
        "type": payload.type,
        "fleet_id": payload.fleet_id,
        "coalesce_recommended": payload.type.startswith("telemetry."),
        "command_topic": False,
    }


@app.post(f"{PRODUCT_PREFIX}/approvals/{{approval_id}}/decision")
async def product_approval_decision(
    approval_id: str,
    payload: ApprovalDecisionIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_token(authorization)
    decision = payload.decision.lower().strip()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve or reject")
    record = {
        "approval_id": approval_id,
        "decision": decision,
        "actor_id": payload.actor_id,
        "reason": payload.reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "note": "Fleetz product remains authoritative for durable apply.",
    }
    with _lock:
        _approvals[approval_id] = record
    return record


@app.get(f"{PRODUCT_PREFIX}/metrics")
async def product_metrics(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    with _lock:
        count = max(1, _metrics["latency_ms_count"])
        return {
            **_metrics,
            "availability": 1.0 - (_metrics["invokes_error"] / max(1, _metrics["invokes_total"])),
            "latency_ms_avg": _metrics["latency_ms_sum"] / count,
            "provider": provider_health(),
            "precise_routes_logged": False,
            "raw_telemetry_logged": False,
            "service_tokens_logged": False,
            "kill_switch": _kill_switch,
        }


@app.get(f"{PRODUCT_PREFIX}/metrics/prometheus")
async def product_metrics_prometheus(authorization: str | None = Header(default=None)) -> PlainTextResponse:
    _check_token(authorization)
    data = await product_metrics(authorization)
    lines = [
        f"fleetz_sidecar_invokes_total {data['invokes_total']}",
        f"fleetz_sidecar_invokes_error {data['invokes_error']}",
        f"fleetz_sidecar_fallback_total {data['fallback_total']}",
        f"fleetz_sidecar_stale_refusals {data['stale_refusals']}",
        f"fleetz_sidecar_command_denials {data['command_denials']}",
        f"fleetz_sidecar_latency_ms_avg {data['latency_ms_avg']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.post(f"{PRODUCT_PREFIX}/ops/kill-switch")
async def kill_switch(body: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    enabled = bool(body.get("enabled"))
    with _lock:
        _kill_switch["enabled"] = enabled
        _kill_switch["reason"] = body.get("reason")
    return {"kill_switch": _kill_switch}


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation = request.headers.get("x-correlation-id") or secrets.token_hex(8)
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = correlation
    response.headers["X-Keprix-Product"] = PRODUCT_KEY
    response.headers["X-Keprix-Pack-Version"] = PACK_VERSION
    return response
