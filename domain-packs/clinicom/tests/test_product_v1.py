from __future__ import annotations

from test_clinicom_sidecar import _load_http_app

from fastapi.testclient import TestClient


def test_product_v1_manifest_and_capabilities() -> None:
    client = TestClient(_load_http_app())
    manifest = client.get("/v1/products/clinicom/manifest")
    capabilities = client.get("/v1/products/clinicom/capabilities")
    assert manifest.status_code == 200
    assert manifest.json()["contract_version"] == "2.0"
    assert capabilities.status_code == 200
    assert capabilities.json()["profile"] == "keprix"


def test_product_v1_invoke_is_proposal_only() -> None:
    client = TestClient(_load_http_app())
    response = client.post(
        "/v1/products/clinicom/invoke",
        json={"capability": "translate", "input": {"text": "No pain", "source_language": "en", "target_language": "en"}},
    )
    assert response.status_code == 200
    assert response.json()["proposal_only"] is True
    assert response.json()["ehr_write"] is False
