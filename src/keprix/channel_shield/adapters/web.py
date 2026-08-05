"""Web chat / embed Channel Shield adapter."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class WebAdapter(ChannelAdapter):
    channel = "web"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        origin = headers.get("origin") or headers.get("Origin") or ""
        allowed = os.environ.get("CHANNEL_SHIELD_WEB_ORIGINS", "").strip()
        public_key = headers.get("x-embed-key") or headers.get("X-Embed-Key") or ""
        expected_key = os.environ.get("CHANNEL_SHIELD_WEB_EMBED_KEY", "").strip()
        if expected_key and public_key == expected_key:
            return {"signed": True, "mode": "embed_key", "origin": origin}
        if allowed and origin:
            hosts = {h.strip() for h in allowed.split(",") if h.strip()}
            host = urlparse(origin).netloc
            if host in hosts or origin in hosts:
                return {"signed": True, "mode": "cors_origin", "origin": origin}
            return {"signed": False, "mode": "cors_origin", "origin": origin}
        return {"signed": False, "mode": "fixture", "origin": origin}

    def ingest(
        self,
        payload: dict[str, Any] | bytes,
        *,
        protection_id: str,
        auth_signals: dict[str, Any] | None = None,
    ) -> tuple[ShieldEnvelope, bytes | None, dict[str, bytes]]:
        if isinstance(payload, bytes):
            import json

            payload = json.loads(payload.decode("utf-8"))
        assert isinstance(payload, dict)
        return build_text_envelope(
            "web", protection_id, payload, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import web_callback

        callback = str((envelope.metadata or {}).get("callback_url") or "")
        result = await web_callback(
            callback_url=callback,
            payload={
                "type": "channel_shield.deliver",
                "messageId": message_id,
                "conversationId": envelope.conversation_id,
                "text": envelope.text,
            },
        )
        if not callback:
            result = {"ok": True, "mode": "widget_allow", "queued": False}
        return {
            "channel": "web",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import web_callback

        callback = str((envelope.metadata or {}).get("callback_url") or "")
        result = await web_callback(
            callback_url=callback,
            payload={
                "type": "channel_shield.safe_summary",
                "messageId": message_id,
                "conversationId": envelope.conversation_id,
                "summary": summary,
            },
        )
        if not callback:
            result = {
                "ok": True,
                "mode": "widget_system_message",
                "queued": True,
                "summary": summary,
            }
        return {
            "channel": "web",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            "summary": summary,
            **result,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "web",
            "ok": True,
            "origins_configured": bool(os.environ.get("CHANNEL_SHIELD_WEB_ORIGINS")),
            "embed_key_configured": bool(os.environ.get("CHANNEL_SHIELD_WEB_EMBED_KEY")),
        }
