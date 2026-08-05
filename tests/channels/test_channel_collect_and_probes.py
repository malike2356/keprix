"""Tests for BotFather collect sessions and extra probes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.channels.channel_probes import (
    _probe_teams,
    _probe_whatsapp,
    _probe_whatsapp_cloud,
)
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


@pytest.mark.asyncio
async def test_whatsapp_probe_requires_enabled():
    ok, msg, _ = await _probe_whatsapp({"enabled": "false"})
    assert ok is False
    ok, msg, meta = await _probe_whatsapp({"enabled": "true"})
    assert ok is True
    assert meta.get("needs_pairing") is True


@pytest.mark.asyncio
async def test_teams_probe_missing_fields():
    ok, msg, _ = await _probe_teams({"client_id": "x"})
    assert ok is False
    assert "Missing" in msg


@pytest.mark.asyncio
async def test_whatsapp_cloud_probe_missing_fields():
    ok, msg, _ = await _probe_whatsapp_cloud({"access_token": "tok"})
    assert ok is False


def test_collect_one_field_at_a_time(isolated_home: Path, monkeypatch: pytest.MonkeyPatch):
    async def _fake_test(channel_id: str):
        return {"success": True, "message": "ok (mocked)", "meta": {}}

    monkeypatch.setattr("keprix.channels.channel_probes.test_channel", _fake_test)

    start = json.loads(channel_config_tool("collect", channel_id="telegram"))
    assert start["ok"] is True
    assert start["complete"] is False
    assert start["next_field"]["key"] == "bot_token"

    secret = "123456789:LIVESECRETTOKENVALUEHERE99"
    done = json.loads(
        channel_config_tool(
            "collect",
            channel_id="tg",
            credentials={"bot_token": secret},
        )
    )
    assert done["ok"] is True
    assert done.get("complete") is True
    assert done["id"] == "telegram"
    assert secret not in json.dumps(done)


def test_collect_email_steps(isolated_home: Path, monkeypatch: pytest.MonkeyPatch):
    async def _fake_test(channel_id: str):
        return {"success": True, "message": "email ok", "meta": {}}

    monkeypatch.setattr("keprix.channels.channel_probes.test_channel", _fake_test)

    step = json.loads(channel_config_tool("collect", channel_id="smtp"))
    assert step["next_field"]["key"] == "address"

    for key, value in [
        ("address", "agent@example.com"),
        ("password", "app-password-value"),
        ("imap_host", "imap.example.com"),
        ("smtp_host", "smtp.example.com"),
    ]:
        step = json.loads(
            channel_config_tool("collect", channel_id="email", credentials={key: value})
        )

    assert step.get("complete") is True
    assert step["id"] == "email"
    assert "app-password-value" not in json.dumps(step)
