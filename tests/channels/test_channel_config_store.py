"""Tests for encrypted channel config store + tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.channels import channel_config_store as store
from keprix.tools.channel_config_tool import channel_config_tool


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "keprix-home"
    home.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.setenv("KEPRIX_CHANNEL_CONFIG_PATH", str(home / "channel_configurations.json"))
    monkeypatch.setenv("KEPRIX_ENV_PATH", str(home / ".env"))
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    return home


def test_save_list_remove_roundtrip(isolated_home: Path):
    saved = store.save_configuration("telegram", {"bot_token": "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"})
    assert saved["configured"] is True
    assert "TELEGRAM_BOT_TOKEN" in saved["env_keys_written"]

    rows = store.list_configurations(include_secrets=False)
    tg = next(r for r in rows if r["id"] == "telegram")
    assert tg["configured"] is True
    assert "credentials" not in tg

    creds = store.get_decrypted_credentials("telegram")
    assert creds["bot_token"].startswith("123456789:")

    env_text = (isolated_home / ".env").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN=" in env_text

    removed = store.remove_configuration("telegram")
    assert removed["ok"] is True
    assert store.get_decrypted_credentials("telegram") == {}


def test_channel_config_tool_list_and_configure(isolated_home: Path, monkeypatch: pytest.MonkeyPatch):
    async def _fake_test(channel_id: str):
        return {"success": True, "message": "ok (mocked)", "meta": {"bot_username": "@test_bot"}}

    monkeypatch.setattr(
        "keprix.channels.channel_probes.test_channel",
        _fake_test,
    )

    listed = json.loads(channel_config_tool("list"))
    assert any(c["id"] == "telegram" for c in listed["channels"])

    result = json.loads(
        channel_config_tool(
            "configure",
            channel_id="tg",
            credentials={"bot_token": "999:TESTTOKENVALUEHERE"},
        )
    )
    assert result["ok"] is True
    assert result["id"] == "telegram"
    assert "999:TESTTOKENVALUEHERE" not in json.dumps(result)
