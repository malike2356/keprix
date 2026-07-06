"""Messaging gateway dispatch with ambient room support (Prompt 45)."""

from __future__ import annotations

from typing import Awaitable, Callable

from keprix.backend.messaging.ambient import AmbientRoomProcessor, get_ambient_processor
from keprix.backend.messaging.message_store import get_message_store
from keprix.backend.messaging.room_config import get_room_config_store
from keprix.backend.messaging.schemas import AgentRunResult, DispatchResult, InboundMessage, RoomConfig
from keprix.backend.messaging.session_state import get_session_state_store

AgentRunner = Callable[[InboundMessage, RoomConfig, list[str]], Awaitable[AgentRunResult]]
ReplySender = Callable[[InboundMessage, RoomConfig, str], Awaitable[None]]


class MessageGateway:
    def __init__(
        self,
        *,
        ambient_processor: AmbientRoomProcessor | None = None,
        agent_runner: AgentRunner | None = None,
        reply_sender: ReplySender | None = None,
    ) -> None:
        self.ambient_processor = ambient_processor or get_ambient_processor()
        self._agent_runner = agent_runner
        self._reply_sender = reply_sender
        self._message_tool_sent: dict[str, bool] = {}

    async def send(self, *, room_id: str, text: str, reply_to: str | None = None) -> dict[str, object]:
        self._message_tool_sent[room_id] = True
        return {"sent": True, "room_id": room_id, "reply_to": reply_to, "text": text}

    def _is_mention(self, message: InboundMessage, room_config: RoomConfig) -> bool:
        if room_config.always_on:
            return True
        return message.is_mention

    async def dispatch_message(self, message: InboundMessage, room_config: RoomConfig) -> DispatchResult:
        await get_message_store().append(message)
        is_mention = self._is_mention(message, room_config)
        ambient_result = None

        if room_config.unmentioned_inbound == "room_event" and not is_mention:
            ambient_result = await self.ambient_processor.process(
                room_id=room_config.room_id,
                message=message,
                workspace_id=room_config.workspace_id,
            )
            if not ambient_result.should_reply:
                return DispatchResult(handled=True, replied=False, mode="ambient_silent", ambient_result=ambient_result)

        if room_config.mention_gating and not is_mention and not (ambient_result and ambient_result.should_reply):
            return DispatchResult(handled=True, replied=False, mode="mention_gated")

        if self._agent_runner is None:
            return DispatchResult(handled=False, replied=False, mode="no_agent_runner", ambient_result=ambient_result)

        context_notes = await get_session_state_store().get_room_context(room_config.room_id, room_config.workspace_id)
        self._message_tool_sent[room_config.room_id] = False
        agent_result = await self._agent_runner(message, room_config, context_notes)

        if room_config.visible_replies == "message_tool":
            replied = bool(self._message_tool_sent.get(room_config.room_id))
            return DispatchResult(
                handled=True,
                replied=replied,
                mode="message_tool",
                ambient_result=ambient_result,
                agent_result=agent_result,
            )

        if agent_result.text and self._reply_sender is not None:
            await self._reply_sender(message, room_config, agent_result.text)
            return DispatchResult(
                handled=True,
                replied=True,
                mode="auto",
                ambient_result=ambient_result,
                agent_result=agent_result,
            )

        return DispatchResult(
            handled=True,
            replied=bool(agent_result.text),
            mode="auto",
            ambient_result=ambient_result,
            agent_result=agent_result,
        )

    async def dispatch_for_room(self, message: InboundMessage) -> DispatchResult:
        room_config = get_room_config_store().get(
            message.workspace_id,
            message.room_id,
            channel_type=message.channel_type,
        )
        return await self.dispatch_message(message, room_config)


_gateway: MessageGateway | None = None


def get_message_gateway(**kwargs) -> MessageGateway:
    global _gateway
    if _gateway is None:
        _gateway = MessageGateway(**kwargs)
    return _gateway


def reset_message_gateway(**kwargs) -> MessageGateway:
    global _gateway
    _gateway = MessageGateway(**kwargs)
    return _gateway
