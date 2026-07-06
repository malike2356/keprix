"""Tests for billing portal API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.billing.stripe.products import sync_products_and_prices
from keprix.billing.subscriptions.lifecycle import activate_subscription


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.mark.asyncio
async def test_portal_account(client):
    await sync_products_and_prices()
    from keprix.auth.session import auth_manager

    guest_id = str(auth_manager.guest_user().get("id") or "admin")
    await activate_subscription(guest_id, plan_id="pro")
    response = client.get("/api/billing/portal/account")
    assert response.status_code == 200
    body = response.json()
    assert body["product"]["id"] == "example-saas"
    assert "feature_matrix" in body
    assert "plans" in body
    assert isinstance(body["plans"], list)
    assert len(body["plans"]) >= 1
    assert body["plans"][0]["id"]


def test_billing_status_enabled(client):
    response = client.get("/api/billing/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["product_id"] == "example-saas"
    assert body["product_name"] == "Example SaaS"
    assert "trial_days" in body
    assert "plans" in body
    assert len(body["plans"]) >= 1


def test_billing_status_disabled(monkeypatch):
    monkeypatch.setenv("KEPRIX_BILLING_ENABLED", "false")
    from keprix.billing import config_loader

    config_loader._CONFIG = None
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/billing/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_webhook_unsigned_allowed(client):
    payload = {
        "type": "payment_method.attached",
        "data": {"object": {"id": "pm_test"}},
    }
    response = client.post("/api/billing/webhook", json=payload)
    assert response.status_code == 200
    assert response.json().get("ok") is True
