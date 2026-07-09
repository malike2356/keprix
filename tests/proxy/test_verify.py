"""Tests for route verification."""

from __future__ import annotations

import json

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.paths import local_vault_path
from keprix.proxy.verify import verify_routes


def test_verify_routes_ok_when_secrets_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().parent.mkdir(parents=True, exist_ok=True)
    local_vault_path().write_text(
        json.dumps({"secrets": {"anthropic-api-key": "value"}}),
        encoding="utf-8",
    )
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.anthropic.com",
                header_name="x-api-key",
                secret_ref="anthropic-api-key",
            )
        ]
    )
    report = verify_routes(config)
    assert report.ok
    assert any("api.anthropic.com" in line for line in report.lines)


def test_verify_routes_fails_on_missing_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {}}), encoding="utf-8")
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.anthropic.com",
                header_name="x-api-key",
                secret_ref="missing-ref",
            )
        ]
    )
    report = verify_routes(config)
    assert not report.ok
