"""Fixture ABBIS product southbound API + Keprix connector client."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from isolation import IsolationContext, IsolationDenied, IsolationEnforcer

PRODUCT_CONTRACT_VERSION = "1.0.0"
_ENFORCER = IsolationEnforcer()
_LOCK = threading.RLock()
_IDEMPOTENCY: dict[str, dict[str, Any]] = {}
_PREVIEWS: dict[str, dict[str, Any]] = {}
_EVENTS_ACKED: set[str] = set()
_OUTBOX: list[dict[str, Any]] = []

# Fixture tenants
FIXTURES = {
    "tenant-alpha": {
        "org": "Sample Operator Alpha",
        "projects": [{"id": "proj-a1", "name": "Site North", "version": 3}],
        "stakeholder": "S07",
        "accessories": [
            "field.operations",
            "quotes.location",
            "drilling.projects",
            "calculators",
            "fleet.maintenance",
            "compliance.registry",
            "inventory.pos",
            "accounting.gl",
        ],
    },
    "tenant-beta": {
        "org": "Sample Operator Beta",
        "projects": [{"id": "proj-b1", "name": "Site East", "version": 1}],
        "stakeholder": "S08",
        "accessories": ["marketplace", "inventory.pos", "calculators"],
    },
}

CONTEXT_SLICES = {
    "dashboard.rig_owner",
    "drf.detail",
    "project.detail",
    "quotation.builder",
    "field.staff_home",
    "client.project",
    "marketplace.vendor",
    "association.exec",
    "intelligence.explore",
    "calculator.run",
}


def reset_fixture_state() -> None:
    with _LOCK:
        _IDEMPOTENCY.clear()
        _PREVIEWS.clear()
        _EVENTS_ACKED.clear()
        _OUTBOX.clear()


def _auth_tenant(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    token = authorization[7:].strip()
    # fixture tokens: abbis.<tenant_id>.<stakeholder>
    parts = token.split(".")
    if len(parts) < 3 or parts[0] != "abbis":
        raise HTTPException(status_code=401, detail="invalid_token")
    return parts[1]


def _isolation_from_headers(
    authorization: str | None,
    *,
    x_purpose: str | None = None,
    x_project: str | None = None,
) -> IsolationContext:
    tenant = _auth_tenant(authorization)
    token = (authorization or "")[7:].strip()
    parts = token.split(".")
    stakeholder = parts[2] if len(parts) > 2 else "S07"
    fixture = FIXTURES.get(tenant)
    if not fixture:
        raise HTTPException(status_code=403, detail="unknown_tenant")
    return IsolationContext(
        product="abbis",
        tenant_id=tenant,
        organisation_id=tenant,
        stakeholder=stakeholder,
        accessories=frozenset(fixture["accessories"]),
        project_id=x_project or "",
        purpose=x_purpose or "product_api",
        grants=frozenset({"*"}),
        onboarding_complete=True,
    )


fixture_app = FastAPI(title="ABBIS Keprix Product Fixture API", version="0.1.0")


class TokenExchangeIn(BaseModel):
    bootstrap_token: str
    tenant_id: str
    actor_id: str
    stakeholder: str = "S07"
    purpose: str = "sidecar_session"
    grants: list[str] = Field(default_factory=list)


class EventAckIn(BaseModel):
    event_id: str
    product: str = "abbis"
    deployment: str = "local"


class ActionPreviewIn(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    record_version: int | None = None


class ActionApplyIn(BaseModel):
    action: str
    preview_hash: str
    idempotency_key: str
    approval_id: str | None = None
    record_version: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@fixture_app.get("/api/keprix/v1/health")
def product_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "product": "abbis",
        "contract_version": PRODUCT_CONTRACT_VERSION,
        "operator": "ghanaian_operating_company",
        "association": "BDAG",
        "mode": "FULL",
    }


@fixture_app.get("/api/keprix/v1/capabilities")
def product_capabilities(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    ctx = _isolation_from_headers(authorization)
    return {
        "contract_version": PRODUCT_CONTRACT_VERSION,
        "product": "abbis",
        "tenant_id": ctx.tenant_id,
        "stakeholder": ctx.stakeholder,
        "accessories": sorted(ctx.accessories),
        "context_slices": sorted(CONTEXT_SLICES),
        "actions": [
            "quote",
            "report",
            "inventory",
            "maintenance_task",
            "activity_message",
            "payment_reminder",
            "marketplace",
        ],
    }


@fixture_app.post("/api/keprix/v1/token/exchange")
def token_exchange(body: TokenExchangeIn) -> dict[str, Any]:
    if body.tenant_id not in FIXTURES:
        raise HTTPException(status_code=403, detail="unknown_tenant")
    token = f"abbis.{body.tenant_id}.{body.stakeholder}"
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 300,
        "product": "abbis",
        "tenant_id": body.tenant_id,
        "actor_id": body.actor_id,
        "purpose": body.purpose,
        "grants": body.grants or ["*"],
    }


@fixture_app.get("/api/keprix/v1/context")
@fixture_app.get("/api/keprix/v1/context/{slice_key}")
def context_slice(
    slice_key: str = "dashboard.rig_owner",
    authorization: str | None = Header(default=None),
    x_purpose: str | None = Header(default=None),
    x_project_id: str | None = Header(default=None),
    fields: str | None = None,
) -> dict[str, Any]:
    ctx = _isolation_from_headers(authorization, x_purpose=x_purpose, x_project=x_project_id)
    if slice_key not in CONTEXT_SLICES:
        raise HTTPException(status_code=404, detail="unknown_slice")
    try:
        _ENFORCER.enforce(ctx, node_key="read_stakeholder_context", required_accessory=None)
    except IsolationDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    fixture = FIXTURES[ctx.tenant_id]
    projected = {
        "slice_key": slice_key,
        "tenant_id": ctx.tenant_id,
        "organisation": fixture["org"],
        "stakeholder": ctx.stakeholder,
        "projects": fixture["projects"],
        "schema_version": "abbis-context@1.0.0",
    }
    if fields:
        keep = {f.strip() for f in fields.split(",") if f.strip()}
        projected = {k: v for k, v in projected.items() if k in keep or k in {"slice_key", "schema_version"}}
    return projected


@fixture_app.get("/api/keprix/v1/localisation")
def localisation() -> dict[str, Any]:
    return {
        "locales": ["en", "tw", "ha", "ee"],
        "fallback": "en",
        "currency": "GHS",
        "units": {"depth": "m", "yield": "lpm"},
        "date_format": "DD/MM/YYYY",
        "operator_copy_source": "abbis",
        "forbidden_terms": ["VERLOX", "KB quote prefix", "Kari"],
        "association_name": "Borehole Drillers Association of Ghana (BDAG)",
        "schema_version": "abbis-localisation@1.0.0",
    }


@fixture_app.get("/api/keprix/v1/reads/{resource}")
def cursor_reads(
    resource: str,
    cursor: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = _isolation_from_headers(authorization)
    allowed = {
        "projects",
        "sites",
        "boreholes",
        "drilling_reports",
        "rigs",
        "fleet",
        "stock",
        "workers",
        "quotes",
        "finance",
        "compliance",
        "marketplace",
        "association",
    }
    if resource not in allowed:
        raise HTTPException(status_code=404, detail="unknown_resource")
    # Cross-tenant fail closed: only return current tenant fixture rows
    items: list[dict[str, Any]] = []
    if resource == "projects":
        items = list(FIXTURES[ctx.tenant_id]["projects"])
    return {"items": items, "next_cursor": None, "tenant_id": ctx.tenant_id}


@fixture_app.post("/api/keprix/v1/actions/{action}/preview")
def action_preview(
    action: str,
    body: ActionPreviewIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = _isolation_from_headers(authorization)
    payload = {"action": action, "tenant_id": ctx.tenant_id, "payload": body.payload, "record_version": body.record_version}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    with _LOCK:
        _PREVIEWS[digest] = {"payload": payload, "created_at": time.time(), "tenant_id": ctx.tenant_id}
    return {
        "preview_hash": digest,
        "action": action,
        "requires_approval": action in {"quote", "inventory", "payment_reminder", "marketplace"},
        "expires_in": 600,
    }


@fixture_app.post("/api/keprix/v1/actions/{action}/apply")
def action_apply(
    action: str,
    body: ActionApplyIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    ctx = _isolation_from_headers(authorization)
    with _LOCK:
        if body.idempotency_key in _IDEMPOTENCY:
            return {**_IDEMPOTENCY[body.idempotency_key], "deduped": True}
        preview = _PREVIEWS.get(body.preview_hash)
        if not preview or preview["tenant_id"] != ctx.tenant_id:
            raise HTTPException(status_code=409, detail="stale_or_unknown_preview")
        if preview["payload"].get("record_version") is not None and body.record_version is not None:
            if preview["payload"]["record_version"] != body.record_version:
                raise HTTPException(status_code=409, detail="stale_record_version")
        result = {
            "status": "applied",
            "action": action,
            "tenant_id": ctx.tenant_id,
            "idempotency_key": body.idempotency_key,
            "preview_hash": body.preview_hash,
            "result_id": f"res_{uuid.uuid4().hex[:10]}",
            "deduped": False,
        }
        _IDEMPOTENCY[body.idempotency_key] = result
        _OUTBOX.append(
            {
                "id": f"evt_{uuid.uuid4().hex[:12]}",
                "type": f"abbis.{action}.applied",
                "tenant": ctx.tenant_id,
                "occurred_at": time.time(),
            }
        )
        return result


@fixture_app.post("/api/keprix/v1/events/ack")
def events_ack(body: EventAckIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _isolation_from_headers(authorization)
    with _LOCK:
        already = body.event_id in _EVENTS_ACKED
        _EVENTS_ACKED.add(body.event_id)
    return {"acked": True, "deduped": already, "event_id": body.event_id}


@fixture_app.get("/api/keprix/v1/events/outbox")
def events_outbox(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _isolation_from_headers(authorization)
    with _LOCK:
        return {"events": list(_OUTBOX)}


class AbbisProductConnector:
    """HTTP client for ABBIS product API (fixture or real)."""

    def __init__(self, base_url: str, access_token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def health(self) -> dict[str, Any]:
        import urllib.request

        req = urllib.request.Request(f"{self.base_url}/api/keprix/v1/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
