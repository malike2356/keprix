"""Tool credential validator tests."""

from __future__ import annotations

import json

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.paths import local_vault_path
from keprix.tools.credential_contract import CredentialRoute, ToolCredentialRegistry
from keprix.tools.credential_validator import validate_all, validation_summary


def test_validator_fails_when_route_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    registry = ToolCredentialRegistry()
    registry.register("web_search.search", [CredentialRoute(host="api.tavily.com", header="Authorization", secret_ref="tavily-api-key")])

    results = validate_all(registry, config=ProxyConfig(routes=[]), proxy_running=True)

    assert results[0].status == "fail"
    assert "route not configured" in results[0].message
    assert validation_summary(results)["fail_count"] == 1


def test_validator_warns_when_secret_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {}}), encoding="utf-8")
    registry = ToolCredentialRegistry()
    registry.register(
        "google_calendar.create",
        [CredentialRoute(host="www.googleapis.com", header="Authorization", scheme="Bearer", secret_ref="google-api-key")],
    )
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="www.googleapis.com",
                header_name="Authorization",
                scheme="Bearer",
                secret_ref="google-api-key",
            )
        ]
    )

    results = validate_all(registry, config=config, proxy_running=True)

    assert results[0].status == "warn"
    assert "not found" in results[0].message


def test_validator_ok_when_proxy_route_and_secret_exist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {"stripe-secret-key": "sk-test"}}), encoding="utf-8")
    registry = ToolCredentialRegistry()
    registry.register(
        "stripe.create_payment",
        [CredentialRoute(host="api.stripe.com", header="Authorization", scheme="Bearer", secret_ref="stripe-secret-key")],
    )
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.stripe.com",
                header_name="Authorization",
                scheme="Bearer",
                secret_ref="stripe-secret-key",
            )
        ]
    )

    results = validate_all(registry, config=config, proxy_running=True)

    assert results[0].status == "ok"
