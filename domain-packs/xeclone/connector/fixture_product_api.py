"""Fixture Xeclone product southbound API (tenant owner-laud)."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from persona.binding import PINNED_VERSION

PRODUCT_CONTRACT_VERSION = "1.0.0"
PACK_ROOT = Path(__file__).resolve().parents[1]
_LOCK = threading.RLock()
_IDEMPOTENCY: dict[str, dict[str, Any]] = {}
_EVENTS_ACKED: set[str] = set()

FIXTURE_TENANT = "owner-laud"

DECLARED_ROUTES: set[str] = set()


def _load_declared_routes() -> set[str]:
    manifest = yaml.safe_load((PACK_ROOT / "connector" / "manifest.yaml").read_text(encoding="utf-8"))
    routes = set()
    for row in manifest.get("routes") or []:
        routes.add(f"{row['method']} {row['path']}")
    return routes


DECLARED_ROUTES = _load_declared_routes()


def reset_fixture_state() -> None:
    with _LOCK:
        _IDEMPOTENCY.clear()
        _EVENTS_ACKED.clear()


def is_route_declared(method: str, path: str) -> bool:
    key = f"{method.upper()} {path}"
    if key in DECLARED_ROUTES:
        return True
    # template match for path params
    for declared in DECLARED_ROUTES:
        m, p = declared.split(" ", 1)
        if m != method.upper():
            continue
        dparts = p.strip("/").split("/")
        parts = path.strip("/").split("/")
        if len(dparts) != len(parts):
            continue
        ok = True
        for a, b in zip(dparts, parts):
            if a.startswith("{") and a.endswith("}"):
                continue
            if a != b:
                ok = False
                break
        if ok:
            return True
    return False


def deny_undeclared(method: str, path: str) -> None:
    if not is_route_declared(method, path):
        raise HTTPException(status_code=403, detail="connector_default_deny")


fixture_app = FastAPI(title="Xeclone Keprix Product Fixture API", version="0.1.0")


class TokenExchangeIn(BaseModel):
    bootstrap_token: str
    tenant_id: str = FIXTURE_TENANT
    actor_id: str
    purpose: str = "sidecar_session"
    grants: list[str] = Field(default_factory=list)


class EventAckIn(BaseModel):
    event_id: str
    product: str = "xeclone"
    deployment: str = "local"


class ActionPreviewIn(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionApplyIn(BaseModel):
    action: str
    preview_hash: str
    idempotency_key: str
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _auth_tenant(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    token = authorization[7:].strip()
    parts = token.split(".")
    if len(parts) < 2 or parts[0] != "xeclone":
        raise HTTPException(status_code=401, detail="invalid_token")
    tenant = parts[1]
    if tenant != FIXTURE_TENANT:
        raise HTTPException(status_code=403, detail="unknown_tenant")
    return tenant


@fixture_app.get("/api/keprix/v1/health")
def product_health() -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/health")
    return {
        "status": "ok",
        "product": "xeclone",
        "contract_version": PRODUCT_CONTRACT_VERSION,
        "tenant": FIXTURE_TENANT,
        "persona_version": PINNED_VERSION,
    }


@fixture_app.get("/api/keprix/v1/capabilities")
def product_capabilities(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/capabilities")
    _auth_tenant(authorization)
    return {
        "product": "xeclone",
        "contract_version": PRODUCT_CONTRACT_VERSION,
        "persona_version": PINNED_VERSION,
        "reads": ["persona", "consent", "calendar", "channels", "inbound", "approvals", "artifacts"],
        "actions": ["draft", "attach_artifact", "schedule", "record_generation", "publish", "ack_inbound"],
    }


@fixture_app.post("/api/keprix/v1/token/exchange")
def token_exchange(body: TokenExchangeIn) -> dict[str, Any]:
    deny_undeclared("POST", "/api/keprix/v1/token/exchange")
    if body.tenant_id != FIXTURE_TENANT:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    token = f"xeclone.{body.tenant_id}.{body.actor_id}"
    return {
        "access_token": token,
        "expires_in": 600,
        "tenant_id": body.tenant_id,
        "actor_id": body.actor_id,
        "purpose": body.purpose,
        "grants": body.grants or ["*"],
    }


@fixture_app.get("/api/keprix/v1/context")
def context(authorization: str | None = Header(default=None), slice_key: str = "dashboard") -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/context")
    tenant = _auth_tenant(authorization)
    return {
        "tenant_id": tenant,
        "slice_key": slice_key,
        "persona_version": PINNED_VERSION,
        "bulk_private_corpus": False,
        "fields": {"display_name": "iLaud", "locale": "en-GB"},
    }


@fixture_app.post("/api/keprix/v1/events/ack")
def events_ack(body: EventAckIn, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("POST", "/api/keprix/v1/events/ack")
    _auth_tenant(authorization)
    with _LOCK:
        if body.event_id in _EVENTS_ACKED:
            return {"acked": True, "deduped": True}
        _EVENTS_ACKED.add(body.event_id)
    return {"acked": True, "deduped": False}


@fixture_app.get("/api/keprix/v1/persona/version")
def persona_version_endpoint(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/persona/version")
    _auth_tenant(authorization)
    return {"persona_version": PINNED_VERSION, "carina_pin": PINNED_VERSION, "keprix_pin": PINNED_VERSION}


@fixture_app.get("/api/keprix/v1/consent/eligibility")
def consent_eligibility(
    authorization: str | None = Header(default=None),
    asset_id: str = "",
    purpose: str = "generate",
) -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/consent/eligibility")
    _auth_tenant(authorization)
    return {"asset_id": asset_id, "purpose": purpose, "eligible": bool(asset_id), "forged_consent_accepted": False}


@fixture_app.get("/api/keprix/v1/calendar")
def calendar(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/calendar")
    _auth_tenant(authorization)
    return {"items": [], "tenant_id": FIXTURE_TENANT}


@fixture_app.get("/api/keprix/v1/channels")
def channels(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", "/api/keprix/v1/channels")
    _auth_tenant(authorization)
    return {"channels": [{"id": "web", "status": "connected", "oauth_exposed": False}]}


@fixture_app.get("/api/keprix/v1/inbound/{item_id}")
def inbound_item(item_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", f"/api/keprix/v1/inbound/{item_id}")
    _auth_tenant(authorization)
    return {"item_id": item_id, "text": "fixture inbound", "tenant_id": FIXTURE_TENANT}


@fixture_app.get("/api/keprix/v1/approvals/{approval_id}")
def approval_item(approval_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", f"/api/keprix/v1/approvals/{approval_id}")
    _auth_tenant(authorization)
    return {"approval_id": approval_id, "status": "pending"}


@fixture_app.get("/api/keprix/v1/artifacts/{artifact_id}")
def artifact_ref(artifact_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    deny_undeclared("GET", f"/api/keprix/v1/artifacts/{artifact_id}")
    _auth_tenant(authorization)
    return {"artifact_id": artifact_id, "uri": f"product://artifacts/{artifact_id}", "secret": None}


@fixture_app.post("/api/keprix/v1/actions/{action}/preview")
def action_preview(
    action: str,
    body: ActionPreviewIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    deny_undeclared("POST", f"/api/keprix/v1/actions/{action}/preview")
    _auth_tenant(authorization)
    preview_hash = hashlib.sha256(json.dumps(body.payload, sort_keys=True).encode()).hexdigest()
    return {"action": action, "preview_hash": preview_hash, "payload": body.payload}


@fixture_app.post("/api/keprix/v1/actions/{action}/apply")
def action_apply(
    action: str,
    body: ActionApplyIn,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    deny_undeclared("POST", f"/api/keprix/v1/actions/{action}/apply")
    _auth_tenant(authorization)
    with _LOCK:
        if body.idempotency_key in _IDEMPOTENCY:
            return {"deduped": True, **_IDEMPOTENCY[body.idempotency_key]}
        row = {
            "action": action,
            "preview_hash": body.preview_hash,
            "approval_id": body.approval_id,
            "status": "applied",
            "idempotency_key": body.idempotency_key,
        }
        _IDEMPOTENCY[body.idempotency_key] = row
    return {"deduped": False, **row}


@fixture_app.api_route("/api/keprix/v1/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def catch_undeclared(full_path: str) -> dict[str, Any]:
    raise HTTPException(status_code=403, detail="connector_default_deny")
