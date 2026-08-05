"""Lightweight SMTP receiver for email Channel Shield (persist-before-accept)."""

from __future__ import annotations

import asyncio
import email
import logging
from email.policy import default as default_policy
from typing import Any

from keprix.channel_shield.adapters.registry import get_adapter
from keprix.channel_shield.config import load_channel_shield_config
from keprix.channel_shield.service import get_channel_shield_service
from keprix.channel_shield.store import get_channel_shield_store

logger = logging.getLogger(__name__)

_SERVER: asyncio.AbstractServer | None = None


async def _handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    """Minimal SMTP dialogue: EHLO/MAIL/RCPT/DATA then process."""
    peer = writer.get_extra_info("peername")
    try:
        writer.write(b"220 keprix-channel-shield ESMTP\r\n")
        await writer.drain()
        mail_from = ""
        rcpt_to: list[str] = []
        data_mode = False
        data_buf = bytearray()
        while True:
            line = await reader.readline()
            if not line:
                break
            if data_mode:
                if line == b".\r\n":
                    raw = bytes(data_buf)
                    await _accept_message(raw, mail_from, rcpt_to)
                    writer.write(b"250 OK queued\r\n")
                    await writer.drain()
                    data_mode = False
                    data_buf.clear()
                    continue
                if line.startswith(b".."):
                    line = line[1:]
                data_buf.extend(line)
                continue
            cmd = line.decode("utf-8", errors="replace").strip()
            upper = cmd.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                writer.write(b"250-keprix\r\n250 OK\r\n")
            elif upper.startswith("MAIL FROM:"):
                mail_from = cmd[10:].strip().strip("<>")
                writer.write(b"250 OK\r\n")
            elif upper.startswith("RCPT TO:"):
                rcpt_to.append(cmd[8:].strip().strip("<>"))
                writer.write(b"250 OK\r\n")
            elif upper == "DATA":
                writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                data_mode = True
            elif upper == "QUIT":
                writer.write(b"221 Bye\r\n")
                await writer.drain()
                break
            elif upper == "RSET":
                mail_from = ""
                rcpt_to = []
                writer.write(b"250 OK\r\n")
            elif upper == "NOOP":
                writer.write(b"250 OK\r\n")
            else:
                writer.write(b"502 Command not implemented\r\n")
            await writer.drain()
    except Exception:
        logger.exception("SMTP client error from %s", peer)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _accept_message(raw: bytes, mail_from: str, rcpt_to: list[str]) -> None:
    """Persist then analyse. Fail closed on analysis error."""
    store = get_channel_shield_store()
    protection = None
    for rcpt in rcpt_to:
        domain = rcpt.split("@")[-1] if "@" in rcpt else rcpt
        protection = await store.find_protection_by_key("email", domain)
        if protection:
            break
        protection = await store.find_protection_by_key("email", rcpt)
        if protection:
            break
    if protection is None:
        for p in store.protections.values():
            if p.channel == "email" and p.enabled:
                protection = p
                break
    if protection is None:
        logger.warning("SMTP accept with no email protection configured")
        return

    adapter = get_adapter("email")
    envelope, raw_bytes, attachment_bytes = adapter.ingest(
        raw,
        protection_id=protection.id,
        auth_signals={"signed": True, "mode": "smtp", "mail_from": mail_from},
    )
    if not envelope.to_addrs and rcpt_to:
        envelope.to_addrs = list(rcpt_to)
    if not envelope.from_addr and mail_from:
        envelope.from_addr = mail_from
    # Touch headers for completeness
    try:
        msg = email.message_from_bytes(raw, policy=default_policy)
        if not envelope.subject:
            envelope.subject = str(msg.get("Subject") or "")
    except Exception:
        pass

    service = get_channel_shield_service()
    await service.process_envelope(
        protection.user_id,
        envelope,
        raw_bytes=raw_bytes,
        attachment_bytes=attachment_bytes,
    )


async def start_smtp_receiver() -> dict[str, Any]:
    global _SERVER
    cfg = load_channel_shield_config()
    if not cfg.enabled or not cfg.adapter_enabled("email"):
        return {"started": False, "reason": "disabled"}
    if _SERVER is not None:
        return {"started": True, "already": True, "host": cfg.smtp_host, "port": cfg.smtp_port}
    _SERVER = await asyncio.start_server(_handle_client, cfg.smtp_host, cfg.smtp_port)
    logger.info("Channel Shield SMTP listening on %s:%s", cfg.smtp_host, cfg.smtp_port)
    return {"started": True, "host": cfg.smtp_host, "port": cfg.smtp_port}


async def stop_smtp_receiver() -> None:
    global _SERVER
    if _SERVER is None:
        return
    _SERVER.close()
    await _SERVER.wait_closed()
    _SERVER = None
