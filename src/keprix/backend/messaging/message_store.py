"""Recent room message store (Prompt 45)."""

from __future__ import annotations

from collections import defaultdict, deque

from keprix.backend.messaging.schemas import InboundMessage, StoredMessage


class MessageStore:
    def __init__(self, *, max_per_room: int = 200) -> None:
        self._max_per_room = max_per_room
        self._rooms: dict[str, deque[StoredMessage]] = defaultdict(deque)

    @staticmethod
    def _key(workspace_id: str, room_id: str) -> str:
        return f"{workspace_id}:{room_id}"

    async def append(self, message: InboundMessage) -> None:
        key = self._key(message.workspace_id, message.room_id)
        queue = self._rooms[key]
        queue.append(
            StoredMessage(
                room_id=message.room_id,
                workspace_id=message.workspace_id,
                sender_name=message.sender_name,
                text=message.text,
            )
        )
        while len(queue) > self._max_per_room:
            queue.popleft()

    async def get_recent(self, *, room_id: str, workspace_id: str, limit: int = 20) -> list[StoredMessage]:
        key = self._key(workspace_id, room_id)
        rows = list(self._rooms.get(key, deque()))
        return rows[-limit:]


_message_store: MessageStore | None = None


def get_message_store() -> MessageStore:
    global _message_store
    if _message_store is None:
        _message_store = MessageStore()
    return _message_store


def reset_message_store() -> MessageStore:
    global _message_store
    _message_store = MessageStore()
    return _message_store
