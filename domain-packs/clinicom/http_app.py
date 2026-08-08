"""Standalone FastAPI sidecar for the Clinicom HTTP contract.

Preserves contract 2.0 routes and adds additive /v1/products/clinicom/*.

Run:
    cd /opt/lampp/htdocs/verlox/keprix/domain-packs/clinicom
    uvicorn http_app:app --host 0.0.0.0 --port 3353
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

import tools.register  # noqa: F401  (registers handlers)
from tools.contract import (
    CONTRACT_VERSION,
    CORE_TOOLS,
    DEEP_TOOLS,
    PACK_VERSION,
    PRODUCT_KEY,
    capabilities_payload,
    canonical_tool_name,
    pack_manifest,
    provider_health,
)
from tools.registry import registry

APP_NAME = os.getenv("CLINICOM_KEPRIX_SIDECAR_NAME", "Keprix Clinicom Sidecar")
SHARED_TOKEN = os.getenv("CLINICOM_SHARED_TOKEN", os.getenv("CLINICOM_SIDECAR_TOKEN", ""))

app = FastAPI(title=APP_NAME, version=PACK_VERSION)

_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}
_jobs: dict[str, dict[str, Any]] = {}
_events_seen: set[str] = set()
_metrics = {
    "invokes_total": 0,
    "invokes_error": 0,
    "fallback_total": 0,
    "low_confidence_total": 0,
    "safety_escalation_total": 0,
    "latency_ms_sum": 0.0,
    "latency_ms_count": 0,
    "by_tool": {},
}


class TranscribeIn(BaseModel):
    audio: str
    mime_type: str = "audio/webm"
    language_hint: str | None = None
    context: str = "general-practice"


class TranslateIn(BaseModel):
    text: str
    source_language: str
    target_language: str
    context: str = "general-practice"


class SimplifyIn(BaseModel):
    text: str
    direction: str = "to-plain"
    target_reading_level: int = Field(default=8, ge=3, le=12)
    context: str = "general-practice"


class SpeakIn(BaseModel):
    text: str
    language: str
    voice: str = "auto"
    speed: float = 0.9


class CulturalAdaptIn(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str = "en"
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class TeachbackScoreIn(BaseModel):
    patient_response: str
    key_points: list[str] = Field(default_factory=list)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class SafetyTriageAssistIn(BaseModel):
    text: str
    safety_terms: list[str] = Field(default_factory=list)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class SessionDigestIn(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] = Field(default_factory=dict)


class SpecialtySimplifyIn(BaseModel):
    text: str
    specialty_pack_id: str = "general"
    target_reading_level: int = Field(default=8, ge=3, le=12)
    context: str = "general-practice"
    session_context: dict[str, Any] = Field(default_factory=dict)


class ConfidenceExplainIn(BaseModel):
    score: int = 0
    provider_sources: dict[str, str] = Field(default_factory=dict)
    pipeline_timing: dict[str, float] = Field(default_factory=dict)
    step_status: list[dict[str, Any]] = Field(default_factory=list)
    context: str = "general-practice"


class ProductHelpIn(BaseModel):
    question: str
    grounding_corpus: str = ""
    capabilities_summary: str = ""


class InvokeIn(BaseModel):
    capability: str
    input: dict[str, Any] = Field(default_factory=dict)
    purpose: str = "communication_assist"
    correlation_id: str | None = None
    organisation_id: str | None = None
    session_id: str | None = None
    actor_id: str | None = None
    idempotency_key: str | None = None


class SessionCreateIn(BaseModel):
    organisation_id: str | None = None
    actor_id: str | None = None
    purpose: str = "communication_assist"
    grants: list[str] = Field(default_factory=list)


class ProductEventIn(BaseModel):
    id: str
    type: str
    source: str = "clinicom"
    subject: str | None = None
    organisation_id: str | None = None
    occurred_at: str | None = None
    correlation_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    sensitivity: str = "minimised"


class ApprovalDecisionIn(BaseModel):
    decision: str
    actor_id: str | None = None
    reason: str | None = None


for _model in (
    TranscribeIn,
    TranslateIn,
    SimplifyIn,
    SpeakIn,
    CulturalAdaptIn,
    TeachbackScoreIn,
    SafetyTriageAssistIn,
    SessionDigestIn,
    SpecialtySimplifyIn,
    ConfidenceExplainIn,
    ProductHelpIn,
    InvokeIn,
    SessionCreateIn,
    ProductEventIn,
    ApprovalDecisionIn,
):
    _model.model_rebuild()


def _check_token(authorization: str | None) -> None:
    if not SHARED_TOKEN:
        return
    expected = f"Bearer {SHARED_TOKEN}"
    if authorization != expected:
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
            if "stub" in source:
                _metrics["fallback_total"] += 1
            conf = result.get("confidence")
            if isinstance(conf, (int, float)) and conf < 0.7:
                _metrics["low_confidence_total"] += 1
            if result.get("human_review_required") and tool.endswith("safety_triage_assist"):
                _metrics["safety_escalation_total"] += 1


def _dispatch(tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    registry_name = canonical_tool_name(tool)
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


def _tool_route(name: str, payload: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    _check_token(authorization)
    return _dispatch(name, payload)


@app.get("/health")
async def health() -> dict[str, Any]:
    health_info = provider_health()
    degraded = health_info["status"] != "live"
    return {
        "status": "degraded" if degraded else "ok",
        "ready": True,
        "sidecar": "keprix-clinicom",
        "pack": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "provider": health_info,
        "degraded": degraded,
    }


@app.get("/clinicom/capabilities")
async def capabilities() -> dict[str, Any]:
    return capabilities_payload()


@app.post("/clinicom/tools/transcribe")
async def transcribe(payload: TranscribeIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("transcribe", payload.model_dump(), authorization)


@app.post("/clinicom/tools/translate")
async def translate(payload: TranslateIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("translate", payload.model_dump(), authorization)


@app.post("/clinicom/tools/simplify")
async def simplify(payload: SimplifyIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("simplify", payload.model_dump(), authorization)


@app.post("/clinicom/tools/speak")
async def speak(payload: SpeakIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("speak", payload.model_dump(), authorization)


@app.post("/clinicom/tools/product_help")
async def product_help(payload: ProductHelpIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("product_help", payload.model_dump(), authorization)


# Bare deep routes (Carina / local clone style)
@app.post("/clinicom/tools/cultural_adapt")
async def cultural_adapt(payload: CulturalAdaptIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("cultural_adapt", payload.model_dump(), authorization)


@app.post("/clinicom/tools/teachback_score")
async def teachback_score(payload: TeachbackScoreIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("teachback_score", payload.model_dump(), authorization)


@app.post("/clinicom/tools/safety_triage_assist")
async def safety_triage_assist(
    payload: SafetyTriageAssistIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("safety_triage_assist", payload.model_dump(), authorization)


@app.post("/clinicom/tools/session_digest")
async def session_digest(payload: SessionDigestIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _tool_route("session_digest", payload.model_dump(), authorization)


@app.post("/clinicom/tools/specialty_simplify")
async def specialty_simplify(
    payload: SpecialtySimplifyIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("specialty_simplify", payload.model_dump(), authorization)


@app.post("/clinicom/tools/confidence_explain")
async def confidence_explain(
    payload: ConfidenceExplainIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("confidence_explain", payload.model_dump(), authorization)


# Prefixed aliases required by Clinicom provider contract 2.0
@app.post("/clinicom/tools/clinicom_cultural_adapt")
async def clinicom_cultural_adapt(
    payload: CulturalAdaptIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_cultural_adapt", payload.model_dump(), authorization)


@app.post("/clinicom/tools/clinicom_teachback_score")
async def clinicom_teachback_score(
    payload: TeachbackScoreIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_teachback_score", payload.model_dump(), authorization)


@app.post("/clinicom/tools/clinicom_safety_triage_assist")
async def clinicom_safety_triage_assist(
    payload: SafetyTriageAssistIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_safety_triage_assist", payload.model_dump(), authorization)


@app.post("/clinicom/tools/clinicom_session_digest")
async def clinicom_session_digest(
    payload: SessionDigestIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_session_digest", payload.model_dump(), authorization)


@app.post("/clinicom/tools/clinicom_specialty_simplify")
async def clinicom_specialty_simplify(
    payload: SpecialtySimplifyIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_specialty_simplify", payload.model_dump(), authorization)


@app.post("/clinicom/tools/clinicom_confidence_explain")
async def clinicom_confidence_explain(
    payload: ConfidenceExplainIn, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    return _tool_route("clinicom_confidence_explain", payload.model_dump(), authorization)


# --- Additive shared product contract (/v1/products/clinicom) ---

PRODUCT_PREFIX = f"/v1/products/{PRODUCT_KEY}"


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
    capability = payload.capability.strip()
    registry_name = canonical_tool_name(capability)
    if registry_name not in set(registry.tool_names()):
        raise HTTPException(status_code=404, detail="Unknown or unregistered capability")
    result = _dispatch(registry_name, payload.input)
    return {
        "capability": registry_name,
        "correlation_id": payload.correlation_id or str(uuid.uuid4()),
        "organisation_id": payload.organisation_id,
        "session_id": payload.session_id,
        "actor_id": payload.actor_id,
        "purpose": payload.purpose,
        "result": result,
        "proposal_only": True,
        "ehr_write": False,
        "acceptance_required": True,
    }


@app.post(f"{PRODUCT_PREFIX}/jobs")
async def product_jobs(payload: InvokeIn, authorization: str | None = Header(default=None)) -> JSONResponse:
    _check_token(authorization)
    job_id = str(uuid.uuid4())
    # Clinicom tools are sync; async jobs wrap the same handler for contract completeness.
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
            if payload.type in {"retention.deleted", "session.deleted", "consent.revoked"}:
                # Purge transient session/job references for opaque ids only
                subject = payload.subject or ""
                for sid in list(_sessions):
                    if subject and subject in json.dumps(_sessions[sid]):
                        _sessions.pop(sid, None)
    return {
        "accepted": True,
        "duplicate": duplicate,
        "id": payload.id,
        "type": payload.type,
        "purged_transient": payload.type in {"retention.deleted", "session.deleted", "consent.revoked"},
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
    return {
        "approval_id": approval_id,
        "decision": decision,
        "actor_id": payload.actor_id,
        "reason": payload.reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "note": "Product remains authoritative for durable acceptance; sidecar records assistive decision only.",
    }


@app.get(f"{PRODUCT_PREFIX}/metrics")
async def product_metrics(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_token(authorization)
    with _lock:
        count = max(1, _metrics["latency_ms_count"])
        snapshot = {
            **_metrics,
            "availability": 1.0 - (_metrics["invokes_error"] / max(1, _metrics["invokes_total"])),
            "latency_ms_avg": _metrics["latency_ms_sum"] / count,
            "provider": provider_health(),
            "raw_patient_content_logged": False,
        }
    return snapshot


@app.get(f"{PRODUCT_PREFIX}/metrics/prometheus")
async def product_metrics_prometheus(authorization: str | None = Header(default=None)) -> PlainTextResponse:
    _check_token(authorization)
    data = await product_metrics(authorization)
    lines = [
        f"clinicom_sidecar_invokes_total {data['invokes_total']}",
        f"clinicom_sidecar_invokes_error {data['invokes_error']}",
        f"clinicom_sidecar_fallback_total {data['fallback_total']}",
        f"clinicom_sidecar_low_confidence_total {data['low_confidence_total']}",
        f"clinicom_sidecar_safety_escalation_total {data['safety_escalation_total']}",
        f"clinicom_sidecar_latency_ms_avg {data['latency_ms_avg']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation = request.headers.get("x-correlation-id") or secrets.token_hex(8)
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = correlation
    response.headers["X-Keprix-Product"] = PRODUCT_KEY
    response.headers["X-Keprix-Pack-Version"] = PACK_VERSION
    return response
