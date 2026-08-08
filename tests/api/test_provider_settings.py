"""Tests for admin provider settings discovery."""

from __future__ import annotations

import os

from keprix.api import provider_settings


def test_provider_settings_snapshot_deepseek_configured(monkeypatch):
    monkeypatch.setenv("KEPRIX_DEFAULT_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(provider_settings, "_ollama_status", lambda: (False, None))

    snapshot = provider_settings.provider_settings_snapshot()

    assert snapshot["deepseek"]["connected"] is True
    assert snapshot["deepseek"]["default_model"] == "deepseek-chat"
    assert snapshot["deepseek"]["is_default"] is True
    assert snapshot["anthropic"]["connected"] is False
    assert snapshot["openai"]["connected"] is False


def test_admin_provider_catalog_lists_registry_providers():
    catalog = provider_settings.admin_provider_catalog()
    ids = {item["id"] for item in catalog}
    assert len(catalog) >= 20
    assert "deepseek" in ids
    assert "anthropic" in ids
    assert "openai" in ids
    assert "google" in ids
    assert "groq" in ids
    assert "xai" in ids


def test_persist_env_value_writes_keprix_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(env_file))
    monkeypatch.chdir(tmp_path)
    provider_settings.persist_env_value("DEEPSEEK_API_KEY", "sk-gui-test")
    assert env_file.read_text(encoding="utf-8").strip() == "DEEPSEEK_API_KEY=sk-gui-test"
    assert os.environ.get("DEEPSEEK_API_KEY") == "sk-gui-test"


def test_load_runtime_dotenv_prefers_keprix_home(monkeypatch, tmp_path):
    from keprix.api import server as api_server

    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("DEEPSEEK_API_KEY=sk-from-gui\nKEPRIX_DEFAULT_PROVIDER=deepseek\n", encoding="utf-8")
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(home / ".env"))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-compose-stale")
    api_server._load_runtime_dotenv()
    assert os.environ.get("DEEPSEEK_API_KEY") == "sk-from-gui"
    assert os.environ.get("KEPRIX_DEFAULT_PROVIDER") == "deepseek"
