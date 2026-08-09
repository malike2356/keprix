"""Concierge profile models (Prompt 628)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class MeetingType:
    id: str
    name: str
    duration_minutes: int
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "durationMinutes": self.duration_minutes,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MeetingType:
        return cls(
            id=str(raw.get("id") or uuid4()),
            name=str(raw.get("name") or "").strip(),
            duration_minutes=int(raw.get("durationMinutes") or raw.get("duration_minutes") or 30),
            description=str(raw.get("description") or ""),
        )


@dataclass
class ConciergeProfile:
    id: str
    workspace_id: str
    persona_id: str
    published: bool = False
    published_at: str | None = None
    persona_name: str | None = None
    greeting_message: str | None = None
    business_name: str | None = None
    business_description: str | None = None
    knowledge_source_ids: list[str] = field(default_factory=list)
    meeting_type_ids: list[str] = field(default_factory=list)
    channel_config: dict[str, Any] = field(default_factory=dict)
    calendar_provider: str | None = None
    calendar_connected: bool = False
    conferencing_provider: str | None = None
    conferencing_connected: bool = False
    business_hours: dict[str, Any] | None = None
    escalation_email: str | None = None
    ics_fallback_ok: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspaceId": self.workspace_id,
            "personaId": self.persona_id,
            "published": self.published,
            "publishedAt": self.published_at,
            "personaName": self.persona_name,
            "greetingMessage": self.greeting_message,
            "businessName": self.business_name,
            "businessDescription": self.business_description,
            "knowledgeSourceIds": list(self.knowledge_source_ids),
            "meetingTypeIds": list(self.meeting_type_ids),
            "channelConfig": dict(self.channel_config or {}),
            "calendarProvider": self.calendar_provider,
            "calendarConnected": self.calendar_connected,
            "conferencingProvider": self.conferencing_provider,
            "conferencingConnected": self.conferencing_connected,
            "businessHours": self.business_hours,
            "escalationEmail": self.escalation_email,
            "icsFallbackOk": self.ics_fallback_ok,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ConciergeProfile:
        import json

        def _json(val: Any, default: Any) -> Any:
            if val is None:
                return default
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return default

        return cls(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            persona_id=str(row["persona_id"]),
            published=bool(row.get("published")),
            published_at=row.get("published_at"),
            persona_name=row.get("persona_name"),
            greeting_message=row.get("greeting_message"),
            business_name=row.get("business_name"),
            business_description=row.get("business_description"),
            knowledge_source_ids=_json(row.get("knowledge_source_ids"), []),
            meeting_type_ids=_json(row.get("meeting_type_ids"), []),
            channel_config=_json(row.get("channel_config"), {}),
            calendar_provider=row.get("calendar_provider"),
            calendar_connected=bool(row.get("calendar_connected")),
            conferencing_provider=row.get("conferencing_provider"),
            conferencing_connected=bool(row.get("conferencing_connected")),
            business_hours=_json(row.get("business_hours"), None),
            escalation_email=row.get("escalation_email"),
            ics_fallback_ok=bool(row.get("ics_fallback_ok", True)),
            created_at=str(row.get("created_at") or _now()),
            updated_at=str(row.get("updated_at") or _now()),
        )


@dataclass
class ConciergeSession:
    """Lightweight visitor session (full audience principal in Prompt 630)."""

    id: str
    workspace_id: str
    persona_id: str
    profile_id: str
    active: bool = True
    created_at: str = field(default_factory=_now)
    closed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
