"""Credential rotation grace path tests."""

from __future__ import annotations

import json

from keprix.proxy.config import ProxyConfig, RouteConfig
from keprix.proxy.injector import CredentialInjector
from keprix.proxy.paths import local_vault_path, rotation_state_path
from keprix.proxy.rotation import write_rotation_signal


def test_verified_bad_rotation_keeps_previous_secret(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    config = ProxyConfig(
        routes=[
            RouteConfig(
                host="api.example.com",
                header_name="Authorization",
                secret_ref="example-key",
                cache={"ttl": "60s"},
            )
        ]
    )
    local_vault_path().write_text(json.dumps({"secrets": {"example-key": "good-old"}}), encoding="utf-8")
    injector = CredentialInjector(config)
    assert injector.inject_headers("api.example.com", {})["Authorization"] == "good-old"

    local_vault_path().write_text(json.dumps({"secrets": {"example-key": "bad-new"}}), encoding="utf-8")
    write_rotation_signal("example-key", verify=True)

    assert injector.inject_headers("api.example.com", {})["Authorization"] == "good-old"
    state = json.loads(rotation_state_path().read_text(encoding="utf-8"))
    assert state["events"][0]["status"] == "failed"
