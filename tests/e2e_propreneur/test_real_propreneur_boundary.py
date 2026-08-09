"""Prompt 642: real Propreneur boundary e2e (connector + Soft Wall + agent loop).

Requires KEPRIX_E2E_PROPRENEUR=1 and fixtures from
`propreneur/scripts/aiva-v1-e2e-mint-fixtures.php` plus a running Propreneur
HTTP server. Provider/LLM may be faked; Propreneur and connector are real.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from keprix.product_sidecar.connector import ProductApiConnector, assert_safe_url
from keprix.product_sidecar.generated import load_propreneur_connector_routes, load_propreneur_pack_nodes
from keprix.product_sidecar.invoke import invoke_node
from keprix.product_sidecar.packs.propreneur_ops import execute_propreneur_node
from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.state import (
    get_approval_store,
    input_hash,
    reset_all_sidecar_state_for_tests,
)
from keprix.product_sidecar.trusted_context import TrustedExecutionContext
from keprix.product_sidecar.types import RequestContext

pytestmark = pytest.mark.skipif(
    os.environ.get("KEPRIX_E2E_PROPRENEUR") != "1",
    reason="Set KEPRIX_E2E_PROPRENEUR=1 and run keprix/scripts/propreneur-e2e-harness.sh",
)


def _fixtures() -> dict:
    path = Path(os.environ.get("KEPRIX_E2E_PROPRENEUR_FIXTURES", "/tmp/propreneur-e2e-fixtures.json"))
    if not path.is_file():
        pytest.fail(
            f"PREFLIGHT FAILED: missing fixtures at {path}. "
            "Run bash keprix/scripts/propreneur-e2e-harness.sh"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret-642")
    reset_all_sidecar_state_for_tests()
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


@pytest.fixture
def fx() -> dict:
    return _fixtures()


@pytest.fixture
def tenant_a(fx: dict) -> dict:
    return fx["tenants"][0]


@pytest.fixture
def tenant_b(fx: dict) -> dict:
    return fx["tenants"][1]


@pytest.fixture
def connector(fx: dict) -> ProductApiConnector:
    base = str(fx["base_url"]).rstrip("/")
    routes = list(load_propreneur_connector_routes().get("routes") or [])
    return ProductApiConnector(
        base_url=base,
        host_allowlist=["127.0.0.1", "localhost", "propreneur.local", "*.propreneur.test"],
        routes=routes,
    )


def _ctx(tenant: dict, **kwargs: object) -> RequestContext:
    base = dict(
        product="propreneur",
        deployment="e2e",
        workspace_id=tenant["workspace_id"],
        actor_id=str(tenant["actor_id"]),
        grants=frozenset({"*"}),
        purpose="e2e",
        correlation_id=f"corr-642-{uuid.uuid4().hex[:8]}",
        session_id=f"sess-642-{uuid.uuid4().hex[:8]}",
    )
    base.update(kwargs)
    return RequestContext(**base)  # type: ignore[arg-type]


def _trusted(tenant: dict, **kwargs: object) -> TrustedExecutionContext:
    fields = dict(
        product="propreneur",
        workspace_id=tenant["workspace_id"],
        actor_id=str(tenant["actor_id"]),
        actor_type="tenant_user",
        correlation_id=f"corr-642-{uuid.uuid4().hex[:8]}",
        authorization_bearer=tenant["api_key"],
        product_host=tenant["host"],
        idempotency_key="",
    )
    fields.update(kwargs)
    return TrustedExecutionContext(**fields)  # type: ignore[arg-type]


async def _approve(workspace_id: str, node_key: str, payload: dict) -> dict:
    store = get_approval_store()
    control_keys = {
        "approval_id",
        "approval_token",
        "idempotency_key",
        "correlation_id",
        "etag",
        "if_match",
        "tool_call_id",
    }
    body = {k: v for k, v in payload.items() if k not in control_keys}
    row = store.request(
        product="propreneur",
        workspace_id=workspace_id,
        node_key=node_key,
        input_hash=input_hash(body),
        reason=f"e2e {node_key}",
        deep_link="/e2e",
    )
    store.decide(row["approval_id"], workspace_id=workspace_id, approved=True, actor_id="e2e-approver")
    out = dict(payload)
    out["approval_id"] = row["approval_id"]
    return out


@pytest.mark.asyncio
async def test_property_crud_via_pack_invoke_and_chat_adapter(
    connector: ProductApiConnector, tenant_a: dict
) -> None:
    ctx = _ctx(tenant_a)
    idem = f"e2e-prop-{uuid.uuid4().hex}"
    create_payload = await _approve(
        tenant_a["workspace_id"],
        "property_create",
        {
            "address_line1": "7 E2E Avenue",
            "city": "Leeds",
            "postcode": "LS7 7EE",
            "property_type": "flat",
            "status": "owned",
            "idempotency_key": idem,
        },
    )
    created = await execute_propreneur_node(
        ctx,
        "property_create",
        create_payload,
        connector=connector,
        trusted=_trusted(tenant_a, idempotency_key=idem),
    )
    assert created.get("success") is True, created
    prop_id = str(created.get("record_id") or (created.get("data") or {}).get("id") or "")
    assert prop_id

    got = await execute_propreneur_node(
        ctx,
        "property_get",
        {"propertyId": prop_id},
        connector=connector,
        trusted=_trusted(tenant_a),
    )
    assert got.get("success") is True, got
    etag = str(got.get("etag") or connector.last_response_headers.get("etag") or "")
    assert etag, f"expected ETag on property GET; headers={connector.last_response_headers} got={got}"

    upd_idem = f"e2e-upd-{uuid.uuid4().hex}"
    update_payload = await _approve(
        tenant_a["workspace_id"],
        "property_update",
        {"propertyId": prop_id, "city": "York", "idempotency_key": upd_idem},
    )
    updated = await execute_propreneur_node(
        ctx,
        "property_update",
        update_payload,
        connector=connector,
        trusted=_trusted(tenant_a, if_match=etag, idempotency_key=upd_idem),
    )
    assert updated.get("success") is True, updated

    # Re-read ETag then archive (Soft Wall + DELETE)
    await execute_propreneur_node(
        ctx,
        "property_get",
        {"propertyId": prop_id},
        connector=connector,
        trusted=_trusted(tenant_a),
    )
    etag2 = connector.last_response_headers.get("etag", "")
    arch_idem = f"e2e-arch-{uuid.uuid4().hex}"
    arch_payload = await _approve(
        tenant_a["workspace_id"],
        "property_archive",
        {"propertyId": prop_id, "idempotency_key": arch_idem},
    )
    archived = await execute_propreneur_node(
        ctx,
        "property_archive",
        arch_payload,
        connector=connector,
        trusted=_trusted(tenant_a, if_match=etag2, idempotency_key=arch_idem),
    )
    assert archived.get("success") is True, archived

    # Chat-style list path (same adapter)
    listed = await execute_propreneur_node(
        ctx,
        "property_search",
        {"q": "York"},
        connector=connector,
        trusted=_trusted(tenant_a),
    )
    assert listed.get("success") is True, listed


@pytest.mark.asyncio
async def test_cross_tenant_get_fails_closed(
    connector: ProductApiConnector, tenant_a: dict, tenant_b: dict
) -> None:
    ctx = _ctx(tenant_a)
    idem = f"iso-{uuid.uuid4().hex}"
    create_payload = await _approve(
        tenant_a["workspace_id"],
        "property_create",
        {
            "address_line1": "9 Isolation Way",
            "city": "Leeds",
            "postcode": "LS9 9II",
            "property_type": "flat",
            "status": "owned",
            "idempotency_key": idem,
        },
    )
    created = await execute_propreneur_node(
        ctx,
        "property_create",
        create_payload,
        connector=connector,
        trusted=_trusted(tenant_a, idempotency_key=idem),
    )
    assert created.get("success") is True, created
    prop_id = str((created.get("data") or {}).get("id"))

    bad = await execute_propreneur_node(
        _ctx(tenant_b),
        "property_get",
        {"propertyId": prop_id},
        connector=connector,
        trusted=_trusted(tenant_b, product_host=tenant_a["host"]),
    )
    assert bad.get("success") is False
    assert bad.get("status") in {"failed", "conflict"}


@pytest.mark.asyncio
async def test_ssrf_circuit_and_emergency_disable_fail_closed(
    connector: ProductApiConnector, tenant_a: dict
) -> None:
    with pytest.raises(Exception):
        assert_safe_url(
            "http://169.254.169.254/latest/meta-data/",
            host_allowlist=connector.host_allowlist,
        )

    registry = get_product_pack_registry()
    registry.disable_node("propreneur", "property_get")
    try:
        denied = await invoke_node(
            _ctx(tenant_a),
            node_key="property_get",
            input_payload={"propertyId": "1"},
        )
        blob = json.dumps(denied).lower()
        assert "denied" in blob or "kill" in blob or denied.get("ok") is False
    except Exception as exc:
        assert "kill" in str(exc).lower() or "denied" in str(exc).lower()
    finally:
        registry.enable_node("propreneur", "property_get")

    connector._circuit_open = True
    with pytest.raises(Exception):
        await connector.call("GET", "/api/aiva/v1/properties", headers=_trusted(tenant_a).to_headers())
    connector.reset_circuit()


@pytest.mark.asyncio
async def test_soft_wall_bypass_and_forged_identity_stripped(
    connector: ProductApiConnector, tenant_a: dict, tenant_b: dict
) -> None:
    ctx = _ctx(tenant_a)
    blocked = await execute_propreneur_node(
        ctx,
        "property_create",
        {
            "address_line1": "No Approve",
            "city": "Leeds",
            "postcode": "LS0 0AA",
            "property_type": "flat",
            "status": "owned",
        },
        connector=connector,
        trusted=_trusted(tenant_a),
    )
    assert blocked.get("success") is False
    assert blocked.get("status") == "awaiting_approval"

    # Model-supplied identity fields must not switch tenant credentials.
    got = await execute_propreneur_node(
        ctx,
        "property_search",
        {
            "q": "x",
            "workspace_id": tenant_b["workspace_id"],
            "authorization_bearer": tenant_b["api_key"],
            "actor_id": "forged",
            "product_host": tenant_b["host"],
        },
        connector=connector,
        trusted=_trusted(tenant_a),
    )
    assert isinstance(got, dict)
    assert got.get("success") is True or got.get("status") == "completed"


def test_live_capability_inventory_nonempty() -> None:
    nodes = load_propreneur_pack_nodes().get("nodes") or []
    live = [n for n in nodes if n.get("status") in {"live", "approval_required"}]
    assert live, "expected live/approval_required nodes for evidence mapping"
