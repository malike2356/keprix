"""Durable store + real egress tests for Channel Shield."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.channel_shield.adapters.registry import get_adapter
from keprix.channel_shield.config import reset_channel_shield_config
from keprix.channel_shield.durable import DurableBackend
from keprix.channel_shield.egress import http_json, slack_post_message, telegram_send_message
from keprix.channel_shield.store import ChannelShieldStore, reset_channel_shield_store
from keprix.channel_shield.types import ShieldEnvelope


@pytest.fixture(autouse=True)
def _reset():
    reset_channel_shield_store()
    reset_channel_shield_config()
    yield
    reset_channel_shield_store()
    reset_channel_shield_config()


@pytest.mark.asyncio
async def test_sqlite_durable_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "shield.db"
    monkeypatch.setenv("CHANNEL_SHIELD_SQLITE_PATH", str(db))
    monkeypatch.delenv("CHANNEL_SHIELD_STORE", raising=False)

    store = ChannelShieldStore(durable=True)
    store._backend = DurableBackend(path=db)
    prot = await store.create_protection(
        "u1", channel="email", label="mail", protection_key="example.com"
    )
    env = ShieldEnvelope(
        channel="email",
        protection_id=prot.id,
        external_message_id="m1",
        conversation_id="",
        from_addr="a@b.com",
        to_addrs=["c@d.com"],
        text="hello durable",
        subject="Hi",
    )
    msg = await store.ingest_envelope("u1", env)
    await store.update_message(msg.id, status="quarantined", verdict="suspect")

    store2 = ChannelShieldStore(durable=True)
    store2._backend = DurableBackend(path=db)
    await store2.ensure_loaded()
    loaded = await store2.get_message(msg.id)
    assert loaded is not None
    assert loaded.text_preview.startswith("hello")
    assert loaded.status == "quarantined"
    prots = await store2.list_protections("u1")
    assert len(prots) == 1
    assert prots[0].protection_key == "example.com"


@pytest.mark.asyncio
async def test_egress_queues_without_credentials(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    slack = await slack_post_message(channel="C1", text="hi")
    assert slack.get("queued") is True
    tg = await telegram_send_message(chat_id="1", text="hi")
    assert tg.get("queued") is True


@pytest.mark.asyncio
async def test_adapters_notify_without_credentials():
    for channel in ("slack", "telegram", "discord", "whatsapp", "sms", "teams", "web"):
        adapter = get_adapter(channel)
        env = ShieldEnvelope(
            channel=channel,
            protection_id="p",
            external_message_id="e",
            conversation_id="c1",
            from_addr="u",
            to_addrs=["t"],
            text="x",
        )
        result = await adapter.notify_safe_summary(env, "mid", "safe summary")
        assert result["channel"] == channel
        assert "summary" in result or result.get("ok") is not None


@pytest.mark.asyncio
async def test_http_json_handles_unreachable():
    result = await http_json("GET", "http://127.0.0.1:1/", timeout=0.2)
    assert result["ok"] is False
