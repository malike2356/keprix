"""Credential rotation API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from keprix.api.auth import require_admin
from keprix.api.server import create_app
from keprix.proxy.config import ProxyConfig, RouteConfig, dump_proxy_config


def test_rotation_status_route(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    dump_proxy_config(
        ProxyConfig(
            routes=[
                RouteConfig(
                    host="api.stripe.com",
                    header_name="Authorization",
                    secret_ref="stripe-secret-key",
                    cache={"ttl": "60s"},
                    rotation={"schedule": "90d", "reminder": "7d"},
                )
            ]
        )
    )
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: {"id": "admin", "role": "admin"}
    client = TestClient(app)

    response = client.get("/api/admin/credentials/rotation")

    assert response.status_code == 200
    assert response.json()["credentials"][0]["secret_ref"] == "stripe-secret-key"
