"""Universal Sidecar HTTP routes under /sidecar/v1 (KUS-02)."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from keprix.universal_sidecar.contract import (
    CONTRACT_NAME,
    CONTRACT_VERSION,
    SIDECAR_API_PREFIX,
    architecture_summary,
)
from keprix.universal_sidecar.events import (
    get_approval_store,
    get_event_service,
    get_job_service,
)
from keprix.universal_sidecar.manifest.validate import export_redacted
from keprix.universal_sidecar.memory import FileIngest, get_memory_service
from keprix.universal_sidecar.nodes import NodeError, catalog_for_project, invoke_safe_node
from keprix.universal_sidecar.pairing import WorkloadToken, get_pairing_store
from keprix.universal_sidecar.registry import get_project_registry

router = APIRouter(prefix=SIDECAR_API_PREFIX, tags=["universal-sidecar"])

_shutting_down = False


def set_shutting_down(value: bool) -> None:
    global _shutting_down
    _shutting_down = bool(value)


def _correlation(request: Request, x_correlation_id: str | None = None) -> str:
    return (
        (x_correlation_id or "").strip()
        or request.headers.get("x-correlation-id")
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )


def _error(
    status: int,
    *,
    error: str,
    code: str,
    correlation_id: str = "",
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": error,
            "code": code,
            "correlation_id": correlation_id or "",
        },
    )


def _raise_error(
    status: int,
    *,
    error: str,
    code: str,
    correlation_id: str = "",
) -> None:
    raise HTTPException(
        status_code=status,
        detail={"error": error, "code": code, "correlation_id": correlation_id or ""},
    )


def _dev_open() -> bool:
    return os.environ.get("KEPRIX_SIDECAR_DEV_OPEN", "").strip() == "1"


def _parse_bearer(authorization: str | None) -> WorkloadToken:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ValueError("denied")
    return get_pairing_store().parse(authorization.split(" ", 1)[1].strip())


def _auth_project(
    authorization: str | None,
    *,
    project_key: str,
    require_grant: str | None = None,
    correlation_id: str = "",
) -> WorkloadToken:
    if _dev_open() and not authorization:
        try:
            grants = get_project_registry().grants_for(project_key)
        except KeyError:
            grants = frozenset({"discover", "jobs", "events", "approvals", "metrics"})
        now = int(time.time())
        return WorkloadToken(
            jti="dev-open",
            iss="keprix",
            aud="keprix-universal-sidecar",
            sub=f"project:{project_key}",
            project=project_key,
            deployment="local",
            environment="local",
            tenant_id="",
            actor_id="dev",
            grants=frozenset(grants) | frozenset({"*"}),
            purpose="dev_open",
            iat=now,
            nbf=now,
            exp=now + 3600,
        )
    try:
        return get_pairing_store().authenticate(
            authorization,
            project_key=project_key,
            require_grant=require_grant,
        )
    except ValueError as exc:
        _raise_error(401, error=str(exc), code=str(exc), correlation_id=correlation_id)
        raise  # pragma: no cover


def _auth_admin(authorization: str | None, *, correlation_id: str = "") -> WorkloadToken | None:
    if _dev_open() and not authorization:
        return None
    try:
        token = _parse_bearer(authorization)
    except ValueError as exc:
        _raise_error(401, error=str(exc), code="denied", correlation_id=correlation_id)
        raise  # pragma: no cover
    if "administration" not in token.grants and "*" not in token.grants:
        _raise_error(
            403,
            error="administration grant required",
            code="denied",
            correlation_id=correlation_id,
        )
    return token


def _require_project(project_key: str, *, correlation_id: str = "") -> dict[str, Any]:
    row = get_project_registry().get(project_key)
    if not row:
        _raise_error(404, error="unknown project_key", code="not_found", correlation_id=correlation_id)
    return row  # type: ignore[return-value]


class SessionCreate(BaseModel):
    tenant_id: str = ""
    actor_id: str = "operator"
    purpose: str = "session"
    grants: list[str] = Field(default_factory=list)
    ttl_seconds: int = 300


class PairCodeBody(BaseModel):
    deployment: str = "local"
    environment: str = "local"
    base_url: str = ""
    callback_urls: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    ttl_seconds: int = 300


class PairApproveBody(BaseModel):
    code: str
    admin_actor: str = "admin"


class TokenExchangeBody(BaseModel):
    purpose: str = "invoke"
    grants: list[str] = Field(default_factory=list)
    tenant_id: str = ""
    actor_id: str = "workload"
    ttl_seconds: int = 300


class InvokeBody(BaseModel):
    node: str
    input: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None
    simulate: bool = False


class JobCreate(BaseModel):
    node: str
    input: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = ""
    run_inline: bool = True


class EventEnvelope(BaseModel):
    id: str
    type: str
    source: str
    subject: str | None = None
    tenant: str | None = None
    tenant_id: str | None = None
    deployment: str = "local"
    environment: str = "local"
    correlation: str | None = None
    correlation_id: str | None = None
    sensitivity: str = "internal"
    data: dict[str, Any] = Field(default_factory=dict)
    specversion: str = "1.0"
    time: float | str | None = None


class ApprovalDecision(BaseModel):
    approved: bool
    actor_id: str = "operator"
    input_hash: str | None = None


class KillBody(BaseModel):
    switch: str = "project"
    value: bool = True
    node: str | None = None


class ApplyManifestBody(BaseModel):
    manifest: dict[str, Any]
    confirm_risky: bool = False


class MemoryWriteBody(BaseModel):
    content: str
    source: str = "api"
    namespace: str = "ephemeral"
    tenant_id: str = ""
    purpose: str = "context"
    ttl_seconds: int = 3600


class MemoryDeleteBody(BaseModel):
    tenant_id: str = ""
    namespace: str | None = None


class FileIngestBody(BaseModel):
    content_type: str = "text/plain"
    data_base64: str
    filename: str = "upload"


@router.get("/health")
async def root_health() -> dict[str, Any]:
    return {"status": "ok", "contract": CONTRACT_NAME, "version": CONTRACT_VERSION}


@router.get("/ready")
async def root_ready() -> JSONResponse:
    if _shutting_down:
        return _error(503, error="shutting down", code="not_ready")
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "shutting_down": False, "config_valid": True},
    )


@router.get("/version")
async def root_version() -> dict[str, Any]:
    return {
        "contract": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "api_prefix": SIDECAR_API_PREFIX,
    }


@router.get("/projects")
async def list_projects(
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    _auth_admin(authorization, correlation_id=corr)
    return {"projects": get_project_registry().list_projects()}


@router.get("/architecture")
async def architecture() -> dict[str, Any]:
    return architecture_summary()


@router.get("/openapi.json")
async def openapi_profile() -> dict[str, Any]:
    """Minimal profile-aware OpenAPI describing enabled universal routes."""
    paths: dict[str, Any] = {
        f"{SIDECAR_API_PREFIX}/health": {"get": {"summary": "Process liveness"}},
        f"{SIDECAR_API_PREFIX}/ready": {"get": {"summary": "Readiness"}},
        f"{SIDECAR_API_PREFIX}/version": {"get": {"summary": "Contract version"}},
        f"{SIDECAR_API_PREFIX}/projects": {"get": {"summary": "List projects (admin)"}},
        f"{SIDECAR_API_PREFIX}/architecture": {"get": {"summary": "Architecture summary"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/health": {"get": {"summary": "Project health"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/ready": {"get": {"summary": "Project ready"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/capabilities": {"get": {"summary": "Capabilities"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/manifest": {"get": {"summary": "Manifest digest"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/sessions": {"post": {"summary": "Mint session"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/pair/code": {"post": {"summary": "Create pairing code"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/pair/approve": {"post": {"summary": "Approve pairing"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/token/exchange": {"post": {"summary": "Token exchange"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/invoke": {"post": {"summary": "Invoke safe node"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/jobs": {"post": {"summary": "Create job"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/jobs/{{job_id}}": {"get": {"summary": "Job status"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/jobs/{{job_id}}/cancel": {"post": {"summary": "Cancel job"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/jobs/{{job_id}}/events": {"get": {"summary": "Job SSE"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/events": {"post": {"summary": "Ingest CloudEvent"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/events/stream": {"get": {"summary": "SSE events"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/approvals/{{id}}/decision": {
            "post": {"summary": "Approval decision"}
        },
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/metrics": {"get": {"summary": "Metrics"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/admin/kill": {"post": {"summary": "Kill switches"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/memory/search": {"get": {"summary": "Memory search"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/memory/write": {"post": {"summary": "Memory write"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/memory/delete": {"post": {"summary": "Memory delete"}},
        f"{SIDECAR_API_PREFIX}/projects/{{project_key}}/files/ingest": {"post": {"summary": "File ingest"}},
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": CONTRACT_NAME,
            "version": CONTRACT_VERSION,
            "description": "Keprix Universal Sidecar profile (sidecar_only / mounted)",
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
            }
        },
        "security": [{"bearerAuth": []}],
    }


@router.get("/projects/{project_key}/health")
async def project_health(project_key: str) -> dict[str, Any]:
    row = get_project_registry().get(project_key)
    if not row:
        _raise_error(404, error="unknown project_key", code="not_found")
    killed = get_project_registry().is_killed(project_key)
    return {
        "status": "ok" if row.get("enabled") and not killed else "degraded",
        "project_key": project_key,
        "enabled": row.get("enabled"),
        "killed": killed,
        "digest": row.get("digest"),
        "contract_version": CONTRACT_VERSION,
    }


@router.get("/projects/{project_key}/ready")
async def project_ready(project_key: str) -> JSONResponse:
    if _shutting_down:
        return _error(503, error="shutting down", code="not_ready")
    row = get_project_registry().get(project_key)
    if not row:
        return _error(503, error="project not applied", code="not_ready")
    if not row.get("enabled") or get_project_registry().is_killed(project_key):
        return _error(503, error="project disabled or killed", code="not_ready")
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "project_key": project_key,
            "digest": row.get("digest"),
            "shutting_down": False,
        },
    )


@router.get("/projects/{project_key}/capabilities")
async def project_capabilities(project_key: str) -> dict[str, Any]:
    _require_project(project_key)
    return {
        "project_key": project_key,
        "contract_version": CONTRACT_VERSION,
        "nodes": catalog_for_project(project_key),
    }


@router.get("/projects/{project_key}/manifest")
async def project_manifest(project_key: str) -> dict[str, Any]:
    row = _require_project(project_key)
    redacted = export_redacted(row["manifest"])
    return {
        "project_key": project_key,
        "digest": row.get("digest"),
        "manifest": {
            "project_key": redacted.get("project_key"),
            "display_name": redacted.get("display_name"),
            "deployment": redacted.get("deployment"),
            "environment": redacted.get("environment"),
            "contract_version": redacted.get("contract_version"),
            "capabilities": redacted.get("capabilities"),
            "memory": redacted.get("memory"),
            "feature_flags": redacted.get("feature_flags"),
            "_redacted": True,
            "_digest": redacted.get("_digest"),
        },
    }


@router.post("/projects/{project_key}/sessions")
async def create_session(
    project_key: str,
    body: SessionCreate,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    row = _require_project(project_key, correlation_id=corr)
    token_ctx = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    grants = set(body.grants) or set(row.get("grants") or set())
    if "*" not in token_ctx.grants:
        grants &= set(token_ctx.grants)
    signed, claims = get_pairing_store().mint_token(
        project=project_key,
        deployment=str(row["manifest"].get("deployment") or "local"),
        environment=str(row["manifest"].get("environment") or "local"),
        grants=grants,
        purpose=body.purpose,
        tenant_id=body.tenant_id,
        actor_id=body.actor_id,
        ttl_seconds=body.ttl_seconds,
    )
    return {
        "session_id": f"sess_{claims.jti[:12]}",
        "access_token": signed,
        "expires_at": claims.exp,
        "grants": sorted(claims.grants),
        "correlation_id": corr,
    }


@router.post("/projects/{project_key}/pair/code")
async def pair_code(
    project_key: str,
    body: PairCodeBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    row = _require_project(project_key, correlation_id=corr)
    if authorization or not _dev_open():
        _auth_project(authorization, project_key=project_key, correlation_id=corr)
    manifest = row["manifest"]
    scopes = body.scopes or [
        "discover",
        "jobs",
        "events",
        "invoke:summarise",
        "memory:ephemeral/read",
        "memory:ephemeral/write",
        "approvals",
        "metrics",
    ]
    try:
        result = get_pairing_store().create_code(
            project_key=project_key,
            deployment=body.deployment or str(manifest.get("deployment") or "local"),
            environment=body.environment or str(manifest.get("environment") or "local"),
            base_url=body.base_url or str(manifest.get("base_url") or ""),
            callback_urls=body.callback_urls or list(manifest.get("callback_urls") or []),
            requested_scopes=scopes,
            ttl_seconds=body.ttl_seconds,
        )
    except PermissionError as exc:
        return _error(403, error=str(exc), code="denied", correlation_id=corr)
    return {**result, "correlation_id": corr}


@router.post("/projects/{project_key}/pair/approve")
async def pair_approve(
    project_key: str,
    body: PairApproveBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    _require_project(project_key, correlation_id=corr)
    if not _dev_open():
        _auth_admin(authorization, correlation_id=corr)
    try:
        result = get_pairing_store().approve_code(body.code, admin_actor=body.admin_actor)
    except KeyError:
        return _error(404, error="unknown_code", code="not_found", correlation_id=corr)
    except ValueError as exc:
        return _error(409, error=str(exc), code=str(exc), correlation_id=corr)
    token = get_pairing_store().parse(result["access_token"])
    if token.project != project_key:
        return _error(403, error="wrong project", code="denied", correlation_id=corr)
    return {**result, "correlation_id": corr}


@router.post("/projects/{project_key}/token/exchange")
async def token_exchange(
    project_key: str,
    body: TokenExchangeBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    _require_project(project_key, correlation_id=corr)
    workload = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    grants = set(body.grants) or set(workload.grants)
    if "*" not in workload.grants:
        grants &= set(workload.grants)
    signed, claims = get_pairing_store().mint_token(
        project=project_key,
        deployment=workload.deployment,
        environment=workload.environment,
        grants=grants,
        purpose=body.purpose,
        tenant_id=body.tenant_id or workload.tenant_id,
        actor_id=body.actor_id or workload.actor_id,
        ttl_seconds=body.ttl_seconds,
    )
    return {
        "access_token": signed,
        "expires_at": claims.exp,
        "grants": sorted(claims.grants),
        "correlation_id": corr,
    }


@router.post("/projects/{project_key}/invoke")
async def invoke(
    project_key: str,
    body: InvokeBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = (
        (x_correlation_id or "").strip()
        or request.headers.get("x-correlation-id")
        or request.headers.get("x-request-id")
        or ""
    )
    if not corr:
        return _error(422, error="X-Correlation-Id or x-request-id required", code="missing_correlation")
    _require_project(project_key, correlation_id=corr)
    token = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    tenant = body.tenant_id if body.tenant_id is not None else token.tenant_id
    try:
        return await invoke_safe_node(
            project_key=project_key,
            node_key=body.node,
            input_payload=body.input,
            grants=token.grants,
            tenant_id=tenant,
            actor_id=token.actor_id,
            correlation_id=corr,
            simulate=body.simulate,
        )
    except NodeError as exc:
        return _error(exc.http_status, error=exc.message, code=exc.code, correlation_id=corr)
    except KeyError:
        return _error(404, error="unknown project_key", code="not_found", correlation_id=corr)


@router.post("/projects/{project_key}/jobs")
async def create_job(
    project_key: str,
    body: JobCreate,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    if not idempotency_key:
        return _error(
            422,
            error="Idempotency-Key header required",
            code="missing_idempotency",
            correlation_id=corr,
        )
    _require_project(project_key, correlation_id=corr)
    token = _auth_project(
        authorization,
        project_key=project_key,
        require_grant="jobs",
        correlation_id=corr,
    )
    try:
        job = get_job_service().create(
            project_key=project_key,
            node_key=body.node,
            input_payload=body.input,
            idempotency_key=idempotency_key,
            tenant_id=body.tenant_id or token.tenant_id,
            actor_id=token.actor_id,
            correlation_id=corr,
        )
    except PermissionError as exc:
        return _error(429, error=str(exc), code=str(exc), correlation_id=corr)
    except ValueError as exc:
        return _error(409, error=str(exc), code=str(exc), correlation_id=corr)

    if body.run_inline and body.node in {"summarise", "project.read"} and job.get("status") == "queued":
        held: dict[str, Any] = {}
        try:
            held["result"] = await invoke_safe_node(
                project_key=project_key,
                node_key=body.node,
                input_payload=body.input,
                grants=token.grants,
                tenant_id=job.get("tenant_id") or "",
                actor_id=token.actor_id,
                correlation_id=corr,
            )
        except Exception as exc:
            held["error"] = exc

        def runner(_snapshot: dict[str, Any]) -> dict[str, Any]:
            if "error" in held:
                raise held["error"]
            return held["result"]

        job = get_job_service().run_inline(job["job_id"], runner)

    get_event_service().emit_outbound(
        project_key=project_key,
        event_type="keprix.job.updated",
        data={"job_id": job["job_id"], "status": job.get("status")},
        tenant_id=job.get("tenant_id") or "",
        correlation_id=corr,
    )
    return {"job": job, "correlation_id": corr}


@router.get("/projects/{project_key}/jobs/{job_id}")
async def get_job(
    project_key: str,
    job_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    tenant_id: str = Query(default=""),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    token = _auth_project(
        authorization,
        project_key=project_key,
        require_grant="jobs",
        correlation_id=corr,
    )
    job = get_job_service().get(
        job_id,
        project_key=project_key,
        tenant_id=tenant_id or token.tenant_id,
    )
    if not job:
        return _error(404, error="job not found", code="not_found", correlation_id=corr)
    return {"job": job, "correlation_id": corr}


@router.post("/projects/{project_key}/jobs/{job_id}/cancel")
async def cancel_job(
    project_key: str,
    job_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, require_grant="jobs", correlation_id=corr)
    job = get_job_service().cancel(job_id, project_key=project_key)
    if not job:
        return _error(404, error="job not found", code="not_found", correlation_id=corr)
    get_event_service().emit_outbound(
        project_key=project_key,
        event_type="keprix.job.cancelled",
        data={"job_id": job_id},
        correlation_id=corr,
    )
    return {"job": job, "idempotent": True, "correlation_id": corr}


def _sse_format(item: dict[str, Any]) -> str:
    cursor = item.get("cursor") or item.get("id") or ""
    payload = json.dumps(item, default=str)
    return f"id: {cursor}\ndata: {payload}\n\n"


@router.get("/projects/{project_key}/jobs/{job_id}/events")
async def job_events_sse(
    project_key: str,
    job_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    cursor: str | None = Query(default=None),
) -> StreamingResponse:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, require_grant="jobs", correlation_id=corr)
    job = get_job_service().get(job_id, project_key=project_key)
    if not job:
        _raise_error(404, error="job not found", code="not_found", correlation_id=corr)

    async def gen() -> AsyncIterator[str]:
        for item in get_event_service().stream_events(project_key, cursor=cursor):
            ev = item.get("event") if isinstance(item.get("event"), dict) else {}
            data = ev.get("data") if isinstance(ev, dict) else {}
            ref = data.get("job_id") if isinstance(data, dict) else None
            if ref is not None and ref != job_id:
                continue
            yield _sse_format(item)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/projects/{project_key}/events")
async def ingest_event(
    project_key: str,
    body: EventEnvelope,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    x_keprix_signature: str | None = Header(default=None),
    x_keprix_timestamp: str | None = Header(default=None),
    x_keprix_key_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, require_grant="events", correlation_id=corr)
    envelope = body.model_dump()
    try:
        result = get_event_service().ingest_inbound(
            project_key=project_key,
            envelope=envelope,
            signature=x_keprix_signature,
            timestamp=x_keprix_timestamp,
            key_id=x_keprix_key_id,
        )
    except ValueError as exc:
        return _error(400, error=str(exc), code=str(exc), correlation_id=corr)
    return {**result, "correlation_id": corr}


@router.get("/projects/{project_key}/events/stream")
async def events_stream(
    project_key: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
    cursor: str | None = Query(default=None),
) -> StreamingResponse:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, require_grant="events", correlation_id=corr)

    async def gen() -> AsyncIterator[str]:
        for item in get_event_service().stream_events(project_key, cursor=cursor):
            yield _sse_format(item)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/projects/{project_key}/approvals/{approval_id}/decision")
async def approval_decision(
    project_key: str,
    approval_id: str,
    body: ApprovalDecision,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, require_grant="approvals", correlation_id=corr)
    try:
        row = get_approval_store().decide(
            approval_id,
            project_key=project_key,
            approved=body.approved,
            actor_id=body.actor_id,
            input_hash=body.input_hash,
        )
    except KeyError:
        return _error(404, error="approval not found", code="not_found", correlation_id=corr)
    except ValueError as exc:
        return _error(409, error=str(exc), code=str(exc), correlation_id=corr)
    return {"approval": row, "correlation_id": corr}


@router.get("/projects/{project_key}/metrics")
async def project_metrics(
    project_key: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    row = _require_project(project_key, correlation_id=corr)
    if authorization or not _dev_open():
        _auth_project(authorization, project_key=project_key, require_grant="metrics", correlation_id=corr)
    snap = get_event_service().snapshot(project_key)
    return {
        "project_key": project_key,
        "enabled": bool(row.get("enabled")),
        "killed": get_project_registry().is_killed(project_key),
        "event_cursor": snap.get("cursor"),
        "contract_version": CONTRACT_VERSION,
    }


@router.post("/projects/{project_key}/admin/kill")
async def admin_kill(
    project_key: str,
    body: KillBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    _require_project(project_key, correlation_id=corr)
    if not _dev_open():
        _auth_admin(authorization, correlation_id=corr)
    else:
        _auth_project(authorization, project_key=project_key, correlation_id=corr)
    get_project_registry().kill(
        project_key,
        switch=body.switch,
        value=body.value,
        node=body.node,
    )
    return {
        "ok": True,
        "switch": body.switch,
        "value": body.value,
        "node": body.node,
        "correlation_id": corr,
    }


@router.post("/admin/apply")
async def admin_apply_manifest(
    body: ApplyManifestBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Apply a validated project manifest into the running registry."""
    corr = _correlation(request, x_correlation_id)
    if not _dev_open():
        _auth_admin(authorization, correlation_id=corr)
    manifest = dict(body.manifest or {})
    key = str(manifest.get("project_key") or "")
    if not key:
        _raise_error(422, error="project_key required", code="validation", correlation_id=corr)
    previous = None
    existing = get_project_registry().get(key)
    if existing:
        previous = existing.get("manifest")
    try:
        result = get_project_registry().apply(
            manifest,
            confirm_risky=body.confirm_risky,
            previous=previous,
        )
    except PermissionError as exc:
        _raise_error(409, error=str(exc), code="confirm_required", correlation_id=corr)
    except ValueError as exc:
        _raise_error(422, error=str(exc)[:500], code="validation", correlation_id=corr)
    return {**result, "correlation_id": corr}


@router.get("/projects/{project_key}/memory/search")
async def memory_search(
    project_key: str,
    request: Request,
    q: str = Query(default=""),
    namespace: str = Query(default="ephemeral"),
    tenant_id: str = Query(default=""),
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    token = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    hits = get_memory_service().search(
        project_key=project_key,
        tenant_id=tenant_id or token.tenant_id,
        query=q,
        namespace=namespace,
    )
    return {"hits": hits, "correlation_id": corr}


@router.post("/projects/{project_key}/memory/write")
async def memory_write(
    project_key: str,
    body: MemoryWriteBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    token = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    try:
        row = get_memory_service().write(
            project_key=project_key,
            tenant_id=body.tenant_id or token.tenant_id,
            namespace=body.namespace,
            content=body.content,
            source=body.source,
            purpose=body.purpose,
            ttl_seconds=body.ttl_seconds,
            actor_id=token.actor_id,
        )
    except PermissionError as exc:
        return _error(403, error=str(exc), code="denied", correlation_id=corr)
    except KeyError:
        return _error(404, error="unknown project_key", code="not_found", correlation_id=corr)
    return {"entry": row, "correlation_id": corr}


@router.post("/projects/{project_key}/memory/delete")
async def memory_delete(
    project_key: str,
    body: MemoryDeleteBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    corr = _correlation(request, x_correlation_id)
    token = _auth_project(authorization, project_key=project_key, correlation_id=corr)
    receipt = get_memory_service().delete_scope(
        project_key=project_key,
        tenant_id=body.tenant_id or token.tenant_id,
        namespace=body.namespace,
    )
    return {"receipt": receipt, "correlation_id": corr}


@router.post("/projects/{project_key}/files/ingest")
async def files_ingest(
    project_key: str,
    body: FileIngestBody,
    request: Request,
    authorization: str | None = Header(default=None),
    x_correlation_id: str | None = Header(default=None),
) -> Any:
    corr = _correlation(request, x_correlation_id)
    _auth_project(authorization, project_key=project_key, correlation_id=corr)
    _require_project(project_key, correlation_id=corr)
    try:
        raw = base64.b64decode(body.data_base64)
        result = FileIngest().ingest(
            project_key=project_key,
            content_type=body.content_type,
            data=raw,
            filename=body.filename,
        )
    except ValueError as exc:
        return _error(400, error=str(exc), code=str(exc), correlation_id=corr)
    except Exception as exc:
        return _error(400, error=str(exc), code="ingest_failed", correlation_id=corr)
    return {"file": result, "correlation_id": corr}


__all__ = ["router", "set_shutting_down", "_shutting_down"]
