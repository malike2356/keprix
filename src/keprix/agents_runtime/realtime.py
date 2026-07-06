"""Realtime voice lane for ECHO-style agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

RealtimeEventType = Literal[
    "speech_in",
    "speech_out",
    "interrupt",
    "tool_pause",
    "escalation",
    "transcript",
]


@dataclass
class RealtimeEvent:
    type: RealtimeEventType
    text: str
    payload: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text, "payload": self.payload, "at": self.at}


@dataclass
class RealtimeSession:
    session_id: str
    agent: str
    events: list[RealtimeEvent] = field(default_factory=list)
    awaiting_approval: bool = False
    interrupted: bool = False

    def append(self, event_type: RealtimeEventType, text: str = "", **payload: Any) -> RealtimeEvent:
        if event_type == "interrupt":
            self.interrupted = True
        if event_type == "tool_pause":
            self.awaiting_approval = True
        if event_type == "escalation":
            self.awaiting_approval = False
        event = RealtimeEvent(type=event_type, text=text, payload=payload)
        self.events.append(event)
        return event

    def transcript(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent": self.agent,
            "awaiting_approval": self.awaiting_approval,
            "interrupted": self.interrupted,
            "events": self.transcript(),
        }


_SESSIONS: dict[str, RealtimeSession] = {}


def create_session(agent: str) -> RealtimeSession:
    session = RealtimeSession(session_id=str(uuid.uuid4()), agent=agent)
    _SESSIONS[session.session_id] = session
    return session


def get_session(session_id: str) -> RealtimeSession | None:
    return _SESSIONS.get(session_id)


def reset_sessions() -> None:
    _SESSIONS.clear()
