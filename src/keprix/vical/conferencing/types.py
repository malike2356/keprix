"""Conferencing adapter protocol (Prompt 632)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class ConferenceCreateInput:
    workspace_id: str
    user_id: str
    persona_id: str | None
    topic: str
    starts_at: str
    duration_minutes: int
    timezone: str = "UTC"
    idempotency_key: str = ""
    host_email: str | None = None
    agenda: str | None = None


@dataclass
class ConferenceUpdateInput:
    workspace_id: str
    user_id: str
    meeting_id: str
    topic: str | None = None
    starts_at: str | None = None
    duration_minutes: int | None = None
    timezone: str | None = None
    idempotency_key: str = ""


@dataclass
class ConferenceDeleteInput:
    workspace_id: str
    user_id: str
    meeting_id: str
    idempotency_key: str = ""


@dataclass
class ConferenceAdapterResult:
    ok: bool
    provider: str
    status: str
    meeting_id: str | None = None
    join_url: str | None = None
    # Private: never serialize to public DTOs / logs / prompts
    host_start_url: str | None = None
    passcode: str | None = None
    duplicate: bool = False
    error_code: str | None = None
    detail: str | None = None
    managed: bool = False
    retry_after_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "status": self.status,
            "meetingId": self.meeting_id,
            "joinUrl": self.join_url,
            "passcode": self.passcode,
            "duplicate": self.duplicate,
            "errorCode": self.error_code,
            "detail": self.detail,
            "managed": self.managed,
            # host_start_url intentionally omitted
        }


class ConferencingAdapter(Protocol):
    provider: Literal["zoom", "static_url"]

    def create_meeting(self, input: ConferenceCreateInput) -> ConferenceAdapterResult: ...

    def update_meeting(self, input: ConferenceUpdateInput) -> ConferenceAdapterResult: ...

    def delete_meeting(self, input: ConferenceDeleteInput) -> ConferenceAdapterResult: ...
