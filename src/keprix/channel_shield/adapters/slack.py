"""Slack Events API Channel Shield adapter."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.types import ShieldEnvelope


class SlackAdapter(ChannelAdapter):
    channel = "slack"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()
        ts = headers.get("x-slack-request-timestamp") or headers.get("X-Slack-Request-Timestamp") or ""
        sig = headers.get("x-slack-signature") or headers.get("X-Slack-Signature") or ""
        if not secret:
            return {"signed": False, "mode": "fixture", "reason": "no signing secret configured"}
        try:
            if abs(time.time() - int(ts)) > 60 * 5:
                return {"signed": False, "reason": "timestamp skew"}
        except ValueError:
            return {"signed": False, "reason": "bad timestamp"}
        base = f"v0:{ts}:{body.decode('utf-8', errors='replace')}"
        digest = hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        expected = f"v0={digest}"
        ok = hmac.compare_digest(expected, sig)
        return {"signed": ok, "mode": "slack_events"}

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
        event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
        files = []
        for f in event.get("files") or []:
            files.append(
                {
                    "id": f.get("id"),
                    "filename": f.get("name") or f.get("title") or "file.bin",
                    "content_type": f.get("mimetype"),
                    "data": f.get("data") or b"",
                }
            )
        normalized = {
            "text": event.get("text") or "",
            "from": event.get("user") or event.get("username") or "",
            "conversation_id": event.get("channel") or "",
            "external_message_id": event.get("ts") or event.get("client_msg_id") or "",
            "attachments": files,
            "metadata": {
                "team_id": payload.get("team_id") or event.get("team"),
                "type": event.get("type"),
            },
        }
        return build_text_envelope(
            "slack", protection_id, normalized, auth_signals=auth_signals
        )

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        # Slack cannot silently rewrite peer messages; deliver = allow downstream agent/post.
        # Optional: post a clean notice when bot token is present.
        from keprix.channel_shield.egress import slack_post_message

        channel = envelope.conversation_id or str((envelope.metadata or {}).get("channel") or "")
        posted = {"ok": True, "mode": "allow_downstream"}
        if channel and (envelope.metadata or {}).get("post_on_deliver"):
            posted = await slack_post_message(
                channel=channel,
                text=f"Released by Channel Shield ({message_id}).",
                thread_ts=envelope.external_message_id or None,
            )
        return {
            "channel": "slack",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            "note": "Slack does not support transparent MX-style intercept; bot posts or blocks files only.",
            **posted,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import slack_post_message

        channel = (
            str((envelope.metadata or {}).get("security_channel") or "")
            or envelope.conversation_id
        )
        result = await slack_post_message(
            channel=channel,
            text=summary[:3500],
            thread_ts=envelope.external_message_id or None,
        )
        return {
            "channel": "slack",
            "message_id": message_id,
            "conversation_id": envelope.conversation_id,
            "summary": summary,
            **result,
        }

    async def suppress_original(self, envelope: ShieldEnvelope) -> dict[str, Any]:
        return {
            "suppressed": False,
            "reason": "Slack message delete requires chat:write and is best-effort for bot messages only",
        }

    async def health(self) -> dict[str, Any]:
        return {
            "channel": "slack",
            "ok": True,
            "signing_secret_configured": bool(os.environ.get("SLACK_SIGNING_SECRET")),
        }
