"""Telegram Channel Shield adapter."""

from __future__ import annotations

import os
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class TelegramAdapter(ChannelAdapter):
    channel = "telegram"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
        provided = headers.get("x-telegram-bot-api-secret-token") or headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )
        if not secret:
            return {"signed": False, "mode": "fixture"}
        return {"signed": provided == secret, "mode": "webhook"}

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
        message = payload.get("message") or payload.get("edited_message") or payload
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        frm = message.get("from") if isinstance(message.get("from"), dict) else {}
        attachments = []
        for key in ("document", "photo", "video", "audio"):
            media = message.get(key)
            if not media:
                continue
            if key == "photo" and isinstance(media, list) and media:
                media = media[-1]
            if isinstance(media, dict):
                attachments.append(
                    {
                        "filename": media.get("file_name") or f"{key}.bin",
                        "content_type": media.get("mime_type") or "application/octet-stream",
                        "data": media.get("data") or b"",
                        "id": media.get("file_id"),
                    }
                )
        normalized = {
            "text": message.get("text") or message.get("caption") or "",
            "from": str(frm.get("id") or frm.get("username") or ""),
            "conversation_id": str(chat.get("id") or ""),
            "external_message_id": str(message.get("message_id") or payload.get("update_id") or ""),
            "attachments": attachments,
            "metadata": {"update_id": payload.get("update_id")},
        }
        return build_text_envelope(
            "telegram", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import telegram_send_message

        result = await telegram_send_message(
            chat_id=envelope.conversation_id,
            text=envelope.text or f"Released message {message_id}",
        )
        return {
            "channel": "telegram",
            "message_id": message_id,
            "chat_id": envelope.conversation_id,
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import telegram_send_message

        result = await telegram_send_message(
            chat_id=envelope.conversation_id, text=summary[:4000]
        )
        return {
            "channel": "telegram",
            "message_id": message_id,
            "chat_id": envelope.conversation_id,
            "summary": summary,
            **result,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "telegram",
            "ok": True,
            "token_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        }
