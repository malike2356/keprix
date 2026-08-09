"""Concierge publish readiness (Prompt 628)."""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.models import ConciergeProfile
from keprix.customer_concierge.store import ConciergeProfileStore, get_concierge_store


def resolve_calendar_connected(provider: str | None) -> bool:
    """Best-effort: provider selected and workspace calendar/viCal available."""
    if not provider:
        return False
    provider = provider.strip().lower()
    try:
        if provider in {"google", "microsoft", "caldav"}:
            # Prefer workspace calendar sources when present
            from keprix.workspace import calendar_sync  # type: ignore

            sources = getattr(calendar_sync, "list_sources", None)
            if callable(sources):
                items = sources() or []
                if items:
                    return True
    except Exception:
        pass
    try:
        from keprix.vical.store import get_vical_store

        store = get_vical_store()
        hosts = getattr(store, "list_host_profiles", None) or getattr(store, "host_profiles", None)
        if callable(hosts):
            return bool(hosts())
        if isinstance(hosts, dict):
            return bool(hosts)
    except Exception:
        pass
    # Explicit operator-set connection flag is refreshed by routes; default false for CE honesty
    return False


def resolve_conferencing_connected(provider: str | None) -> bool:
    if not provider:
        return False
    provider = provider.strip().lower()
    try:
        from keprix.vical import conferencing

        if provider in {"zoom", "google_meet", "meet", "url", "template"}:
            # Connected only when a template/URL helper reports configured
            check = getattr(conferencing, "is_configured", None)
            if callable(check):
                return bool(check(provider))
            tmpl = getattr(conferencing, "default_meeting_url_template", None)
            if callable(tmpl):
                return bool(tmpl())
            if isinstance(tmpl, str) and tmpl.strip():
                return True
    except Exception:
        pass
    return False


def evaluate_readiness(
    workspace_id: str,
    persona_id: str,
    *,
    store: ConciergeProfileStore | None = None,
) -> dict[str, Any]:
    store = store or get_concierge_store()
    profile = store.get(workspace_id, persona_id)
    if profile:
        cal = resolve_calendar_connected(profile.calendar_provider) or profile.calendar_connected
        conf = resolve_conferencing_connected(profile.conferencing_provider) or profile.conferencing_connected
        # ICS-only fallback: when no online calendar provider is required, keep calendar optional
        store.update_connection_flags(
            workspace_id,
            persona_id,
            calendar_connected=cal,
            conferencing_connected=conf,
        )
        profile = store.get(workspace_id, persona_id)

    checks: list[dict[str, str]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    has_profile = bool(
        profile
        and profile.persona_name
        and profile.business_name
        and profile.greeting_message
        and profile.escalation_email
    )
    checks.append(
        {"key": "profile", "label": "Concierge profile", "status": "done" if has_profile else "missing"}
    )
    if not has_profile:
        blockers.append("profile")

    channels = (profile.channel_config if profile else {}) or {}
    channel_enabled = bool(
        (channels.get("web") or {}).get("enabled")
        or (channels.get("telegram") or {}).get("enabled")
        or (channels.get("whatsapp") or {}).get("enabled")
        or (channels.get("email") or {}).get("enabled")
    )
    checks.append(
        {
            "key": "channels",
            "label": "At least one channel",
            "status": "done" if channel_enabled else "missing",
        }
    )
    if not channel_enabled:
        blockers.append("channels")

    knowledge_ok = bool(profile and profile.knowledge_source_ids)
    checks.append(
        {
            "key": "knowledge",
            "label": "Published knowledge source",
            "status": "done" if knowledge_ok else "warning",
        }
    )
    if not knowledge_ok:
        warnings.append("knowledge")

    meeting_types = list((channels.get("meetingTypes") or []) if profile else [])
    has_calendar_provider = bool(profile and profile.calendar_provider)
    has_conf_provider = bool(profile and profile.conferencing_provider)

    if has_calendar_provider:
        calendar_ok = bool(profile and profile.calendar_connected)
        checks.append(
            {
                "key": "calendar",
                "label": "Calendar connected",
                "status": "done" if calendar_ok else "missing",
            }
        )
        if not calendar_ok:
            blockers.append("calendar")
    elif meeting_types:
        checks.append({"key": "calendar", "label": "Calendar (ICS fallback)", "status": "warning"})
        warnings.append("calendar_ics_fallback")
    else:
        checks.append({"key": "calendar", "label": "Calendar connected", "status": "done"})

    if has_conf_provider:
        conf_ok = bool(profile and profile.conferencing_connected)
        checks.append(
            {
                "key": "conferencing",
                "label": "Conferencing connected",
                "status": "done" if conf_ok else "missing",
            }
        )
        if not conf_ok:
            blockers.append("conferencing")
    elif meeting_types:
        checks.append(
            {
                "key": "conferencing",
                "label": "Conferencing (optional ICS-only)",
                "status": "warning",
            }
        )
        warnings.append("conferencing_optional")
    else:
        checks.append({"key": "conferencing", "label": "Conferencing connected", "status": "done"})

    ready = len(blockers) == 0 and has_profile and channel_enabled
    return {
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "profile": profile.to_dict() if profile else None,
    }


def profile_has_meeting_types(profile: ConciergeProfile | None) -> bool:
    if not profile:
        return False
    mts = (profile.channel_config or {}).get("meetingTypes") or []
    return len(mts) > 0
