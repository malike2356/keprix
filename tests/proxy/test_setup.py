"""Tests for credential proxy setup wizard."""

from __future__ import annotations

import json

from keprix.proxy.config import load_proxy_config
from keprix.proxy.paths import local_vault_path, proxy_config_path
from keprix.proxy.setup_wizard import run_setup_wizard


def test_setup_wizard_writes_config_routes_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")

    config = run_setup_wizard(vault="keychain", interactive=False)

    assert proxy_config_path().is_file()
    assert len(config.routes) == 3
    assert load_proxy_config().vault == "keychain"
    assert local_vault_path().is_file()
    vault = json.loads(local_vault_path().read_text(encoding="utf-8"))
    assert vault["secrets"]["anthropic-api-key"] == "anthropic-test-key"
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "HTTPS_PROXY=" in env_text
    assert "dummy-replaced-by-proxy" in env_text
