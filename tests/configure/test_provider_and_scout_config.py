"""Wave 2 provider + scout conversational config tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.configure.provider_requirements import (
    find_provider_by_alias,
    get_sensitive_provider_field_keys,
    validate_provider_credentials,
)
from keprix.tools.provider_config_tool import provider_config_tool
from toolsets import resolve_toolset


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "keprix-home"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_ENV_FILE", str(home / ".env"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("KEPRIX_DEFAULT_PROVIDER", raising=False)
    (home / ".env").write_text("", encoding="utf-8")
    return home


def test_provider_aliases():
    assert find_provider_by_alias("OpenAI").id == "openai"
    assert find_provider_by_alias("gpt").id == "openai"
    assert find_provider_by_alias("claude").id == "anthropic"
    assert find_provider_by_alias("deepseek") is not None


def test_sensitive_provider_keys():
    keys = get_sensitive_provider_field_keys()
    assert "api_key" in keys


def test_validate_openai_requires_key():
    ok, msg, _ = validate_provider_credentials("openai", {})
    assert ok is False
    assert "api_key" in msg


def test_provider_config_in_core_toolsets():
    for name in ("keprix-cli", "keprix-telegram", "keprix-api-server"):
        tools = resolve_toolset(name)
        assert "provider_config" in tools, name
        assert "scout_config" in tools, name


def test_provider_collect_flow(isolated_home: Path, monkeypatch: pytest.MonkeyPatch):
    start = json.loads(provider_config_tool("collect", provider_id="openai"))
    assert start["ok"] is True
    assert start["complete"] is False
    assert start["next_field"]["key"] == "api_key"

    secret = "sk-test-live-secret-value-123456"
    done = json.loads(
        provider_config_tool(
            "collect",
            provider_id="gpt",
            credentials={"api_key": secret},
        )
    )
    assert done["ok"] is True
    assert done.get("complete") is True
    assert done["id"] == "openai"
    assert secret not in json.dumps(done)
    env_text = (isolated_home / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=" in env_text


def test_scout_requirements_and_collect_partial():
    from keprix.tools.scout_config_tool import scout_config_tool

    req = json.loads(scout_config_tool("requirements"))
    assert req["ok"] is True
    assert req["next_field"]["key"] == "provider_endpoint"

    step = json.loads(
        scout_config_tool(
            "collect",
            credentials={"provider_endpoint": "https://console.example.com"},
            session_id="test-scout",
        )
    )
    assert step["ok"] is True
    assert step["complete"] is False
    assert step["next_field"]["key"] == "api_key"
