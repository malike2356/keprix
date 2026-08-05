"""WhatsApp Cloud API Channel Shield adapter."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class WhatsAppAdapter(ChannelAdapter):
    channel = "whatsapp"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        secret = os.environ.get("WHATSAPP_APP_SECRET", "").strip()
        sig = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256") or ""
        if not secret:
            return {"signed": False, "mode": "fixture"}
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return {"signed": hmac.compare_digest(expected, sig), "mode": "cloud_api"}

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
        # Flatten Cloud API webhook structure or accept fixture
        msg = payload
        if "entry" in payload:
            try:
                changes = payload["entry"][0]["changes"][0]["value"]
                messages = changes.get("messages") or []
                msg = messages[0] if messages else changes
                msg = {**msg, "phone_number_id": (changes.get("metadata") or {}).get("phone_number_id")}
            except (IndexError, KeyError, TypeError):
                msg = payload
        attachments = []
        for key in ("image", "document", "audio", "video"):
            media = msg.get(key)
            if isinstance(media, dict):
                attachments.append(
                    {
                        "filename": media.get("filename") or f"{key}.bin",
                        "content_type": media.get("mime_type") or "application/octet-stream",
                        "data": media.get("data") or b"",
                        "id": media.get("id"),
                    }
                )
        text = ""
        if isinstance(msg.get("text"), dict):
            text = str(msg["text"].get("body") or "")
        else:
            text = str(msg.get("text") or msg.get("body") or "")
        normalized = {
            "text": text,
            "from": str(msg.get("from") or ""),
            "conversation_id": str(msg.get("from") or msg.get("phone_number_id") or ""),
            "external_message_id": str(msg.get("id") or ""),
            "attachments": attachments,
            "metadata": {
                "phone_number_id": msg.get("phone_number_id") or payload.get("phone_number_id"),
            },
        }
        return build_text_envelope(
            "whatsapp", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import whatsapp_send_text

        phone_id = str((envelope.metadata or {}).get("phone_number_id") or "")
        result = await whatsapp_send_text(
            to=envelope.conversation_id or (envelope.to_addrs[0] if envelope.to_addrs else ""),
            text=envelope.text or f"Released message {message_id}",
            phone_number_id=phone_id or None,
        )
        return {
            "channel": "whatsapp",
            "message_id": message_id,
            "to": envelope.conversation_id,
            "note": "Session/template rules still apply for outbound.",
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import whatsapp_send_text

        phone_id = str((envelope.metadata or {}).get("phone_number_id") or "")
        result = await whatsapp_send_text(
            to=envelope.conversation_id or (envelope.to_addrs[0] if envelope.to_addrs else ""),
            text=summary[:900],
            phone_number_id=phone_id or None,
        )
        return {
            "channel": "whatsapp",
            "message_id": message_id,
            "to": envelope.conversation_id,
            "summary": summary[:900],
            **result,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "whatsapp",
            "ok": True,
            "token_configured": bool(
                os.environ.get("WHATSAPP_TOKEN") or os.environ.get("WHATSAPP_ACCESS_TOKEN")
            ),
        }
