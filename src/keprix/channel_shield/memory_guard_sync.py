"""Sync memory guard for tools that cannot await."""

from __future__ import annotations

from keprix.channel_shield.agent_safe import BLOCKED_VERDICTS
from keprix.channel_shield.store import get_channel_shield_store
from keprix.channel_shield.types import MessageStatus


def check_memory_write(
    content: str,
    *,
    message_id: str | None = None,
    memory_kind: str | None = None,
) -> str | None:
    """Return an error string when the write must be blocked, else None."""
    lower = (content or "").lower()
    markers = (
        "eicar-standard-antivirus-test-file",
        "ignore previous instructions",
        "system prompt override",
        "powershell -enc",
    )
    if any(m in lower for m in markers) and (memory_kind or "").lower() not in {
        "incident",
        "security_incident",
    }:
        return (
            "Channel Shield blocked memory write: raw suspicious content. "
            "Store an incident memory with evidence handle instead."
        )

    if not message_id:
        return None

    store = get_channel_shield_store()
    message = store.messages.get(message_id)
    if message is None:
        return None

    if message.status == MessageStatus.DESTROYED.value:
        return "Channel Shield: message destroyed; memory write refused."

    verdict = message.verdict or ""
    blocked = verdict in BLOCKED_VERDICTS and message.status not in {
        MessageStatus.RELEASED.value,
        MessageStatus.DELIVERED.value,
    }
    if blocked and (memory_kind or "").lower() not in {"incident", "security_incident"}:
        # Best-effort audit (sync append)
        store.memory_blocks.append(
            {
                "action": "memory",
                "messageId": message_id,
                "reason": "ordinary memory blocked",
            }
        )
        return (
            "Channel Shield blocked ordinary memory for quarantined content. "
            "Use incident memory only (prefix [channel-shield-incident])."
        )
    return None
