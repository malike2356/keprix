"""Caller memory context for phone voice sessions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.voice.session import VoiceSession


@dataclass
class CallSummary:
    timestamp: str
    duration_seconds: int
    topic: str
    outcome: str
    follow_up_needed: bool = False
    follow_up_action: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class CallerContext:
    caller_id: str
    name: str | None = None
    previous_calls: list[CallSummary] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    last_call_date: str | None = None

    @classmethod
    async def from_phone(cls, phone: str) -> "CallerContext":
        caller_id = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16]
        data = _CALLER_MEMORY.get(caller_id)
        if not data:
            return cls(caller_id=caller_id)
        return data

    async def save_summary(self, session: VoiceSession, *, outcome: str, notes: str = "") -> CallSummary:
        summary = CallSummary(
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=0,
            topic=session.topic or "phone enquiry",
            outcome=outcome,
            follow_up_needed="follow up" in outcome.lower(),
            notes=notes,
        )
        self.previous_calls.append(summary)
        self.last_call_date = summary.timestamp
        _CALLER_MEMORY[self.caller_id] = self
        return summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "caller_id": self.caller_id,
            "name": self.name,
            "previous_calls": [call.to_dict() for call in self.previous_calls],
            "open_items": self.open_items,
            "preferences": self.preferences,
            "last_call_date": self.last_call_date,
        }


_CALLER_MEMORY: dict[str, CallerContext] = {}


def reset_caller_memory() -> None:
    _CALLER_MEMORY.clear()
