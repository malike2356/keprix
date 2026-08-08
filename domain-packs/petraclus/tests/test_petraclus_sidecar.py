"""HTTP contract tests for the Petraclus Keprix sidecar."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import load_app
from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def test_health_and_capabilities_schemas() -> None:
    client = TestClient(load_app())
    health = client.get("/v1/products/petraclus/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["sidecar"] == "keprix-petraclus"
    assert body["pack_version"] == "0.1.0"
    assert body["contract_version"] == "1.0.0"
    assert body["licence_authority"] == "keys.petraclus.uk"

    caps = client.get("/v1/products/petraclus/capabilities")
    assert caps.status_code == 200
    payload = caps.json()
    assert payload["contract_version"] == "1.0.0"
    keys = {n["key"] for n in payload["nodes"]}
    for required in (
        "asset_get",
        "finding_explain",
        "severity_review",
        "scan_plan_propose",
        "scan_start",
        "report_publish",
    ):
        assert required in keys
    for node in payload["nodes"]:
        assert "risk" in node
        assert "edition_min" in node
        assert "requires_target_grant" in node
        assert "requires_approval" in node


def test_invoke_read() -> None:
    client = TestClient(load_app())
    response = client.post(
        "/v1/products/petraclus/invoke",
        json={
            "capability": "asset_get",
            "workspace_id": "ws-alpha",
            "grants": ["node:*"],
            "input": {"workspace_id": "ws-alpha", "asset_id": "asset-alpha-1", "purpose": "read"},
        },
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["asset"]["id"] == "asset-alpha-1"
    assert "provenance" in result


def test_invoke_analysis() -> None:
    client = TestClient(load_app())
    golden = json.loads((PACK_ROOT / "tests/fixtures/golden_finding.json").read_text(encoding="utf-8"))
    response = client.post(
        "/v1/products/petraclus/invoke",
        json={
            "capability": "severity_review",
            "workspace_id": "ws-alpha",
            "grants": ["node:*"],
            "input": {
                "workspace_id": "ws-alpha",
                "finding_id": golden["id"],
                "purpose": "analysis",
            },
        },
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["review"]["scanner_severity"] == "high"
    assert result["review"]["severity_changed_by_model"] is False
    assert result["provenance"]["observed_scanner_fact"]["cve"] == "CVE-2016-2183"
    assert result["provenance"]["cited_ids"]["finding_ids"] == ["finding-golden-1"]


def test_provision_dry_run() -> None:
    client = TestClient(load_app())
    response = client.post(
        "/v1/products/petraclus/provision",
        json={
            "deployment": "local",
            "workspace_id": "ws-alpha",
            "mode": "local_community",
            "edition": "community",
            "dry_run": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["secrets_included"] is False
