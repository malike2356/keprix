"""Room session context notes (Prompt 45)."""

from __future__ import annotations

from collections import defaultdict

from keprix.backend.messaging.schemas import RoomConfig


class SessionStateStore:
    def __init__(self) -> None:
        self._notes: dict[str, list[str]] = defaultdict(list)

    @staticmethod
    def _key(workspace_id: str, room_id: str) -> str:
        return f"{workspace_id}:{room_id}"

    async def append_room_context(self, room_id: str, workspace_id: str, notes: list[str]) -> None:
        key = self._key(workspace_id, room_id)
        self._notes[key].extend(note for note in notes if note.strip())
        self._notes[key] = self._notes[key][-50:]

    async def get_room_context(self, room_id: str, workspace_id: str) -> list[str]:
        return list(self._notes.get(self._key(workspace_id, room_id), []))

    def build_system_fragment(self, room_config: RoomConfig) -> str | None:
        if room_config.visible_replies != "message_tool":
            return None
        notes = self._notes.get(self._key(room_config.workspace_id, room_config.room_id), [])
        lines = [
            "## Group Room Context",
            "You are operating in ambient mode in a group chat room.",
            "You have been monitoring this conversation as a background observer.",
            "Reply only when you have something genuinely useful to add.",
            "If you choose to reply, use the `message` tool to send your response.",
            "If you do not use the `message` tool, the room stays silent.",
            "Do not acknowledge messages just to appear active.",
        ]
        if notes:
            lines.append("")
            lines.append("Recent observer notes:")
            for note in notes[-10:]:
                lines.append(f"- {note}")
        return "\n".join(lines)


_session_state: SessionStateStore | None = None


def get_session_state_store() -> SessionStateStore:
    global _session_state
    if _session_state is None:
        _session_state = SessionStateStore()
    return _session_state


def reset_session_state_store() -> SessionStateStore:
    global _session_state
    _session_state = SessionStateStore()
    return _session_state
