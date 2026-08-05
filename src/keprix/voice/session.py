"""Phone voice session state."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class VoiceSession:
    caller: str
    called: str
    persona: str = "receptionist"
    business_id: str = "default"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "connected"
    topic: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None
    transcript: list[dict[str, Any]] = field(default_factory=list)
    escalated: bool = False
    appointments_booked: int = 0
    cost: dict[str, float] = field(default_factory=dict)

    @property
    def caller_id(self) -> str:
        return hashlib.sha256(self.caller.encode("utf-8")).hexdigest()[:16]

    def append(self, role: str, text: str, **meta: Any) -> None:
        self.transcript.append({"role": role, "text": text, "at": datetime.now(timezone.utc).isoformat(), **meta})

    def finish(self) -> None:
        self.status = "ended"
        self.ended_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "caller": self.caller,
            "called": self.called,
            "persona": self.persona,
            "business_id": self.business_id,
            "status": self.status,
            "topic": self.topic,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "transcript": self.transcript,
            "escalated": self.escalated,
            "appointments_booked": self.appointments_booked,
            "cost": self.cost,
        }


_SESSIONS: dict[str, VoiceSession] = {}


def create_voice_session(*, caller: str, called: str, persona: str = "receptionist", business_id: str = "default") -> VoiceSession:
    session = VoiceSession(caller=caller, called=called, persona=persona, business_id=business_id)
    _SESSIONS[session.session_id] = session
    return session


def get_voice_session(session_id: str) -> VoiceSession | None:
    return _SESSIONS.get(session_id)


def list_voice_sessions(status: str | None = None) -> list[VoiceSession]:
    rows = list(_SESSIONS.values())
    if status:
        rows = [row for row in rows if row.status == status]
    return sorted(rows, key=lambda row: row.started_at, reverse=True)


def reset_voice_sessions() -> None:
    _SESSIONS.clear()
