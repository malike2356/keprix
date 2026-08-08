"""Connector contract tests for Petraclus fixture API."""

from __future__ import annotations

import sys

import yaml
from conftest import PACK_ROOT, load_app
from fastapi.testclient import TestClient


def test_declared_endpoints_only() -> None:
    manifest = yaml.safe_load((PACK_ROOT / "connector/manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["default_deny"] is True
    paths = {row["path"] for row in manifest["routes"]}
    assert "/api/keprix/v1/findings/{id}" in paths
    assert "/api/keprix/v1/scans/start" in paths
    assert manifest["no_sql"] is True
    assert manifest["no_ui_scrape"] is True

    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    from connector.fixture_product_api import PetraclusProductConnector

    client = TestClient(load_app())
    connector = PetraclusProductConnector(token="petraclus.ws-alpha.tester", transport_client=client)
    try:
        connector.request("GET", "/api/keprix/v1/secret-dump")
        assert False, "expected allowlist denial"
    except PermissionError as exc:
        assert "path_not_allowlisted" in str(exc)

    health = client.get("/fixture-product/api/keprix/v1/health")
    assert health.status_code == 200
    assert health.json()["product"] == "petraclus"


def test_redaction_and_edition_gates() -> None:
    client = TestClient(load_app())
    token = "petraclus.ws-alpha.tester"
    evidence = client.get(
        "/fixture-product/api/keprix/v1/evidence/evidence-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert evidence.status_code == 200
    body = evidence.json()
    assert body["redacted"] is True
    assert body["raw"] is None

    audit = client.get(
        "/fixture-product/api/keprix/v1/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit.status_code == 403

    ticket_preview = client.post(
        "/fixture-product/api/keprix/v1/tickets/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"workspace_id": "ws-alpha", "payload": {"title": "x"}},
    )
    assert ticket_preview.status_code == 403


def test_duplicate_action_prevention_and_stale_approval() -> None:
    client = TestClient(load_app())
    token = "petraclus.ws-alpha.tester"
    headers = {"Authorization": f"Bearer {token}"}

    start = client.post(
        "/fixture-product/api/keprix/v1/scans/start",
        headers=headers,
        json={
            "workspace_id": "ws-alpha",
            "target_grant_id": "grant-valid",
            "approval_id": "missing-appr",
            "input_hash": "h1",
            "idempotency_key": "idem-1",
            "plan": {},
        },
    )
    assert start.status_code == 409

    client.post(
        "/fixture-product/api/keprix/v1/approvals/appr-dup/decision",
        headers=headers,
        json={"approved": True, "actor_id": "t", "input_hash": "h-dup", "workspace_id": "ws-alpha"},
    )
    first = client.post(
        "/fixture-product/api/keprix/v1/scans/start",
        headers=headers,
        json={
            "workspace_id": "ws-alpha",
            "target_grant_id": "grant-valid",
            "approval_id": "appr-dup",
            "input_hash": "h-dup",
            "idempotency_key": "idem-dup",
            "plan": {},
        },
    )
    second = client.post(
        "/fixture-product/api/keprix/v1/scans/start",
        headers=headers,
        json={
            "workspace_id": "ws-alpha",
            "target_grant_id": "grant-valid",
            "approval_id": "appr-dup",
            "input_hash": "h-dup",
            "idempotency_key": "idem-dup",
            "plan": {},
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["deduped"] is True
    assert first.json()["scan_id"] == second.json()["scan_id"]
