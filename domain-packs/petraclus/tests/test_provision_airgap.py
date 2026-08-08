"""Air-gap and provisioning tests for Petraclus."""

from __future__ import annotations

import json

from conftest import PACK_ROOT, load_app
from fastapi.testclient import TestClient


def test_airgap_plan_has_no_phone_home() -> None:
    client = TestClient(load_app())
    response = client.get("/v1/products/petraclus/airgap/bundle")
    assert response.status_code == 200
    body = response.json()
    assert body["phone_home"] is False
    assert body["secrets_included"] is False
    assert "licence_phone_home" in body["excludes"]
    assert "telemetry" in body["excludes"]

    manifest = json.loads((PACK_ROOT / "airgap/bundle.manifest.json").read_text(encoding="utf-8"))
    assert manifest["phone_home"] is False
    assert manifest["secrets_included"] is False


def test_upgrade_does_not_auto_enable_risky() -> None:
    client = TestClient(load_app())
    denied = client.post(
        "/v1/products/petraclus/upgrade/validate",
        json={"enable_risky_nodes": True},
    )
    assert denied.status_code == 200
    assert denied.json()["ok"] is False
    assert denied.json()["auto_enabled_risky"] is False

    ok = client.post(
        "/v1/products/petraclus/upgrade/validate",
        json={"enable_risky_nodes": False},
    )
    assert ok.json()["ok"] is True
    assert ok.json()["auto_enabled_risky"] is False


def test_rollback_and_receipt_secrets_false() -> None:
    client = TestClient(load_app())
    rb = client.post(
        "/v1/products/petraclus/rollback",
        json={"to_pack_version": "0.0.1"},
    )
    assert rb.status_code == 200
    assert rb.json()["status"] == "rolled_back"
    assert rb.json()["licence_unchanged"] is True

    provisioned = client.post(
        "/v1/products/petraclus/provision",
        json={
            "deployment": "local",
            "workspace_id": "ws-alpha",
            "mode": "air_gapped",
            "edition": "community",
            "dry_run": False,
            "activate": False,
        },
    )
    assert provisioned.status_code == 200
    body = provisioned.json()
    assert body["secrets_included"] is False
    assert body["licence_minted"] is False
