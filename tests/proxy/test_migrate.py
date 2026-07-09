"""Tests for vault migration from Keprix .env."""

from __future__ import annotations

import json

from keprix.proxy.config import load_proxy_config
from keprix.proxy.migrate import migrate_vault_from_env
from keprix.proxy.paths import local_vault_path


def test_migrate_vault_from_env_copies_keys_and_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    env_path = tmp_path / ".env"
    env_path.write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nOPENAI_API_KEY=sk-openai-test\n",
        encoding="utf-8",
    )

    result = migrate_vault_from_env(env_path)

    assert "ANTHROPIC_API_KEY" in result.migrated
    assert "OPENAI_API_KEY" in result.migrated
    vault = json.loads(local_vault_path().read_text(encoding="utf-8"))
    assert vault["secrets"]["anthropic-api-key"] == "sk-ant-test"
    assert vault["secrets"]["openai-api-key"] == "sk-openai-test"
    config = load_proxy_config()
    hosts = {route.host for route in config.routes}
    assert "api.anthropic.com" in hosts
    assert "api.openai.com" in hosts


def test_migrate_skips_dummy_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    env_path = tmp_path / ".env"
    env_path.write_text("ANTHROPIC_API_KEY=dummy-replaced-by-proxy\n", encoding="utf-8")

    result = migrate_vault_from_env(env_path)

    assert "ANTHROPIC_API_KEY" in result.skipped
