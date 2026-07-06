"""Tests for channel slash adapters and renderers."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import time
from pathlib import Path

import pytest

from keprix.slash.audit import SlashAuditStore
from keprix.slash.confirmations import SlashConfirmationStore
from keprix.slash.renderers import render_discord, render_telegram, render_slack
from keprix.slash.schemas import SlashResult


def _load_gateway_module(name: str):
    path = Path(__file__).resolve().parents[2] / "src" / "keprix" / "gateway" / "slash" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"gateway_slash_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def audit_store(tmp_path, monkeypatch):
    store = SlashAuditStore(base_dir=tmp_path / "slash")
    monkeypatch.setattr("keprix.slash.audit.get_slash_audit_store", lambda: store)
    monkeypatch.setattr("keprix.slash.executor.get_slash_audit_store", lambda: store)
    return store


@pytest.fixture
def confirm_store(monkeypatch):
    store = SlashConfirmationStore()
    monkeypatch.setattr("keprix.slash.confirmations.get_confirmation_store", lambda: store)
    monkeypatch.setattr("keprix.slash.executor.get_confirmation_store", lambda: store)
    return store


def test_telegram_renders_inline_keyboard():
    result = SlashResult(ok=True, message="confirm?", requires_confirmation=True, confirmation_token="tok123")
    payload = render_telegram(result)
    assert "reply_markup" in payload
    assert payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"].endswith("tok123")


def test_discord_ephemeral_sensitive():
    result = SlashResult(ok=True, message="secret", ephemeral=True)
    payload = render_discord(result)
    assert payload["ephemeral"] is True


@pytest.mark.asyncio
async def test_discord_carina_prefix(audit_store):
    discord = _load_gateway_module("discord")
    payload = await discord.handle_discord_slash(
        text="/carina status",
        user_id="d1",
        workspace_id="ws",
        channel_id="c1",
        role="admin",
    )
    assert "content" in payload


def test_slack_invalid_signature_rejected():
    slack = _load_gateway_module("slack")
    body = b"command=/status"
    ts = str(int(time.time()))
    assert slack.verify_slack_signature(
        signing_secret="secret",
        timestamp=ts,
        body=body,
        signature="v0=deadbeef",
    ) is False


def test_slack_valid_signature():
    slack = _load_gateway_module("slack")
    secret = "secret"
    body = b"command=/status"
    ts = str(int(time.time()))
    base = f"v0:{ts}:{body.decode('utf-8')}"
    digest = hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
    assert slack.verify_slack_signature(
        signing_secret=secret,
        timestamp=ts,
        body=body,
        signature=f"v0={digest}",
    ) is True


def test_slack_ephemeral_preview():
    result = SlashResult(ok=True, message="preview", requires_confirmation=True, confirmation_token="abc")
    payload = render_slack(result)
    assert payload["response_type"] == "ephemeral"


@pytest.mark.asyncio
async def test_telegram_status(audit_store):
    telegram = _load_gateway_module("telegram")
    payload = await telegram.handle_telegram_slash(
        text="/status",
        user_id="t1",
        workspace_id="ws",
        chat_id="chat1",
        role="admin",
    )
    assert "text" in payload
