"""Ambient room processor (Prompt 45)."""

from __future__ import annotations

from typing import Callable

from keprix.backend.messaging.background_review import get_background_review_queue
from keprix.backend.messaging.classifier import ClassifierFn, default_classifier
from keprix.backend.messaging.message_store import get_message_store
from keprix.backend.messaging.schemas import AmbientProcessingResult, InboundMessage
from keprix.backend.messaging.session_state import get_session_state_store


class AmbientRoomProcessor:
    def __init__(self, *, classifier: ClassifierFn | None = None) -> None:
        self._classifier = classifier or default_classifier

    async def process(
        self,
        room_id: str,
        message: InboundMessage,
        workspace_id: str,
    ) -> AmbientProcessingResult:
        context = await self._build_room_context(room_id, message, workspace_id)
        result = await self._classify_message(context, message)
        if result.context_notes:
            await get_session_state_store().append_room_context(room_id, workspace_id, result.context_notes)
        if result.memory_candidates:
            await get_background_review_queue().queue_room_memory(workspace_id, result.memory_candidates)
        return result

    async def _build_room_context(
        self,
        room_id: str,
        message: InboundMessage,
        workspace_id: str,
    ) -> str:
        history = await get_message_store().get_recent(room_id=room_id, workspace_id=workspace_id, limit=20)
        lines = [f"{row.sender_name}: {row.text}" for row in history]
        if not lines or lines[-1] != f"{message.sender_name}: {message.text}":
            lines.append(f"{message.sender_name}: {message.text}")
        return "\n".join(lines)

    async def _classify_message(self, context: str, message: InboundMessage) -> AmbientProcessingResult:
        return await self._classifier(context, message)


def get_ambient_processor(classifier: ClassifierFn | None = None) -> AmbientRoomProcessor:
    return AmbientRoomProcessor(classifier=classifier)
