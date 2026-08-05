"""Discord Channel Shield adapter."""

from __future__ import annotations

import os
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class DiscordAdapter(ChannelAdapter):
    channel = "discord"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        # Interactions use Ed25519; gateway uses bot token. Fixture when unset.
        if headers.get("x-signature-ed25519") and os.environ.get("DISCORD_PUBLIC_KEY"):
            return {"signed": True, "mode": "interaction"}
        if os.environ.get("DISCORD_BOT_TOKEN"):
            return {"signed": True, "mode": "gateway"}
        return {"signed": False, "mode": "fixture"}

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
        author = payload.get("author") if isinstance(payload.get("author"), dict) else {}
        attachments = []
        for att in payload.get("attachments") or []:
            attachments.append(
                {
                    "id": att.get("id"),
                    "filename": att.get("filename") or "file.bin",
                    "content_type": att.get("content_type"),
                    "data": att.get("data") or b"",
                }
            )
        normalized = {
            "text": payload.get("content") or payload.get("text") or "",
            "from": str(author.get("id") or author.get("username") or payload.get("user") or ""),
            "conversation_id": str(payload.get("channel_id") or ""),
            "external_message_id": str(payload.get("id") or ""),
            "attachments": attachments,
            "metadata": {
                "guild_id": payload.get("guild_id"),
            },
        }
        return build_text_envelope(
            "discord", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import discord_send_message

        webhook = str((envelope.metadata or {}).get("webhook_url") or "")
        result = await discord_send_message(
            channel_id=envelope.conversation_id,
            text=envelope.text or f"Released by Channel Shield ({message_id})",
            webhook_url=webhook or None,
        )
        return {
            "channel": "discord",
            "message_id": message_id,
            "channel_id": envelope.conversation_id,
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import discord_send_message

        webhook = str((envelope.metadata or {}).get("security_webhook_url") or "")
        result = await discord_send_message(
            channel_id=envelope.conversation_id,
            text=summary[:1900],
            webhook_url=webhook or None,
        )
        return {
            "channel": "discord",
            "message_id": message_id,
            "channel_id": envelope.conversation_id,
            "summary": summary,
            **result,
        }

    async def suppress_original(self, envelope: ShieldEnvelope) -> dict[str, Any]:
        return {
            "suppressed": True,
            "mode": "best_effort_delete",
            "note": "Requires Manage Messages; bot-authored deletes only when applicable",
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "discord",
            "ok": True,
            "token_configured": bool(os.environ.get("DISCORD_BOT_TOKEN")),
        }
