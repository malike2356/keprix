"""Tests for admin provider settings discovery."""

from __future__ import annotations

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
