"""Audience principal models (Prompt 630)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


AudienceSessionMode = Literal["public", "preview"]
AudienceConsentState = Literal["unknown", "granted", "denied", "withdrawn"]
AudienceRiskState = Literal["normal", "elevated", "blocked"]
AudienceSessionStatus = Literal["active", "handed_off", "closed"]


@dataclass
class AudienceIdentity:
    id: str
    workspace_id: str
    channel: str
    external_key: str
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    crm_contact_id: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspaceId": self.workspace_id,
            "channel": self.channel,
            "externalKey": self.external_key,
            "displayName": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "crmContactId": self.crm_contact_id,
            "actorType": "audience",
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class AudienceSession:
    id: str
    workspace_id: str
    persona_id: str
    concierge_profile_id: str | None
    identity_id: str
    channel: str
    session_mode: AudienceSessionMode
    widget_session_token: str | None
    origin: str | None
    locale: str | None
    consent_state: AudienceConsentState
    risk_state: AudienceRiskState
    status: AudienceSessionStatus
    expires_at: str
    last_active_at: str
    created_at: str
    # Never a workspace member
    principal: str = "audience_session"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {
            "id": d["id"],
            "workspaceId": d["workspace_id"],
            "personaId": d["persona_id"],
            "conciergeProfileId": d["concierge_profile_id"],
            "identityId": d["identity_id"],
            "channel": d["channel"],
            "sessionMode": d["session_mode"],
            "widgetSessionToken": d["widget_session_token"],
            "origin": d["origin"],
            "locale": d["locale"],
            "consentState": d["consent_state"],
            "riskState": d["risk_state"],
            "status": d["status"],
            "expiresAt": d["expires_at"],
            "lastActiveAt": d["last_active_at"],
            "createdAt": d["created_at"],
            "principal": "audience_session",
            "actorType": "audience",
            "workspaceMember": False,
        }


def is_audience_session_usable(session: AudienceSession) -> bool:
    if session.status not in {"active", "handed_off"}:
        return False
    if session.risk_state == "blocked":
        return False
    try:
        if datetime.fromisoformat(session.expires_at.replace("Z", "+00:00")).timestamp() <= datetime.now(
            timezone.utc
        ).timestamp():
            return False
    except Exception:
        return False
    return True
