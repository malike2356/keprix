"""SMS (Twilio-compatible) Channel Shield adapter."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class SmsAdapter(ChannelAdapter):
    channel = "sms"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        sig = headers.get("x-twilio-signature") or headers.get("X-Twilio-Signature") or ""
        token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
        if not token:
            return {"signed": False, "mode": "fixture"}
        return {"signed": bool(sig), "mode": "twilio", "note": "signature present checked"}

    def ingest(
        self,
        payload: dict[str, Any] | bytes,
        *,
        protection_id: str,
        auth_signals: dict[str, Any] | None = None,
    ) -> tuple[ShieldEnvelope, bytes | None, dict[str, bytes]]:
        if isinstance(payload, bytes):
            form = {k: v[0] for k, v in parse_qs(payload.decode("utf-8")).items()}
            payload = form
        assert isinstance(payload, dict)
        attachments = []
        num = int(payload.get("NumMedia") or 0)
        for i in range(num):
            media_data = payload.get(f"MediaData{i}")
            if isinstance(media_data, str):
                data = media_data.encode("utf-8")
            else:
                data = media_data or b""
            attachments.append(
                {
                    "filename": f"mms-{i}.bin",
                    "content_type": payload.get(f"MediaContentType{i}")
                    or "application/octet-stream",
                    "data": data,
                }
            )
        for item in payload.get("attachments") or []:
            attachments.append(item)
        normalized = {
            "text": str(payload.get("Body") or payload.get("text") or ""),
            "from": str(payload.get("From") or payload.get("from") or ""),
            "to": [str(payload.get("To") or payload.get("to") or "")],
            "conversation_id": str(payload.get("From") or ""),
            "external_message_id": str(payload.get("MessageSid") or payload.get("id") or ""),
            "attachments": attachments,
            "metadata": {"inbound_number": payload.get("To") or payload.get("to")},
        }
        return build_text_envelope(
            "sms", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import sms_send_twilio

        to = (envelope.to_addrs[0] if envelope.to_addrs else "") or envelope.conversation_id
        result = await sms_send_twilio(
            to=to,
            body=(envelope.text or f"Released {message_id}")[:1500],
            from_number=str((envelope.metadata or {}).get("inbound_number") or "") or None,
        )
        return {
            "channel": "sms",
            "message_id": message_id,
            "to": list(envelope.to_addrs),
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import sms_send_twilio

        to = (envelope.to_addrs[0] if envelope.to_addrs else "") or envelope.conversation_id
        short = summary[:240]
        result = await sms_send_twilio(
            to=to,
            body=short,
            from_number=str((envelope.metadata or {}).get("inbound_number") or "") or None,
        )
        return {
            "channel": "sms",
            "message_id": message_id,
            "to": list(envelope.to_addrs) or [envelope.conversation_id],
            "summary": short,
            **result,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "sms",
            "ok": True,
            "twilio_configured": bool(
                os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_ACCOUNT_SID")
            ),
        }
