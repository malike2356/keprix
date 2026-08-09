"""In-process mail capture for local/standalone E2E (Prompt 628).

When real external delivery is inappropriate, Soft Wall approve can bind SMTP
to this capture list (or to Mailpit via docker/docker-compose.mailpit.yml).
Captured sends are real adapter path traffic: subject/body/to/from are recorded
after Soft Wall approval, not mocked success without calling the send helper.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_CAPTURED: list[dict[str, Any]] = []


def reset_mail_capture() -> None:
    _CAPTURED.clear()


def captured_messages() -> list[dict[str, Any]]:
    return deepcopy(_CAPTURED)


def record_smtp_send(
    account: dict[str, Any],
    *,
    from_addr: str,
    to_addresses: list[str],
    cc_addresses: list[str],
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Drop-in replacement for ``keprix.email.helpers.send_smtp_message``.

    Returns provider ids so delivery stamps genuine message/thread identifiers.
    """
    import uuid

    mid = f"capture-{uuid.uuid4().hex[:16]}@keprix.local"
    row = {
        "to": list(to_addresses or []),
        "cc": list(cc_addresses or []),
        "subject": subject,
        "body": body,
        "from": from_addr
        or (account or {}).get("email_address")
        or (account or {}).get("username"),
        "account_id": (account or {}).get("id"),
        "provider_message_id": mid,
        "message_id": mid,
    }
    _CAPTURED.append(row)
    return {"message_id": mid, "provider_message_id": mid, "provider": "mail_capture"}


def capture_sender_resolution(
    *,
    mailbox: str = "sender@keprix.local",
    account_id: str = "capture_acct",
    smtp_host: str = "127.0.0.1",
    smtp_port: int = 1025,
) -> dict[str, Any]:
    """Return a resolve_sender payload pointing at local SMTP / Mailpit."""
    account = {
        "id": account_id,
        "email_address": mailbox,
        "username": mailbox,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "use_starttls": False,
        "password": "",
    }
    return {
        "mode": "smtp",
        "provider": "smtp",
        "account_id": account_id,
        "mailbox": mailbox,
        "account": account,
    }
