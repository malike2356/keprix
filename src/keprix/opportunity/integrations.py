"""Optional integration discovery for Opportunity Engine launch orchestration."""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field

IntegrationKind = Literal[
    "crm",
    "email",
    "ads",
    "social",
    "website",
    "analytics",
    "stripe",
    "calendar",
    "forms",
]

INTEGRATION_LABELS: dict[IntegrationKind, str] = {
    "crm": "CRM",
    "email": "Email platform",
    "ads": "Ads manager",
    "social": "Social account",
    "website": "Website or landing page builder",
    "analytics": "Analytics",
    "stripe": "Stripe",
    "calendar": "Calendar",
    "forms": "Form tool",
}

SETUP_INSTRUCTIONS: dict[IntegrationKind, str] = {
    "crm": "Connect contacts/CRM in Settings > Contacts or set KEPRIX_INTEGRATION_CRM=connected.",
    "email": "Add an email account under Settings > Email or set KEPRIX_INTEGRATION_EMAIL=connected.",
    "ads": "Connect an ads manager integration or set KEPRIX_INTEGRATION_ADS=connected.",
    "social": "Link a social publishing account or set KEPRIX_INTEGRATION_SOCIAL=connected.",
    "website": "Configure site deploy target or set KEPRIX_INTEGRATION_WEBSITE=connected.",
    "analytics": "Connect analytics (GA4, Plausible, etc.) or set KEPRIX_INTEGRATION_ANALYTICS=connected.",
    "stripe": "Add Stripe API keys in billing settings or set KEPRIX_INTEGRATION_STRIPE=connected.",
    "calendar": "Connect calendar sync or set KEPRIX_INTEGRATION_CALENDAR=connected.",
    "forms": "Configure form tool (Typeform, Tally, etc.) or set KEPRIX_INTEGRATION_FORMS=connected.",
}


class IntegrationStatus(BaseModel):
    kind: IntegrationKind
    label: str
    connected: bool = False
    provider: str | None = None
    setup_instructions: str = ""


class IntegrationReport(BaseModel):
    connected: list[IntegrationStatus] = Field(default_factory=list)
    missing: list[IntegrationStatus] = Field(default_factory=list)
    pending_tasks: list[dict[str, str]] = Field(default_factory=list)


def _env_connected(kind: IntegrationKind) -> bool:
    key = f"KEPRIX_INTEGRATION_{kind.upper()}"
    return os.environ.get(key, "").lower() in {"1", "true", "connected", "yes"}


def _meta_override(meta: dict[str, Any] | None, kind: IntegrationKind) -> bool | None:
    if not meta:
        return None
    integrations = meta.get("integrations_config") or {}
    if kind in integrations:
        return bool(integrations[kind])
    return None


def _probe_email() -> tuple[bool, str | None]:
    if _env_connected("email"):
        return True, "env"
    return False, None


def _probe_crm() -> tuple[bool, str | None]:
    if _env_connected("crm"):
        return True, "env"
    return False, None


def _probe_calendar() -> tuple[bool, str | None]:
    if _env_connected("calendar"):
        return True, "env"
    try:
        from keprix.workspace.calendar import get_calendar_store  # type: ignore[attr-defined]

        get_calendar_store()
        return True, "keprix.workspace.calendar"
    except Exception:
        return False, None


_PROBE_HANDLERS: dict[IntegrationKind, Any] = {
    "email": _probe_email,
    "crm": _probe_crm,
    "calendar": _probe_calendar,
}


def probe_integration(kind: IntegrationKind, *, meta: dict[str, Any] | None = None) -> IntegrationStatus:
    override = _meta_override(meta, kind)
    if override is True:
        return IntegrationStatus(
            kind=kind,
            label=INTEGRATION_LABELS[kind],
            connected=True,
            provider="configured",
            setup_instructions=SETUP_INSTRUCTIONS[kind],
        )
    if override is False:
        return IntegrationStatus(
            kind=kind,
            label=INTEGRATION_LABELS[kind],
            connected=False,
            setup_instructions=SETUP_INSTRUCTIONS[kind],
        )

    handler = _PROBE_HANDLERS.get(kind)
    if handler:
        connected, provider = handler()
    else:
        connected = _env_connected(kind)
        provider = "env" if connected else None

    return IntegrationStatus(
        kind=kind,
        label=INTEGRATION_LABELS[kind],
        connected=connected,
        provider=provider,
        setup_instructions=SETUP_INSTRUCTIONS[kind],
    )


def discover_integrations(*, meta: dict[str, Any] | None = None) -> IntegrationReport:
    connected: list[IntegrationStatus] = []
    missing: list[IntegrationStatus] = []
    pending_tasks: list[dict[str, str]] = []

    for kind in INTEGRATION_LABELS:
        status = probe_integration(kind, meta=meta)
        if status.connected:
            connected.append(status)
        else:
            missing.append(status)
            pending_tasks.append(
                {
                    "integration": kind,
                    "task": f"Connect {status.label}",
                    "instructions": status.setup_instructions,
                },
            )

    return IntegrationReport(connected=connected, missing=missing, pending_tasks=pending_tasks)
