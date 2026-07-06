"""Messaging schemas for ambient room events (Prompt 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

UnmentionedInboundMode = Literal["normal", "room_event"]
VisibleRepliesMode = Literal["auto", "message_tool"]


@dataclass
class RoomConfig:
    room_id: str
    channel_type: str
    workspace_id: str
    unmentioned_inbound: UnmentionedInboundMode = "normal"
    visible_replies: VisibleRepliesMode = "auto"
    history_limit: int = 50
    mention_gating: bool = True
    always_on: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "channel_type": self.channel_type,
            "workspace_id": self.workspace_id,
            "unmentioned_inbound": self.unmentioned_inbound,
            "visible_replies": self.visible_replies,
            "history_limit": self.history_limit,
            "mention_gating": self.mention_gating,
            "always_on": self.always_on,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RoomConfig":
        return cls(
            room_id=str(payload["room_id"]),
            channel_type=str(payload.get("channel_type") or "unknown"),
            workspace_id=str(payload.get("workspace_id") or "default"),
            unmentioned_inbound=payload.get("unmentioned_inbound", "normal"),
            visible_replies=payload.get("visible_replies", "auto"),
            history_limit=int(payload.get("history_limit") or 50),
            mention_gating=bool(payload.get("mention_gating", True)),
            always_on=bool(payload.get("always_on", False)),
        )


@dataclass
class InboundMessage:
    room_id: str
    workspace_id: str
    channel_type: str
    message_id: str
    sender_id: str
    sender_name: str
    text: str
    is_mention: bool = False
    is_group: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StoredMessage:
    room_id: str
    workspace_id: str
    sender_name: str
    text: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AmbientProcessingResult:
    should_reply: bool
    context_notes: list[str]
    memory_candidates: list[str]


@dataclass
class AgentRunResult:
    text: str | None = None
    message_tool_called: bool = False


@dataclass
class DispatchResult:
    handled: bool
    replied: bool
    mode: str
    ambient_result: AmbientProcessingResult | None = None
    agent_result: AgentRunResult | None = None
