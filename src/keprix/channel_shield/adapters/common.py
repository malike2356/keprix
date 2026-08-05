"""Shared helpers for Channel Shield adapters."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from keprix.channel_shield.pipeline import extract_links
from keprix.channel_shield.types import ShieldAttachment, ShieldEnvelope


def build_text_envelope(
    channel: str,
    protection_id: str,
    payload: dict[str, Any],
    *,
    auth_signals: dict[str, Any] | None = None,
) -> tuple[ShieldEnvelope, bytes | None, dict[str, bytes]]:
    text = str(payload.get("text") or payload.get("body") or payload.get("message") or "")
    attachment_bytes: dict[str, bytes] = {}
    attachments: list[ShieldAttachment] = []
    for item in payload.get("attachments") or payload.get("files") or []:
        aid = str(item.get("id") or uuid.uuid4())
        data = item.get("data")
        if isinstance(data, str):
            data = data.encode("utf-8")
        elif data is None:
            data = b""
        attachment_bytes[aid] = data
        name = str(item.get("filename") or item.get("name") or "file.bin")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else str(item.get("extension") or "")
        attachments.append(
            ShieldAttachment(
                id=aid,
                filename=name,
                content_type=str(item.get("content_type") or item.get("mimetype") or "application/octet-stream"),
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                storage_uri=f"shield://att/{aid}",
                extension=ext,
            )
        )
    envelope = ShieldEnvelope(
        channel=channel,
        protection_id=protection_id,
        external_message_id=str(
            payload.get("external_message_id")
            or payload.get("message_id")
            or payload.get("ts")
            or payload.get("id")
            or uuid.uuid4()
        ),
        conversation_id=str(
            payload.get("conversation_id")
            or payload.get("channel_id")
            or payload.get("chat_id")
            or payload.get("thread_ts")
            or ""
        ),
        from_addr=str(
            payload.get("from")
            or payload.get("user")
            or payload.get("sender")
            or payload.get("author")
            or ""
        ),
        to_addrs=list(payload.get("to") or payload.get("recipients") or []),
        text=text,
        links=extract_links(text),
        attachments=attachments,
        auth_signals=dict(auth_signals or payload.get("auth_signals") or {}),
        metadata=dict(payload.get("metadata") or {}),
        subject=str(payload.get("subject") or ""),
    )
    return envelope, text.encode("utf-8"), attachment_bytes


def verify_hmac_sha256(secret: str, body: bytes, signature: str, *, prefix: str = "") -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = signature[len(prefix) :] if prefix and signature.startswith(prefix) else signature
    return hmac.compare_digest(expected, provided)
