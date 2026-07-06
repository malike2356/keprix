"""Notification schemas and constants (Prompt 24)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

NOTIFICATION_TYPES = frozenset(
    {
        "approval_needed",
        "job_complete",
        "job_failed",
        "scheduled_task_failed",
        "setup_needs_attention",
        "credential_expiring",
        "usage_limit_warning",
        "llm_budget_alert",
        "billing_failed",
        "subscription_changed",
        "security_alert",
        "governance_policy_alert",
        "data_import_complete",
        "research_complete",
        "ml_experiment_complete",
        "pack_gate_pending",
        "localization_correction",
    }
)

SEVERITY_LEVELS = frozenset({"info", "warning", "critical"})

CHANNELS = frozenset(
    {
        "in_app",
        "email",
        "push",
        "slack",
        "telegram",
        "discord",
        "webchat",
    }
)

GROUP_CHANNELS = frozenset({"slack", "telegram", "discord", "webchat"})

DEFAULT_CHANNELS_BY_SEVERITY: dict[str, list[str]] = {
    "info": ["in_app"],
    "warning": ["in_app", "email"],
    "critical": ["in_app", "email", "push"],
}


class NotificationPreferences(BaseModel):
    workspace_id: str = "default"
    user_id: str = "default"
    channels_enabled: dict[str, bool] = Field(
        default_factory=lambda: {
            "in_app": True,
            "email": True,
            "push": True,
            "slack": False,
            "telegram": False,
            "discord": False,
            "webchat": False,
        }
    )
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    quiet_hours_timezone: str = "UTC"
    digest_enabled: bool = True
    escalation_delay_minutes: int = Field(default=60, ge=5, le=1440)


class NotificationDispatchBody(BaseModel):
    notification_type: str
    severity: Literal["info", "warning", "critical"] = "info"
    title: str
    message: str
    user_id: str | None = None
    href: str | None = None
    sensitive: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "system"
    source_id: str | None = None
    workspace_id: str = "default"


class PreferencesUpdateBody(BaseModel):
    channels_enabled: dict[str, bool] | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    quiet_hours_timezone: str | None = None
    digest_enabled: bool | None = None
    escalation_delay_minutes: int | None = Field(default=None, ge=5, le=1440)
