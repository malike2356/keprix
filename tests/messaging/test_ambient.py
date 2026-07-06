"""Prompt 45 ambient room events tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.messaging.ambient import AmbientRoomProcessor
from keprix.backend.messaging.background_review import get_background_review_queue, reset_background_review_queue
from keprix.backend.messaging.gateway import reset_message_gateway
from keprix.backend.messaging.message_store import reset_message_store
from keprix.backend.messaging.room_config import reset_room_config_store
from keprix.backend.messaging.schemas import AgentRunResult, AmbientProcessingResult, InboundMessage, RoomConfig
from keprix.backend.messaging.session_state import get_session_state_store, reset_session_state_store


@pytest.fixture
def messaging_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_room_config_store(tmp_path / "messaging")
    reset_message_store()
    reset_session_state_store()
    reset_background_review_queue()
    return tmp_path


def _message(**overrides) -> InboundMessage:
    payload = {
        "room_id": "group-1",
        "workspace_id": "default",
        "channel_type": "whatsapp",
        "message_id": "m-1",
        "sender_id": "u-1",
        "sender_name": "Ada",
        "text": "contractors are on site",
        "is_mention": False,
        "is_group": True,
    }
    payload.update(overrides)
    return InboundMessage(**payload)


def _room(**overrides) -> RoomConfig:
    payload = {
        "room_id": "group-1",
        "channel_type": "whatsapp",
        "workspace_id": "default",
    }
    payload.update(overrides)
    return RoomConfig(**payload)


@pytest.mark.asyncio
async def test_ambient_unmentioned_skips_full_agent_run(messaging_env):
    async def classifier(_context, message):
        return AmbientProcessingResult(should_reply=False, context_notes=["site update"], memory_candidates=[])

    agent_calls = {"count": 0}

    async def agent_runner(_message, _room, _notes):
        agent_calls["count"] += 1
        return AgentRunResult(text="hello")

    gateway = reset_message_gateway(
        ambient_processor=AmbientRoomProcessor(classifier=classifier),
        agent_runner=agent_runner,
    )
    result = await gateway.dispatch_message(_message(), _room(unmentioned_inbound="room_event"))
    assert result.mode == "ambient_silent"
    assert result.replied is False
    assert agent_calls["count"] == 0


@pytest.mark.asyncio
async def test_ambient_should_reply_triggers_agent_run(messaging_env):
    async def classifier(_context, _message):
        return AmbientProcessingResult(should_reply=True, context_notes=[], memory_candidates=[])

    agent_calls = {"count": 0}

    async def agent_runner(_message, _room, _notes):
        agent_calls["count"] += 1
        return AgentRunResult(text="answer")

    replies: list[str] = []

    async def reply_sender(_message, _room, text):
        replies.append(text)

    gateway = reset_message_gateway(
        ambient_processor=AmbientRoomProcessor(classifier=classifier),
        agent_runner=agent_runner,
        reply_sender=reply_sender,
    )
    result = await gateway.dispatch_message(_message(text="can you help?"), _room(unmentioned_inbound="room_event"))
    assert agent_calls["count"] == 1
    assert result.replied is True


@pytest.mark.asyncio
async def test_message_tool_only_visible_replies(messaging_env):
    async def silent_agent(_message, _room, _notes):
        return AgentRunResult(text="draft only")

    gateway = reset_message_gateway(agent_runner=silent_agent)
    result = await gateway.dispatch_message(
        _message(is_mention=True, text="@bot hello"),
        _room(unmentioned_inbound="normal", visible_replies="message_tool"),
    )
    assert result.replied is False

    async def tool_agent(message, _room, _notes):
        await gateway.send(room_id=message.room_id, text="visible")
        return AgentRunResult(text="draft only")

    gateway = reset_message_gateway(agent_runner=tool_agent)
    result = await gateway.dispatch_message(
        _message(is_mention=True, text="@bot hello"),
        _room(unmentioned_inbound="normal", visible_replies="message_tool"),
    )
    assert result.replied is True


@pytest.mark.asyncio
async def test_normal_mode_mention_replies_auto(messaging_env):
    replies: list[str] = []

    async def agent_runner(_message, _room, _notes):
        return AgentRunResult(text="auto reply")

    async def reply_sender(_message, _room, text):
        replies.append(text)

    gateway = reset_message_gateway(agent_runner=agent_runner, reply_sender=reply_sender)
    result = await gateway.dispatch_message(_message(is_mention=True), _room())
    assert result.replied is True
    assert replies == ["auto reply"]


@pytest.mark.asyncio
async def test_context_notes_and_memory_candidates(messaging_env):
    async def classifier(_context, _message):
        return AmbientProcessingResult(
            should_reply=False,
            context_notes=["borehole inquiry"],
            memory_candidates=["Ada is a contractor"],
        )

    processor = AmbientRoomProcessor(classifier=classifier)
    gateway = reset_message_gateway(ambient_processor=processor)
    await gateway.dispatch_message(_message(), _room(unmentioned_inbound="room_event"))

    notes = await get_session_state_store().get_room_context("group-1", "default")
    assert "borehole inquiry" in notes
    pending = get_background_review_queue().list_pending("default")
    assert pending[0].content == "Ada is a contractor"


@pytest.mark.asyncio
async def test_ambient_api_shortcut(messaging_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/rooms/group-1/config/ambient",
            json={"workspace_id": "default", "channel_type": "whatsapp"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["unmentioned_inbound"] == "room_event"
    assert body["visible_replies"] == "message_tool"


@pytest.mark.asyncio
async def test_normal_room_unchanged_for_unmentioned(messaging_env):
    agent_calls = {"count": 0}

    async def agent_runner(_message, _room, _notes):
        agent_calls["count"] += 1
        return AgentRunResult(text="nope")

    gateway = reset_message_gateway(agent_runner=agent_runner)
    result = await gateway.dispatch_message(_message(), _room(unmentioned_inbound="normal"))
    assert result.mode == "mention_gated"
    assert agent_calls["count"] == 0
