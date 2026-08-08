"""HTTP contract tests for the ABBIS Keprix sidecar."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def _load_app():
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    for name in list(sys.modules):
        if name == "http_app" or name.startswith("abbis_http_app"):
            del sys.modules[name]
    import http_app

    return http_app.app


def test_health_and_capabilities() -> None:
    client = TestClient(_load_app())
    health = client.get("/v1/products/abbis/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["sidecar"] == "keprix-abbis"
    assert body["operator"] == "ghanaian_operating_company"
    assert body["association"] == "BDAG"

    caps = client.get("/v1/products/abbis/capabilities")
    assert caps.status_code == 200
    keys = {n["key"] for n in caps.json()["nodes"]}
    assert "pipe_count_calculate" in keys
    assert "national_aggregate_summary" in keys


def test_invoke_pipe_count() -> None:
    client = TestClient(_load_app())
    response = client.post(
        "/v1/products/abbis/invoke",
        json={"capability": "pipe_count_calculate", "input": {"overburden_m": 45}},
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["pipes_required"] == 15
    assert result["value_kind"] == "calculated"


def test_invoke_pump_and_quote() -> None:
    client = TestClient(_load_app())
    pump = client.post(
        "/v1/products/abbis/invoke",
        json={
            "capability": "pump_yield_calculate",
            "input": {
                "bucket_litres": 20,
                "fill_seconds": 10,
                "drawdown_minutes": 15,
                "recovery_minutes": 45,
            },
        },
    )
    assert pump.status_code == 200
    assert pump.json()["result"]["yield_lpm"] == 120.0

    quote = client.post(
        "/v1/products/abbis/invoke",
        json={
            "capability": "quote_calculate",
            "input": {
                "overburden_m": 45,
                "depth_m": 60,
                "margin_pct": 20,
                "rig_rental_ghs": 10000,
            },
        },
    )
    assert quote.status_code == 200
    assert quote.json()["result"]["currency"] == "GHS"


def test_forbidden_kb_prefix() -> None:
    client = TestClient(_load_app())
    response = client.post(
        "/v1/products/abbis/invoke",
        json={
            "capability": "quote_calculate",
            "input": {
                "overburden_m": 45,
                "depth_m": 60,
                "margin_pct": 20,
                "quote_prefix": "KB-001",
            },
        },
    )
    assert response.status_code == 400


def test_event_dedupe_and_job_cancel() -> None:
    client = TestClient(_load_app())
    evt = {"id": "e1", "type": "calculator.run", "source": "abbis", "tenant": "tenant-alpha"}
    assert client.post("/v1/products/abbis/events", json=evt).json()["deduped"] is False
    assert client.post("/v1/products/abbis/events", json=evt).json()["deduped"] is True

    job = client.post(
        "/v1/products/abbis/jobs",
        json={
            "capability": "pipe_count_calculate",
            "input": {"overburden_m": 5},
            "tenant_id": "t1",
        },
    ).json()
    cancelled = client.post(f"/v1/products/abbis/jobs/{job['job_id']}/cancel").json()
    assert cancelled["status"] in {"completed", "cancelled"}


def test_fixture_product_health() -> None:
    client = TestClient(_load_app())
    response = client.get("/fixture-product/api/keprix/v1/health")
    assert response.status_code == 200
    assert response.json()["product"] == "abbis"
