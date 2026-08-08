"""Provisioning + product connector fixture tests."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK_ROOT))

from provisioning import plan_provision, provision, upgrade_validate  # noqa: E402
from connector.fixture_product_api import reset_fixture_state  # noqa: E402


def _load_app():
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    for name in list(sys.modules):
        if name == "http_app" or name.startswith("abbis_http_app"):
            del sys.modules[name]
    import http_app

    return http_app.app


def test_provision_entitled_nodes_only() -> None:
    plan = plan_provision(deployment="local", tenant_id="tenant-alpha", stakeholder="S19")
    assert "pipe_count_calculate" in plan["nodes"] or "calculators" in plan["accessories"]
    assert "national_aggregate_summary" not in plan["nodes"]


def test_provision_receipt_secret_free() -> None:
    receipt = provision(deployment="local", tenant_id="tenant-alpha", stakeholder="S07", activate=False)
    assert receipt["secrets_included"] is False
    assert receipt["operator_boundary"]["forbidden"] == ["VERLOX"]
    assert "BDAG" in receipt["operator_boundary"]["association"]


def test_upgrade_blocks_auto_national() -> None:
    assert upgrade_validate(enable_national=True)["ok"] is False
    assert upgrade_validate(enable_accessory="fleet.maintenance")["ok"] is True


def test_connector_preview_apply_idempotent() -> None:
    reset_fixture_state()
    client = TestClient(_load_app())
    headers = {"Authorization": "Bearer abbis.tenant-alpha.S07"}
    preview = client.post(
        "/fixture-product/api/keprix/v1/actions/inventory/preview",
        headers=headers,
        json={"action": "inventory", "payload": {"sku": "pipe", "qty": 2}, "record_version": 1},
    )
    assert preview.status_code == 200
    digest = preview.json()["preview_hash"]
    apply1 = client.post(
        "/fixture-product/api/keprix/v1/actions/inventory/apply",
        headers=headers,
        json={
            "action": "inventory",
            "preview_hash": digest,
            "idempotency_key": "idem-1",
            "record_version": 1,
            "payload": {"sku": "pipe", "qty": 2},
        },
    )
    apply2 = client.post(
        "/fixture-product/api/keprix/v1/actions/inventory/apply",
        headers=headers,
        json={
            "action": "inventory",
            "preview_hash": digest,
            "idempotency_key": "idem-1",
            "record_version": 1,
            "payload": {"sku": "pipe", "qty": 2},
        },
    )
    assert apply1.status_code == 200
    assert apply2.json()["deduped"] is True


def test_cross_tenant_context_fail_closed() -> None:
    client = TestClient(_load_app())
    # beta token cannot read alpha by swapping; context is always self-tenant
    headers = {"Authorization": "Bearer abbis.tenant-beta.S08"}
    ctx = client.get("/fixture-product/api/keprix/v1/context/marketplace.vendor", headers=headers)
    assert ctx.status_code == 200
    assert ctx.json()["tenant_id"] == "tenant-beta"


def test_stale_preview_rejected() -> None:
    reset_fixture_state()
    client = TestClient(_load_app())
    headers = {"Authorization": "Bearer abbis.tenant-alpha.S07"}
    bad = client.post(
        "/fixture-product/api/keprix/v1/actions/quote/apply",
        headers=headers,
        json={
            "action": "quote",
            "preview_hash": "missing",
            "idempotency_key": "idem-x",
            "payload": {},
        },
    )
    assert bad.status_code == 409
