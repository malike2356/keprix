"""Ambient room `message` tool alias (Prompt 45)."""

from __future__ import annotations

from typing import Any

from keprix.backend.messaging.gateway import get_message_gateway


TOOL_SPEC = {
    "name": "message",
    "description": (
        "Send a message to a chat room or channel. "
        "In ambient mode rooms, this is the ONLY way to post a visible reply."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "room_id": {"type": "string"},
            "text": {"type": "string"},
            "reply_to_message_id": {"type": "string"},
        },
        "required": ["room_id", "text"],
    },
}


async def send_room_message(
    room_id: str,
    text: str,
    reply_to_message_id: str | None = None,
) -> dict[str, Any]:
    return await get_message_gateway().send(room_id=room_id, text=text, reply_to=reply_to_message_id)
