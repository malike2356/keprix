"""Credential audit route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from keprix.api.auth import require_admin
from keprix.api.server import create_app
from keprix.tools.credential_audit import record_credential_audit


def test_admin_credentials_route_lists_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: {"id": "admin", "role": "admin"}
    client = TestClient(app)
    record_credential_audit(
        tool="stripe.create_payment",
        route={"host": "api.stripe.com", "path": "/v1/payment_intents", "method": "POST"},
        credential_ref="stripe-secret-key",
        status="injected",
        duration_ms=234,
        response_status=200,
    )

    response = client.get("/api/admin/credentials")

    assert response.status_code == 200
    payload = response.json()
    assert payload["audit"][0]["tool"] == "stripe.create_payment"
    assert "validation" in payload
