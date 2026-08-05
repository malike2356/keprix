"""Channel Shield core + adapter fixture tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.channel_shield.config import reset_channel_shield_config
from keprix.channel_shield.doctor import run_e2e, run_e2e_matrix
from keprix.channel_shield.pipeline import EICAR, run_pipeline
from keprix.channel_shield.scout_bridge import honour_scout_command
from keprix.channel_shield.store import get_channel_shield_store, reset_channel_shield_store
from keprix.channel_shield.types import CHANNELS, ShieldEnvelope, Verdict


@pytest.fixture(autouse=True)
def _reset():
    reset_channel_shield_store()
    reset_channel_shield_config()
    yield
    reset_channel_shield_store()
    reset_channel_shield_config()


def test_envelope_roundtrip():
    env = ShieldEnvelope(
        channel="email",
        protection_id="p1",
        external_message_id="m1",
        conversation_id="c1",
        from_addr="a@b.com",
        to_addrs=["c@d.com"],
        text="hello https://example.com",
        links=["https://example.com"],
    )
    restored = ShieldEnvelope.from_dict(env.to_dict())
    assert restored.channel == "email"
    assert restored.external_message_id == "m1"
    assert restored.links == ["https://example.com"]


def test_pipeline_clean():
    env = ShieldEnvelope(
        channel="email",
        protection_id="p1",
        external_message_id="m1",
        conversation_id="",
        from_addr="a@b.com",
        to_addrs=["c@d.com"],
        text="Hello team, notes from yesterday.",
        subject="Notes",
        auth_signals={"spf": "pass", "dkim": "pass", "dmarc": "pass"},
    )
    report = run_pipeline(env)
    assert report.verdict == Verdict.CLEAN


def test_pipeline_eicar_malicious():
    env = ShieldEnvelope(
        channel="email",
        protection_id="p1",
        external_message_id="m2",
        conversation_id="",
        from_addr="evil@x.com",
        to_addrs=["c@d.com"],
        text="Urgent action required",
        subject="Invoice",
    )
    from keprix.channel_shield.types import ShieldAttachment

    att = ShieldAttachment(
        id="a1",
        filename="invoice.exe",
        content_type="application/octet-stream",
        size=len(EICAR),
        sha256="x",
        storage_uri="shield://att/a1",
        extension="exe",
    )
    env.attachments = [att]
    report = run_pipeline(env, attachment_bytes={"a1": EICAR})
    assert report.verdict == Verdict.MALICIOUS


def test_fail_closed_on_sandbox_error():
    from keprix.channel_shield.config import ChannelShieldConfig
    from keprix.channel_shield.types import ShieldAttachment

    env = ShieldEnvelope(
        channel="web",
        protection_id="p1",
        external_message_id="m3",
        conversation_id="c",
        from_addr="u",
        to_addrs=[],
        text="file",
    )
    att = ShieldAttachment(
        id="a1",
        filename="dropper.exe",
        content_type="application/octet-stream",
        size=4,
        sha256="x",
        storage_uri="shield://att/a1",
        extension="exe",
    )
    env.attachments = [att]
    cfg = ChannelShieldConfig(enabled=True, fail_closed_default=True)

    def boom(_att, _data):
        raise RuntimeError("sandbox down")

    report = run_pipeline(env, cfg=cfg, attachment_bytes={"a1": b"test"}, sandbox_runner=boom)
    assert report.verdict in {Verdict.ERROR, Verdict.MALICIOUS, Verdict.SUSPECT}


def test_scout_honour_command():
    result = honour_scout_command("quarantine", {"tool": "channel_shield"})
    assert result["honoured"] is True


def test_runtime_enabled_honours_explicit_feature_manager_override(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    feature_file = tmp_path / "feature_flags.json"
    feature_file.write_text('{"channel_shield": true}', encoding="utf-8")

    import keprix.feature_flags.store as flag_store

    monkeypatch.setattr(flag_store, "_flags_path", lambda: feature_file)
    monkeypatch.delenv("CHANNEL_SHIELD_ENABLED", raising=False)
    reset_channel_shield_config()

    from keprix.channel_shield.config import load_channel_shield_config

    assert load_channel_shield_config(force=True).enabled is True


def test_runtime_enabled_safe_default_and_env_precedence(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    feature_file = tmp_path / "feature_flags.json"
    feature_file.write_text("{}", encoding="utf-8")

    import keprix.feature_flags.store as flag_store
    from keprix.channel_shield.config import load_channel_shield_config

    monkeypatch.setattr(flag_store, "_flags_path", lambda: feature_file)
    monkeypatch.delenv("CHANNEL_SHIELD_ENABLED", raising=False)
    reset_channel_shield_config()
    assert load_channel_shield_config(force=True).enabled is False

    feature_file.write_text('{"channel_shield": true}', encoding="utf-8")
    monkeypatch.setenv("CHANNEL_SHIELD_ENABLED", "false")
    reset_channel_shield_config()
    assert load_channel_shield_config(force=True).enabled is False


@pytest.mark.asyncio
async def test_api_protection_crud_and_ingest_clean():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/channel-shield/protections",
            json={
                "channel": "email",
                "label": "Example domain",
                "protection_key": "example.com",
            },
        )
        assert created.status_code == 201
        protection_id = created.json()["id"]

        ingest = await client.post(
            "/api/channel-shield/ingest",
            json={
                "channel": "email",
                "protection_id": protection_id,
                "payload": {
                    "from": "alice@example.com",
                    "to": ["bob@example.com"],
                    "subject": "Hi",
                    "text": "Hello friend",
                    "message_id": "api-clean-1",
                },
            },
        )
        assert ingest.status_code == 200
        body = ingest.json()
        assert body["message"]["verdict"] == "clean"
        assert body["action"]["decision"] == "deliver"


@pytest.mark.asyncio
async def test_api_malicious_quarantine_and_email_alias():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/channel-shield/protections",
            json={"channel": "email", "label": "d", "protection_key": "d.com"},
        )
        protection_id = created.json()["id"]
        ingest = await client.post(
            "/api/email-shield/ingest",
            json={
                "channel": "slack",  # alias forces email in handler
                "protection_id": protection_id,
                "payload": {
                    "from": "evil@x.com",
                    "to": ["bob@d.com"],
                    "subject": "Urgent action required",
                    "text": "verify your account http://evil.xyz/x",
                    "attachments": [
                        {
                            "filename": "invoice.exe",
                            "data": EICAR.decode("latin-1"),
                            "extension": "exe",
                        }
                    ],
                },
            },
        )
        assert ingest.status_code == 200
        body = ingest.json()
        assert body["action"]["decision"] == "quarantine"
        assert body["message"]["safe_summary"]
        assert body["message"]["channel"] == "email"

        msg_id = body["message"]["id"]
        destroy = await client.post(
            f"/api/channel-shield/messages/{msg_id}/destroy",
            headers={"x-admin": "true"},
        )
        assert destroy.status_code == 200


@pytest.mark.asyncio
async def test_malicious_release_requires_admin():
    store = get_channel_shield_store()
    prot = await store.create_protection(
        "local", channel="slack", label="t", protection_key="T1"
    )
    from keprix.channel_shield.adapters.registry import get_adapter
    from keprix.channel_shield.service import get_channel_shield_service

    adapter = get_adapter("slack")
    payload = {
        "event": {
            "type": "message",
            "text": "Urgent action required http://evil.xyz",
            "user": "U",
            "channel": "C",
            "ts": "9.9",
            "files": [{"name": "x.exe", "data": EICAR}],
        }
    }
    env, raw, atts = adapter.ingest(payload, protection_id=prot.id, auth_signals={"signed": True})
    result = await get_channel_shield_service().process_envelope(
        "local", env, raw_bytes=raw, attachment_bytes=atts
    )
    msg_id = result["message"]["id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post(f"/api/channel-shield/messages/{msg_id}/release")
        assert denied.status_code == 403
        allowed = await client.post(
            f"/api/channel-shield/messages/{msg_id}/release",
            headers={"x-admin": "true"},
        )
        assert allowed.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", list(CHANNELS))
async def test_adapter_e2e_matrix_item(channel: str):
    result = await run_e2e(channel)
    assert result["ok"] is True, result
    assert result["clean"]["decision"] == "deliver"
    assert result["malicious"]["decision"] == "quarantine"
    assert result["malicious"]["safe_summary"]


@pytest.mark.asyncio
async def test_full_matrix():
    matrix = await run_e2e_matrix()
    assert matrix["ok"] is True
    assert set(matrix["results"].keys()) == set(CHANNELS)


@pytest.mark.asyncio
async def test_adapters_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/channel-shield/adapters")
    assert response.status_code == 200
    data = response.json()
    assert set(data["adapters"]) == set(CHANNELS)
