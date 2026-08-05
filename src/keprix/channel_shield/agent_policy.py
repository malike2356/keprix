"""Per-agent Channel Shield policy controls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentShieldPolicy:
    agent_id: str
    label: str = ""
    can_view_safe_summary: bool = True
    can_request_release: bool = True
    can_release_after_approval: bool = False
    can_destroy: bool = False
    can_notify_recipients: bool = True
    can_contact_external_senders: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "label": self.label or self.agent_id,
            "canViewSafeSummary": self.can_view_safe_summary,
            "canRequestRelease": self.can_request_release,
            "canReleaseAfterApproval": self.can_release_after_approval,
            "canDestroy": self.can_destroy,
            "canNotifyRecipients": self.can_notify_recipients,
            "canContactExternalSenders": self.can_contact_external_senders,
        }


DEFAULT_POLICIES: dict[str, AgentShieldPolicy] = {
    "assistant": AgentShieldPolicy(
        agent_id="assistant",
        label="Default assistant",
        can_view_safe_summary=True,
        can_request_release=True,
        can_release_after_approval=False,
        can_destroy=False,
        can_notify_recipients=True,
        can_contact_external_senders=False,
    ),
    "employee-agent": AgentShieldPolicy(
        agent_id="employee-agent",
        label="Employee agent",
        can_view_safe_summary=True,
        can_request_release=True,
        can_release_after_approval=False,
        can_destroy=False,
        can_notify_recipients=True,
        can_contact_external_senders=False,
    ),
    "warden": AgentShieldPolicy(
        agent_id="warden",
        label="WARDEN / security persona",
        can_view_safe_summary=True,
        can_request_release=True,
        can_release_after_approval=True,
        can_destroy=True,
        can_notify_recipients=True,
        can_contact_external_senders=False,
    ),
}


def get_agent_policy(agent_id: str, overrides: dict[str, Any] | None = None) -> AgentShieldPolicy:
    base = DEFAULT_POLICIES.get(agent_id) or AgentShieldPolicy(agent_id=agent_id)
    if not overrides:
        return base
    return AgentShieldPolicy(
        agent_id=agent_id,
        label=str(overrides.get("label") or base.label),
        can_view_safe_summary=bool(
            overrides.get("can_view_safe_summary", base.can_view_safe_summary)
        ),
        can_request_release=bool(
            overrides.get("can_request_release", base.can_request_release)
        ),
        can_release_after_approval=bool(
            overrides.get("can_release_after_approval", base.can_release_after_approval)
        ),
        can_destroy=bool(overrides.get("can_destroy", base.can_destroy)),
        can_notify_recipients=bool(
            overrides.get("can_notify_recipients", base.can_notify_recipients)
        ),
        can_contact_external_senders=bool(
            overrides.get("can_contact_external_senders", base.can_contact_external_senders)
        ),
    )


def list_default_policies() -> list[dict[str, Any]]:
    return [p.to_dict() for p in DEFAULT_POLICIES.values()]
