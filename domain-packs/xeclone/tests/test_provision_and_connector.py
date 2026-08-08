"""Provision and connector boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def _client() -> TestClient:
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    import http_app

    return TestClient(http_app.app)


def test_provision_and_deprovision() -> None:
    client = _client()
    plan = client.get("/v1/products/xeclone/provision/plan", params={"tenant_id": "owner-laud"})
    assert plan.status_code == 200
    assert plan.json()["product"] == "xeclone"
    assert plan.json()["autonomous_mode"] is False

    prov = client.post(
        "/v1/products/xeclone/provision",
        json={"tenant_id": "owner-laud", "deployment": "local", "activate": True},
    )
    assert prov.status_code == 200
    receipt = prov.json()
    assert receipt["secrets_included"] is False
    assert receipt["carina_path_changed"] is False
    assert "token" not in json_keys_lower(receipt)

    deprov = client.post(
        "/v1/products/xeclone/deprovision",
        json={"tenant_id": "owner-laud", "deployment": "local"},
    )
    assert deprov.status_code == 200
    assert deprov.json()["tokens_revoked"] is True
    assert deprov.json()["secrets_included"] is False


def json_keys_lower(obj, acc=None):
    acc = acc or set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k).lower())
            json_keys_lower(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            json_keys_lower(item, acc)
    return acc


def test_connector_deny_undeclared() -> None:
    client = _client()
    # Declared health works
    ok = client.get("/fixture-product/api/keprix/v1/health")
    assert ok.status_code == 200
    # Undeclared path denied
    denied = client.get("/fixture-product/api/keprix/v1/secret-dump")
    assert denied.status_code == 403
    assert denied.json()["detail"] == "connector_default_deny"


def test_rag_boundaries() -> None:
    client = _client()
    # Cross-tenant must not leak
    other = client.post(
        "/v1/products/xeclone/rag/search",
        json={"query": "never", "tenant_id": "owner-laud", "audience": "public"},
    )
    assert other.status_code == 200
    texts = " ".join(h.get("text", "") for h in other.json()["hits"])
    assert "other-tenant" not in texts
    assert "Must never appear" not in texts

    # Relationship excluded from public audience
    rel = client.post(
        "/v1/products/xeclone/rag/search",
        json={"query": "family", "tenant_id": "owner-laud", "audience": "public"},
    )
    assert all(h.get("sensitivity") != "relationship" for h in rel.json()["hits"])
