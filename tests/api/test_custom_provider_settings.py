"""Tests for custom provider CRUD and provider disconnect."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api import custom_provider_settings, provider_settings
from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("custom_providers: []\n", encoding="utf-8")
    env_path = tmp_path / ".env"
    env_path.write_text("KEPRIX_ADMIN_PASSWORD=admin-pass\n", encoding="utf-8")

    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(env_path))
    monkeypatch.setattr("keprix_cli.config.get_config_path", lambda: config_path)
    monkeypatch.setattr("keprix.api.provider_settings._resolve_env_file", lambda: env_path)
    provider_settings.get_admin_provider_specs.cache_clear()
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, config_path, env_path


def test_custom_provider_crud(admin_client):
    client, config_path, _env_path = admin_client

    created = client.post(
        "/api/settings/custom-providers",
        json={
            "name": "Local Ollama",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "default_model": "llama3.2",
        },
    )
    assert created.status_code == 200
    provider = created.json()["provider"]
    assert provider["name"] == "Local Ollama"
    assert provider["connected"] is True
    provider_id = provider["id"]

    listed = client.get("/api/settings")
    assert listed.status_code == 200
    custom_items = listed.json()["custom_providers"]
    assert any(item["id"] == provider_id for item in custom_items)

    updated = client.put(
        f"/api/settings/custom-providers/{provider_id}",
        json={"default_model": "mistral"},
    )
    assert updated.status_code == 200
    assert updated.json()["provider"]["default_model"] == "mistral"

    deleted = client.delete(f"/api/settings/custom-providers/{provider_id}")
    assert deleted.status_code == 200
    assert "Local Ollama" in config_path.read_text(encoding="utf-8") or "custom_providers: []" in config_path.read_text(encoding="utf-8")


def test_delete_builtin_provider_clears_env(admin_client, monkeypatch):
    client, _config_path, env_path = admin_client
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    provider_settings._upsert_env_file(env_path, "DEEPSEEK_API_KEY", "sk-test")

    response = client.delete("/api/settings/providers/deepseek")
    assert response.status_code == 200
    assert response.json()["provider"]["connected"] is False
    assert "DEEPSEEK_API_KEY=" not in env_path.read_text(encoding="utf-8")


def test_set_default_provider(admin_client, monkeypatch):
    client, _config_path, env_path = admin_client

    response = client.post(
        "/api/settings/default-provider",
        json={"provider_id": "custom/local-ollama"},
    )
    assert response.status_code == 200
    assert response.json()["default_provider"] == "custom/local-ollama"
    assert "KEPRIX_DEFAULT_PROVIDER=custom/local-ollama" in env_path.read_text(encoding="utf-8")


def test_custom_provider_module_roundtrip(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("custom_providers: []\n", encoding="utf-8")
    monkeypatch.setattr("keprix_cli.config.get_config_path", lambda: config_path)

    created = custom_provider_settings.create_custom_provider(
        name="RunPod",
        base_url="https://api.runpod.ai/v1",
        api_key="rp-test",
        default_model="meta-llama/Meta-Llama-3-8B-Instruct",
    )
    assert created["id"] == "runpod"

    updated = custom_provider_settings.update_custom_provider("runpod", default_model="llama-3")
    assert updated["default_model"] == "llama-3"

    items = custom_provider_settings.list_custom_providers()
    assert len(items) == 1

    deleted = custom_provider_settings.delete_custom_provider("runpod")
    assert deleted["name"] == "RunPod"
    assert custom_provider_settings.list_custom_providers() == []
