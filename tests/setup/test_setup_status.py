"""Setup status snapshot tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.setup.status import model_configured, provider_configured, setup_status_snapshot


@pytest.fixture
def fresh_home(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    (tmp_path / "config.yaml").write_text("model: ''\n", encoding="utf-8")
    (tmp_path / ".env").write_text("", encoding="utf-8")
    return tmp_path


def test_fresh_install_reports_unconfigured(fresh_home):
    assert provider_configured() is False
    snapshot = setup_status_snapshot()
    assert snapshot["provider_configured"] is False
    assert snapshot["model_configured"] is False
    assert "wizard_sections" in snapshot
    assert snapshot["docs_url"].endswith("/getting-started/first-run")


def test_env_key_marks_provider_configured(fresh_home, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert provider_configured() is True
    snapshot = setup_status_snapshot()
    assert snapshot["provider_configured"] is True


def test_model_configured_when_provider_set(fresh_home):
    config_path = fresh_home / "config.yaml"
    config_path.write_text(
        "model:\n  provider: openai\n  default: gpt-4.1-mini\n",
        encoding="utf-8",
    )
    assert provider_configured() is True
    assert model_configured() is True


def test_setup_status_api(fresh_home, monkeypatch):
    monkeypatch.setattr(
        "keprix.setup.routes.setup_status_snapshot",
        lambda: {
            "provider_configured": False,
            "model_configured": False,
            "active_provider": None,
            "default_model": None,
            "wizard_sections": ["model"],
            "docs_url": "https://example.test/first-run",
        },
    )
    client = TestClient(create_app())
    response = client.get("/api/setup/status")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_configured"] is False
    assert isinstance(body.get("minimal_providers"), list)


def test_minimal_setup_api(fresh_home, monkeypatch):
    monkeypatch.setattr(
        "keprix.setup.routes.apply_minimal_setup",
        lambda **kwargs: {"ok": True, "status": {"provider_configured": True}},
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/setup/minimal",
        json={
            "provider": "openai",
            "api_key": "sk-test-openai",
            "model": "gpt-4.1-mini",
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
