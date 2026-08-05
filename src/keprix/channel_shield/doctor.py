"""Doctor and fixture E2E helpers for Channel Shield CLI."""

from __future__ import annotations

from typing import Any

from keprix.channel_shield.adapters.registry import adapters_health, list_adapters
from keprix.channel_shield.config import config_to_dict, load_channel_shield_config
from keprix.channel_shield.pipeline import EICAR
from keprix.channel_shield.scout_bridge import scout_configured
from keprix.channel_shield.service import get_channel_shield_service
from keprix.channel_shield.store import get_channel_shield_store
from keprix.channel_shield.types import CHANNELS, Verdict


async def run_doctor() -> dict[str, Any]:
    cfg = load_channel_shield_config()
    health = await adapters_health()
    checks = [
        {"id": "config_loaded", "ok": True, "detail": config_to_dict(cfg)},
        {"id": "adapters_registered", "ok": len(list_adapters()) == len(CHANNELS)},
        {
            "id": "adapter_health",
            "ok": all(h.get("ok") for h in health),
            "detail": health,
        },
        {
            "id": "fail_closed_default",
            "ok": cfg.fail_closed_default is True,
            "detail": cfg.fail_closed_default,
        },
        {
            "id": "scout_optional",
            "ok": True,
            "detail": {"configured": scout_configured(), "emit": cfg.scout_emit_signals},
        },
        {
            "id": "raw_store_dir",
            "ok": bool(cfg.raw_store_dir),
            "detail": cfg.raw_store_dir,
        },
    ]
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


async def run_e2e(channel: str, *, user_id: str = "local") -> dict[str, Any]:
    if channel not in CHANNELS:
        return {"ok": False, "error": f"unknown channel: {channel}"}

    store = get_channel_shield_store()
    service = get_channel_shield_service()
    from keprix.channel_shield.adapters.registry import get_adapter

    protection = await store.create_protection(
        user_id,
        channel=channel,
        label=f"e2e-{channel}",
        protection_key=f"e2e-{channel}",
        config={"e2e": True},
    )
    adapter = get_adapter(channel)

    clean_payload = _clean_fixture(channel)
    env_clean, raw_clean, att_clean = adapter.ingest(
        clean_payload, protection_id=protection.id, auth_signals={"signed": True, "mode": "e2e"}
    )
    clean_result = await service.process_envelope(
        user_id, env_clean, raw_bytes=raw_clean, attachment_bytes=att_clean
    )

    bad_payload = _malicious_fixture(channel)
    env_bad, raw_bad, att_bad = adapter.ingest(
        bad_payload, protection_id=protection.id, auth_signals={"signed": True, "mode": "e2e"}
    )
    bad_result = await service.process_envelope(
        user_id, env_bad, raw_bytes=raw_bad, attachment_bytes=att_bad
    )

    clean_ok = clean_result["message"]["verdict"] == Verdict.CLEAN.value
    clean_delivered = clean_result["action"]["decision"] == "deliver"
    bad_held = bad_result["action"]["decision"] == "quarantine"
    bad_not_delivered = bad_result["message"]["status"] == "quarantined"
    summary_ok = bool(bad_result["message"].get("safe_summary"))

    return {
        "ok": clean_ok and clean_delivered and bad_held and bad_not_delivered and summary_ok,
        "channel": channel,
        "clean": {
            "verdict": clean_result["message"]["verdict"],
            "decision": clean_result["action"]["decision"],
        },
        "malicious": {
            "verdict": bad_result["message"]["verdict"],
            "decision": bad_result["action"]["decision"],
            "safe_summary": bad_result["message"].get("safe_summary"),
        },
        "scout_configured": scout_configured(),
    }


async def run_e2e_matrix() -> dict[str, Any]:
    results = {}
    for channel in CHANNELS:
        results[channel] = await run_e2e(channel)
    return {
        "ok": all(r.get("ok") for r in results.values()),
        "results": results,
    }


def _clean_fixture(channel: str) -> dict[str, Any]:
    base = {
        "text": "Hello, meeting notes attached as a reminder only.",
        "from": "alice@example.com",
        "to": ["bob@example.com"],
        "subject": "Meeting notes",
        "message_id": f"clean-{channel}",
        "conversation_id": f"conv-{channel}",
    }
    if channel == "slack":
        return {"event": {"type": "message", "text": base["text"], "user": "U1", "channel": "C1", "ts": "1.1"}}
    if channel == "teams":
        return {"text": base["text"], "from": {"id": "user1"}, "conversation": {"id": "conv1"}, "id": "m1"}
    if channel == "telegram":
        return {"message": {"message_id": 1, "text": base["text"], "from": {"id": 1}, "chat": {"id": 2}}}
    if channel == "whatsapp":
        return {"text": {"body": base["text"]}, "from": "15551234567", "id": "wamid.1"}
    if channel == "discord":
        return {"content": base["text"], "author": {"id": "1"}, "channel_id": "2", "id": "3"}
    if channel == "sms":
        return {"Body": base["text"], "From": "+15550001", "To": "+15550002", "MessageSid": "SM1"}
    if channel == "web":
        return {**base, "conversation_id": "web-1"}
    return base


def _malicious_fixture(channel: str) -> dict[str, Any]:
    att = {
        "filename": "invoice.exe",
        "content_type": "application/octet-stream",
        "data": EICAR,
        "extension": "exe",
    }
    base = {
        "text": "Urgent action required: verify your account http://evil.xyz/login",
        "from": "attacker@evil.xyz",
        "to": ["bob@example.com"],
        "subject": "Urgent wire transfer",
        "message_id": f"bad-{channel}",
        "conversation_id": f"conv-bad-{channel}",
        "attachments": [att],
    }
    if channel == "slack":
        return {
            "event": {
                "type": "message",
                "text": base["text"],
                "user": "U2",
                "channel": "C1",
                "ts": "2.2",
                "files": [{"id": "F1", "name": "invoice.exe", "mimetype": "application/octet-stream", "data": EICAR}],
            }
        }
    if channel == "teams":
        return {
            "text": base["text"],
            "from": {"id": "bad"},
            "conversation": {"id": "c"},
            "id": "bad1",
            "attachments": [{"name": "invoice.exe", "contentType": "application/octet-stream", "data": EICAR}],
        }
    if channel == "telegram":
        return {
            "message": {
                "message_id": 9,
                "caption": base["text"],
                "from": {"id": 9},
                "chat": {"id": 2},
                "document": {"file_name": "invoice.exe", "mime_type": "application/octet-stream", "data": EICAR},
            }
        }
    if channel == "whatsapp":
        return {
            "text": {"body": base["text"]},
            "from": "15559999",
            "id": "wamid.bad",
            "document": {"filename": "invoice.exe", "mime_type": "application/octet-stream", "data": EICAR},
        }
    if channel == "discord":
        return {
            "content": base["text"],
            "author": {"id": "9"},
            "channel_id": "2",
            "id": "bad",
            "attachments": [{"filename": "invoice.exe", "content_type": "application/octet-stream", "data": EICAR}],
        }
    if channel == "sms":
        return {
            "Body": base["text"],
            "From": "+15559999",
            "To": "+15550002",
            "MessageSid": "SMbad",
            "attachments": [att],
        }
    if channel == "web":
        return base
    return base
