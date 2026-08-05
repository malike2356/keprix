"""Microsoft Teams Channel Shield adapter."""

from __future__ import annotations

import os
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class TeamsAdapter(ChannelAdapter):
    channel = "teams"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        # Bot Framework JWT validation is environment-specific; fixture mode when unset.
        auth = headers.get("authorization") or headers.get("Authorization") or ""
        if not auth and not os.environ.get("TEAMS_APP_ID"):
            return {"signed": False, "mode": "fixture"}
        return {"signed": bool(auth), "mode": "bot_framework"}

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
        attachments = []
        for att in payload.get("attachments") or []:
            content = att.get("content") if isinstance(att.get("content"), dict) else {}
            attachments.append(
                {
                    "filename": att.get("name") or content.get("filename") or "file.bin",
                    "content_type": att.get("contentType") or "application/octet-stream",
                    "data": att.get("data") or b"",
                }
            )
        from_obj = payload.get("from") if isinstance(payload.get("from"), dict) else {}
        conv = payload.get("conversation") if isinstance(payload.get("conversation"), dict) else {}
        normalized = {
            "text": payload.get("text") or "",
            "from": from_obj.get("id") or from_obj.get("name") or "",
            "conversation_id": conv.get("id") or "",
            "external_message_id": payload.get("id") or "",
            "attachments": attachments,
            "metadata": {
                "tenant_id": (payload.get("channelData") or {}).get("tenant", {}).get("id")
                if isinstance(payload.get("channelData"), dict)
                else payload.get("tenant_id"),
                "serviceUrl": payload.get("serviceUrl"),
            },
        }
        return build_text_envelope(
            "teams", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import teams_send_activity

        service_url = str((envelope.metadata or {}).get("serviceUrl") or "")
        result = await teams_send_activity(
            service_url=service_url,
            conversation_id=envelope.conversation_id,
            text=envelope.text or f"Released by Channel Shield ({message_id})",
        )
        return {
            "channel": "teams",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import teams_send_activity

        service_url = str((envelope.metadata or {}).get("serviceUrl") or "")
        result = await teams_send_activity(
            service_url=service_url,
            conversation_id=envelope.conversation_id,
            text=summary[:4000],
        )
        return {
            "channel": "teams",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            "summary": summary,
            **result,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "teams",
            "ok": True,
            "app_id_configured": bool(os.environ.get("TEAMS_APP_ID")),
        }
