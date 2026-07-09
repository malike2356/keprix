"""Tests for credential header injection."""

from __future__ import annotations

import json

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.injector import CredentialInjector
from keprix.proxy.paths import local_vault_path


def test_injector_adds_header_with_scheme(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(
        json.dumps({"secrets": {"openai-api-key": "sk-test"}}),
        encoding="utf-8",
    )
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.openai.com",
                header_name="Authorization",
                secret_ref="openai-api-key",
                scheme="Bearer",
            )
        ]
    )
    injector = CredentialInjector(config)
    headers = injector.inject_headers("api.openai.com", {"User-Agent": "test"})
    assert headers["Authorization"] == "Bearer sk-test"
    assert headers["User-Agent"] == "test"


def test_injector_leaves_unmatched_hosts_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {}}), encoding="utf-8")
    injector = CredentialInjector(ProxyConfig())
    headers = {"Host": "example.com"}
    assert injector.inject_headers("example.com", headers) == headers
