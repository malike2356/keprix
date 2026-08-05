"""Admin billing pricing pin endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_admin_catalog_and_pricing_pin(billing_env, monkeypatch, tmp_path):
    writable = tmp_path / "billing-writable.yaml"
    writable.write_text(Path(__file__).resolve().parents[2].joinpath("config/billing.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("KEPRIX_BILLING_CONFIG", str(writable))

    from keprix.billing import config_loader
    from keprix.api.server import create_app
    from keprix.auth.dependencies import get_current_user

    config_loader._CONFIG = None
    config_loader._CONFIG_PATH = None

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "1", "role": "admin", "username": "admin"}

    client = TestClient(app)
    catalog = client.get("/api/billing/admin/catalog")
    assert catalog.status_code == 200
    items = catalog.json()["items"]
    assert any(item["price_id"] == "price_test_pro_month" for item in items)

    pricing = client.get("/api/billing/admin/pricing")
    assert pricing.status_code == 200
    assert pricing.json()["config_path"].endswith("billing-writable.yaml")

    put = client.put(
        "/api/billing/admin/pricing",
        json={
            "plans": [
                {"id": "community", "prices": []},
                {
                    "id": "pro",
                    "prices": [
                        {"interval": "month", "stripe_price_id": "price_test_pro_month"},
                        {"interval": "year", "stripe_price_id": "price_test_pro_year"},
                    ],
                },
                {
                    "id": "team",
                    "prices": [
                        {"interval": "month", "stripe_price_id": "price_test_team_month"},
                        {"interval": "year", "stripe_price_id": "price_test_team_year"},
                    ],
                },
            ]
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["ok"] is True
    pro = next(plan for plan in body["plans"] if plan["id"] == "pro")
    assert {p["interval"] for p in pro["prices"]} == {"month", "year"}
    assert all(p.get("stripe_price_id") for p in pro["prices"])

    # Reject unknown price IDs (must be in catalog).
    bad = client.put(
        "/api/billing/admin/pricing",
        json={
            "plans": [
                {
                    "id": "pro",
                    "prices": [{"interval": "month", "stripe_price_id": "price_not_in_catalog"}],
                }
            ]
        },
    )
    assert bad.status_code == 400
