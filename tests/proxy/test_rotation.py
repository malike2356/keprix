"""Credential rotation tests."""

from __future__ import annotations

import json

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.injector import CredentialInjector
from keprix.proxy.paths import local_vault_path, rotation_state_path
from keprix.proxy.rotation import rotation_status, write_rotation_signal


def _config() -> ProxyConfig:
    return ProxyConfig(
        routes=[
            RouteConfig(
                host="api.anthropic.com",
                header_name="x-api-key",
                secret_ref="anthropic-api-key",
                cache="none",
            )
        ]
    )


def test_per_request_fetch_detects_vault_rotation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {"anthropic-api-key": "old"}}), encoding="utf-8")
    injector = CredentialInjector(_config())

    first = injector.inject_headers("api.anthropic.com", {})
    local_vault_path().write_text(json.dumps({"secrets": {"anthropic-api-key": "new"}}), encoding="utf-8")
    second = injector.inject_headers("api.anthropic.com", {})

    assert first["x-api-key"] == "old"
    assert second["x-api-key"] == "new"
    state = json.loads(rotation_state_path().read_text(encoding="utf-8"))
    assert state["events"][0]["event"] == "credential.rotated"


def test_rotation_status_lists_configured_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.stripe.com",
                header_name="Authorization",
                secret_ref="stripe-secret-key",
                scheme="Bearer",
                cache={"ttl": "60s"},
                rotation={"schedule": "90d", "reminder": "7d"},
            )
        ]
    )

    status = rotation_status(config)

    assert status["credentials"][0]["secret_ref"] == "stripe-secret-key"
    assert status["credentials"][0]["cache_ttl"] == "60s"
    assert status["credentials"][0]["rotation"]["schedule"] == "90d"


def test_rotate_signal_invalidates_ttl_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.sendgrid.com",
                header_name="Authorization",
                secret_ref="sendgrid-api-key",
                cache={"ttl": "60s"},
            )
        ]
    )
    local_vault_path().write_text(json.dumps({"secrets": {"sendgrid-api-key": "old"}}), encoding="utf-8")
    injector = CredentialInjector(config)
    assert injector.inject_headers("api.sendgrid.com", {})["Authorization"] == "old"

    local_vault_path().write_text(json.dumps({"secrets": {"sendgrid-api-key": "new"}}), encoding="utf-8")
    assert injector.inject_headers("api.sendgrid.com", {})["Authorization"] == "old"
    write_rotation_signal("sendgrid-api-key")

    assert injector.inject_headers("api.sendgrid.com", {})["Authorization"] == "new"
