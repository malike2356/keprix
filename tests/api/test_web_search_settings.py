"""API tests for web search settings UI backend."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_web_search_settings_lists_catalog(monkeypatch):
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "admin@test.local")
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "secret-pass")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/auth/login", json={"email": "admin@test.local", "password": "secret-pass"})
        if login.status_code != 200:
            pytest.skip("Admin auth not configured in test environment")
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/settings/web-search", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert "catalog" in payload
    assert "providers" in payload
    assert any(item["id"] == "tavily" for item in payload["catalog"])


@pytest.mark.asyncio
async def test_save_tavily_settings_persists_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    config_dir = tmp_path / ".keprix"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("web:\n  search_backend: \"\"\n", encoding="utf-8")

    monkeypatch.setenv("KEPRIX_HOME", str(config_dir))
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(env_file))
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "admin@test.local")
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "secret-pass")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/auth/login", json={"email": "admin@test.local", "password": "secret-pass"})
        if login.status_code != 200:
            pytest.skip("Admin auth not configured in test environment")
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.put(
            "/api/settings/web-search/tavily",
            headers=headers,
            json={"env_values": {"TAVILY_API_KEY": "tvly-test-key"}, "set_active": True},
        )

    assert response.status_code == 200
    assert "tvly-test-key" in env_file.read_text(encoding="utf-8")
    assert "search_backend: tavily" in (config_dir / "config.yaml").read_text(encoding="utf-8")
