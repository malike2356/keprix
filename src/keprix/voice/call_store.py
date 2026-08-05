"""In-memory call records for the Aiva phone channel."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class VoiceTurn:
    role: str
    text: str
    timestamp: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "text": self.text, "timestamp": self.timestamp.isoformat()}


@dataclass
class VoiceCallRecord:
    call_sid: str
    worker_id: str
    caller_number: str
    caller_name: str | None = None
    caller_contact_id: str | None = None
    started_at: datetime = field(default_factory=_now)
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    transcript: list[VoiceTurn] = field(default_factory=list)
    summary: str | None = None
    escalated: bool = False
    escalated_to: str | None = None
    tasks_created: list[str] = field(default_factory=list)
    recording_url: str | None = None

    def add_turn(self, role: str, text: str) -> None:
        self.transcript.append(VoiceTurn(role=role, text=text))

    def finish(self) -> None:
        self.ended_at = _now()
        self.duration_seconds = max(0, int((self.ended_at - self.started_at).total_seconds()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_sid": self.call_sid,
            "worker_id": self.worker_id,
            "caller_number": self.caller_number,
            "caller_name": self.caller_name,
            "caller_contact_id": self.caller_contact_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "transcript": [turn.to_dict() for turn in self.transcript],
            "summary": self.summary,
            "escalated": self.escalated,
            "escalated_to": self.escalated_to,
            "tasks_created": self.tasks_created,
            "recording_url": self.recording_url,
        }


_CALLS: dict[str, VoiceCallRecord] = {}


class VoiceCallStore:
    async def create(self, call_sid: str, *, worker_id: str, caller: str, caller_name: str | None = None, caller_contact_id: str | None = None) -> VoiceCallRecord:
        record = VoiceCallRecord(
            call_sid=call_sid,
            worker_id=worker_id,
            caller_number=caller,
            caller_name=caller_name,
            caller_contact_id=caller_contact_id,
        )
        _CALLS[call_sid] = record
        return record

    async def get(self, call_sid: str) -> VoiceCallRecord | None:
        return _CALLS.get(call_sid)

    async def list(self) -> list[VoiceCallRecord]:
        return sorted(_CALLS.values(), key=lambda record: record.started_at, reverse=True)

    async def save(self, record: VoiceCallRecord) -> VoiceCallRecord:
        _CALLS[record.call_sid] = record
        return record


def reset_call_store() -> None:
    _CALLS.clear()
