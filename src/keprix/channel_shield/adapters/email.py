"""Email Channel Shield adapter (SMTP / provider / shadow poll)."""

from __future__ import annotations

import email
import hashlib
import re
import uuid
from email import policy
from typing import Any

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.common import build_text_envelope
from keprix.channel_shield.pipeline import extract_links
from keprix.channel_shield.types import ShieldAttachment, ShieldEnvelope


def _parse_auth_from_headers(msg: email.message.Message) -> dict[str, Any]:
    auth: dict[str, Any] = {}
    received_spf = msg.get("Received-SPF", "")
    if "pass" in received_spf.lower():
        auth["spf"] = "pass"
    elif "fail" in received_spf.lower():
        auth["spf"] = "fail"
    auth_results = msg.get("Authentication-Results", "")
    for proto in ("spf", "dkim", "dmarc"):
        m = re.search(rf"{proto}=(pass|fail|softfail|none)", auth_results, re.I)
        if m:
            auth[proto] = m.group(1).lower()
    return auth


class EmailAdapter(ChannelAdapter):
    channel = "email"

    def authenticate_ingress(self, headers: dict[str, str], body: bytes) -> dict[str, Any]:
        return {"signed": True, "mode": headers.get("x-shield-mode", "smtp")}

    def ingest(
        self,
        payload: dict[str, Any] | bytes,
        *,
        protection_id: str,
        auth_signals: dict[str, Any] | None = None,
    ) -> tuple[ShieldEnvelope, bytes | None, dict[str, bytes]]:
        if isinstance(payload, dict) and not payload.get("raw_rfc822"):
            return build_text_envelope(
                "email", protection_id, payload, auth_signals=auth_signals
            )

        if isinstance(payload, dict) and payload.get("raw_rfc822"):
            raw = payload["raw_rfc822"]
            if isinstance(raw, str):
                raw = raw.encode("utf-8", errors="replace")
        elif isinstance(payload, bytes):
            raw = payload
        else:
            raise ValueError("unsupported email payload")

        msg = email.message_from_bytes(raw, policy=policy.default)
        text_parts: list[str] = []
        attachments: list[ShieldAttachment] = []
        attachment_bytes: dict[str, bytes] = {}

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "")
                if ctype == "text/plain" and "attachment" not in disp:
                    try:
                        text_parts.append(str(part.get_content()))
                    except Exception:
                        payload_bytes = part.get_payload(decode=True) or b""
                        text_parts.append(payload_bytes.decode("utf-8", errors="replace"))
                elif "attachment" in disp or part.get_filename():
                    data = part.get_payload(decode=True) or b""
                    aid = str(uuid.uuid4())
                    attachment_bytes[aid] = data
                    name = part.get_filename() or "attachment.bin"
                    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                    attachments.append(
                        ShieldAttachment(
                            id=aid,
                            filename=name,
                            content_type=part.get_content_type(),
                            size=len(data),
                            sha256=hashlib.sha256(data).hexdigest(),
                            storage_uri=f"shield://att/{aid}",
                            extension=ext,
                        )
                    )
        else:
            try:
                text_parts.append(str(msg.get_content()))
            except Exception:
                text_parts.append(
                    (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
                )

        text = "\n".join(t for t in text_parts if t)
        to_raw = msg.get("To", "")
        to_addrs = [a.strip() for a in re.split(r"[,;]", to_raw) if a.strip()]
        auth = {**_parse_auth_from_headers(msg), **(auth_signals or {})}
        envelope = ShieldEnvelope(
            channel="email",
            protection_id=protection_id,
            external_message_id=str(msg.get("Message-ID") or uuid.uuid4()),
            conversation_id=str(msg.get("In-Reply-To") or msg.get("References") or ""),
            from_addr=str(msg.get("From") or ""),
            to_addrs=to_addrs,
            text=text,
            links=extract_links(text),
            attachments=attachments,
            auth_signals=auth,
            metadata={"mode": "mime"},
            subject=str(msg.get("Subject") or ""),
        )
        return envelope, raw, attachment_bytes

    async def deliver(self, envelope: ShieldEnvelope, message_id: str) -> dict[str, Any]:
        from keprix.channel_shield.egress import deliver_email_smtp

        body = envelope.text or ""
        if envelope.attachments:
            names = ", ".join(a.filename for a in envelope.attachments)
            body = f"{body}\n\n[Attachments held/analysed: {names}]".strip()
        result = await deliver_email_smtp(
            to_addrs=list(envelope.to_addrs),
            subject=envelope.subject or "(no subject)",
            body=body,
            from_addr=envelope.from_addr or None,
            user_id=str((envelope.metadata or {}).get("user_id") or "local"),
        )
        return {
            "channel": "email",
            "message_id": message_id,
            "to": list(envelope.to_addrs),
            "subject": envelope.subject,
            **result,
        }

    async def notify_safe_summary(
        self, envelope: ShieldEnvelope, message_id: str, summary: str
    ) -> dict[str, Any]:
        from keprix.channel_shield.egress import deliver_email_smtp

        notify_to = list(envelope.to_addrs)
        security = (envelope.metadata or {}).get("security_mailbox")
        if security:
            notify_to = [str(security)]
        result = await deliver_email_smtp(
            to_addrs=notify_to,
            subject=f"[Quarantined] {envelope.subject or 'message'}",
            body=summary,
            user_id=str((envelope.metadata or {}).get("user_id") or "local"),
        )
        return {
            "channel": "email",
            "message_id": message_id,
            "to": notify_to,
            "subject": f"[Quarantined] {envelope.subject or 'message'}",
            "summary": summary,
            **result,
        }

    async def health(self) -> dict[str, Any]:
        from keprix.channel_shield.config import load_channel_shield_config

        cfg = load_channel_shield_config()
        return {
            "channel": "email",
            "ok": True,
            "modes": ["smtp", "provider", "shadow_poll"],
            "smtp": {"host": cfg.smtp_host, "port": cfg.smtp_port},
        }
