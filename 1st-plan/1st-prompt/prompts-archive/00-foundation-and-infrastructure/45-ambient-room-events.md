# keprix - Prompt 45: Ambient Room Events in Group Channels

## Context

Reference: `planning/agents-to-adopt/openclaw/docs/channels/ambient-room-events.md`.

Prompt 13 builds the messaging gateway with 20+ channel adapters and a unified inbox. The current group chat model works for direct mentions: user mentions the agent, agent replies. This is correct for most cases.

The problem is always-on group deployments. In an AbbiS WhatsApp group with 30 field contractors, the agent does not need to reply to every message. Most messages are between contractors. But the agent should be listening: updating its memory about who is asking what, noting when a new borehole inquiry surfaces, tracking follow-ups. It should reply only when it has something genuinely useful to add - not because it was mentioned.

The current NO_REPLY pattern handles this badly. The agent receives the message, processes it, builds a full response, and then decides to say `NO_REPLY`. That is wasteful: a full LLM call spent on a message the agent should never have drafted a response for in the first place.

Ambient room events separate the two concerns:
- **Inbound processing**: the agent always processes unmentioned group messages as quiet context (updates memory, checks if the message is relevant to a known topic).
- **Outbound decision**: the agent replies only when it explicitly calls the `message` tool. If it does not call `message`, the room stays silent. No `NO_REPLY` pattern needed.

This prompt adds ambient mode to the messaging gateway as a per-room configuration option.

---

## File Structure

```
keprix/backend/messaging/
    ambient.py              - AmbientRoomProcessor: quiet context processing
    gateway.py              - (existing) add ambient mode handling in message dispatch
    room_config.py          - (existing or new) per-room configuration including ambient mode

keprix/tests/messaging/
    test_ambient.py
```

---

## Room Configuration

Ambient mode is configured per-room (not per-channel-type). Any group room across any channel can be set to ambient mode.

```python
# keprix/backend/messaging/room_config.py

from dataclasses import dataclass
from typing import Literal

UnmentionedInboundMode = Literal["normal", "room_event"]
# normal: only process messages that mention the agent
# room_event: process ALL messages as quiet context; never auto-reply

VisibleRepliesMode = Literal["auto", "message_tool"]
# auto: agent replies whenever it has a response (current behavior)
# message_tool: agent replies ONLY when it calls the `message` tool explicitly

@dataclass
class RoomConfig:
    room_id: str
    channel_type: str               # 'whatsapp', 'telegram', 'slack', etc.
    workspace_id: str
    unmentioned_inbound: UnmentionedInboundMode = "normal"
    visible_replies: VisibleRepliesMode = "auto"
    history_limit: int = 50         # how many past messages to include as context
    mention_gating: bool = True     # if True, agent only replies when mentioned
    always_on: bool = False         # if True, room receives all messages regardless of mention
```

Database: add a `room_configs` table with these columns. Configurable per-room via the workspace settings UI and the API.

---

## Ambient Room Processor

```python
# keprix/backend/messaging/ambient.py

class AmbientRoomProcessor:
    """
    Processes group messages in ambient mode.
    Does NOT generate a user-facing reply.
    Updates memory and session state as quiet side-effects only.
    """

    async def process(
        self,
        room_id: str,
        message: InboundMessage,
        workspace_id: str,
    ) -> AmbientProcessingResult:
        """
        Called for every message in an ambient room, whether or not the agent was mentioned.

        Returns:
          - should_reply: bool - True only if the message directly asks the agent for something
          - context_notes: list[str] - notes added to session state (not sent to user)
          - memory_candidates: list[str] - facts worth saving to memory (reviewed by background fork)
        """
        # Build a compact context window: recent room history + this message.
        # Do NOT include the full message history - this is a cheap context update, not a full agent run.
        context = await self._build_room_context(room_id, message, workspace_id)

        # Run a cheap LLM call (use a fast/cheap model, not the primary model).
        # The prompt asks: is this message directed at the agent? If so, what context is relevant?
        result = await self._classify_message(context, message)

        # Update session state with any context notes (non-blocking, no reply generated).
        if result.context_notes:
            await session_state.append_room_context(room_id, workspace_id, result.context_notes)

        # Queue memory candidates for background review (Prompt 03 background review fork).
        if result.memory_candidates:
            await background_review.queue_room_memory(workspace_id, result.memory_candidates)

        return result

    async def _build_room_context(
        self,
        room_id: str,
        message: InboundMessage,
        workspace_id: str,
    ) -> str:
        history = await message_store.get_recent(
            room_id=room_id,
            workspace_id=workspace_id,
            limit=20,   # compact window; not the full history_limit
        )
        lines = [f"{m.sender_name}: {m.text}" for m in history]
        lines.append(f"{message.sender_name}: {message.text}")
        return "\n".join(lines)

    async def _classify_message(
        self,
        context: str,
        message: InboundMessage,
    ) -> AmbientProcessingResult:
        """
        Uses a cheap LLM call (haiku-class) to classify the message.
        Schema: { should_reply: bool, context_notes: [], memory_candidates: [] }
        """
        prompt = (
            "You are monitoring a group chat as a background observer. "
            "Classify this message:\n\n"
            f"{context}\n\n"
            "Return JSON:\n"
            "{\n"
            "  \"should_reply\": true|false,  // true only if the message is a direct question or request to the AI assistant\n"
            "  \"context_notes\": [],          // brief notes about what is being discussed (max 3 items, each under 20 words)\n"
            "  \"memory_candidates\": []       // facts about participants worth remembering (names, roles, projects; max 2 items)\n"
            "}"
        )
        raw = await llm.complete(prompt, model="fast", response_format="json")
        parsed = json.loads(raw)
        return AmbientProcessingResult(
            should_reply=bool(parsed.get("should_reply", False)),
            context_notes=parsed.get("context_notes", []),
            memory_candidates=parsed.get("memory_candidates", []),
        )


@dataclass
class AmbientProcessingResult:
    should_reply: bool
    context_notes: list[str]
    memory_candidates: list[str]
```

---

## Gateway Integration

In the message gateway dispatch loop (`keprix/backend/messaging/gateway.py`), add ambient mode handling before the main agent run:

```python
async def dispatch_message(self, message: InboundMessage, room_config: RoomConfig) -> None:
    """Main message dispatch. Called for every inbound message."""

    is_mention = self._is_mention(message, room_config)

    # Ambient room mode: process all messages as quiet context.
    if room_config.unmentioned_inbound == "room_event" and not is_mention:
        result = await ambient_processor.process(
            room_id=room_config.room_id,
            message=message,
            workspace_id=room_config.workspace_id,
        )
        if not result.should_reply:
            # Agent listened but has nothing to add. Room stays silent.
            return
        # If should_reply is True, fall through to the full agent run below.
        # This means the message was a direct question even without an explicit mention.

    # Normal path: mention-gated or ambient message that needs a reply.
    if room_config.mention_gating and not is_mention and not result.should_reply:
        return  # not mentioned, not ambient-classified as needing reply

    # Full agent run.
    response = await self._run_agent(message, room_config)

    # Visible replies mode: only send if agent called the `message` tool.
    if room_config.visible_replies == "message_tool":
        # The agent's tool calls are inspected. If `message` was called, the
        # gateway already sent the reply (via the tool). Nothing more to do here.
        # If `message` was NOT called, the room stays silent.
        return

    # Default: send whatever the agent produced.
    if response:
        await self._send_reply(response, message, room_config)
```

The `message` tool (already in the tool registry from Prompt 05 or 11) sends a message to the room directly from within a tool call. When `visible_replies = "message_tool"`, this is the ONLY path by which the agent can put text into the room.

---

## The `message` Tool

If not already in the tool registry, add it:

```python
# In tool registry (Prompt 05):

@tool(name="message", category="messaging")
async def send_room_message(
    room_id: str,
    text: str,
    reply_to_message_id: str | None = None,
) -> dict:
    """
    Send a message to a chat room or channel.
    In ambient mode rooms, this is the ONLY way to post a visible reply.
    Use this when you have something genuinely useful to add to the conversation.
    Do not call this just to acknowledge messages.

    Args:
        room_id: The room or channel identifier.
        text: The message text to send.
        reply_to_message_id: Optional message ID to reply to (threading).
    """
    await gateway.send(room_id=room_id, text=text, reply_to=reply_to_message_id)
    return {"sent": True, "room_id": room_id}
```

---

## Room Config API

```
GET    /api/rooms/{room_id}/config
       Returns: RoomConfig for this room

PATCH  /api/rooms/{room_id}/config
       Body: { unmentioned_inbound?, visible_replies?, history_limit?, mention_gating?, always_on? }
       Returns: updated RoomConfig

POST   /api/rooms/{room_id}/config/ambient
       Shortcut: sets unmentioned_inbound="room_event" and visible_replies="message_tool" in one call.
       Recommended setup for always-on group monitoring.
```

---

## System Prompt Fragment for Ambient Rooms

When a room is in ambient mode, the system prompt for any run in that room includes an additional context fragment:

```
## Group Room Context
You are operating in ambient mode in a group chat room.
You have been monitoring this conversation as a background observer.
Recent context from the room is provided below.
Reply only when you have something genuinely useful to add.
If you choose to reply, use the `message` tool to send your response.
If you do not use the `message` tool, the room stays silent.
Do not acknowledge messages just to appear active.
```

This fragment is injected by the gateway into the system prompt stable tier when `visible_replies = "message_tool"`.

---

## Workspace Settings UI

In the messaging settings page: for each connected group room (WhatsApp group, Telegram group, Slack channel), show a toggle: "Ambient monitoring mode." Enabling it sets `unmentioned_inbound = "room_event"` and `visible_replies = "message_tool"`. A tooltip explains: "In ambient mode, the agent listens to all messages but only replies when it has something useful to add."

A secondary toggle: "Always-on" (enables the room to receive all messages without mention gating). Note: not all channels support this; disabled if the channel does not support it.

---

## Acceptance Criteria

- With `unmentioned_inbound = "room_event"`, an unmentioned group message triggers `AmbientRoomProcessor.process()` rather than a full agent run.
- When `AmbientRoomProcessor.process()` returns `should_reply=False`, no message is sent to the room and no full LLM agent run occurs.
- When `AmbientRoomProcessor.process()` returns `should_reply=True`, a full agent run fires and the agent can reply via the `message` tool.
- With `visible_replies = "message_tool"`, a full agent run that does not call the `message` tool produces no visible output in the room.
- With `visible_replies = "auto"` (default), a direct mention always produces a reply as before (no behavior change for existing rooms).
- `context_notes` from ambient processing are stored in session state and appear in the room context on the next full agent run.
- `memory_candidates` from ambient processing are queued for background review, not committed immediately.
- `POST /api/rooms/{room_id}/config/ambient` sets both `unmentioned_inbound` and `visible_replies` atomically.
- `_classify_message` uses a fast/cheap model (not the primary workspace model) so ambient processing does not inflate costs on busy group chats.
- A room with `unmentioned_inbound = "normal"` (default) behaves identically to the pre-ambient behavior for all message types.
