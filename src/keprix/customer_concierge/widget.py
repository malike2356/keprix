"""Public widget helpers (Prompt 628)."""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.models import ConciergeProfile


def public_widget_embed(workspace_id: str, persona_id: str) -> dict[str, str]:
    path = f"/embed/concierge/{workspace_id}/{persona_id}"
    snippet = (
        f'<iframe src="{path}" title="Keprix Customer Concierge" '
        f'width="400" height="640" style="border:0;border-radius:8px;"></iframe>'
    )
    return {"publicUrl": path, "embedSnippet": snippet}


def public_widget_status(profile: ConciergeProfile | None) -> dict[str, Any]:
    from keprix.customer_concierge.audience_mode import get_audience_mode

    if not profile or not profile.published or get_audience_mode(profile.workspace_id) == "team":
        return {
            "published": False,
            "acceptingNewSessions": False,
            "greeting": None,
            "personaName": profile.persona_name if profile else None,
            "businessName": profile.business_name if profile else None,
        }
    return {
        "published": True,
        "acceptingNewSessions": True,
        "greeting": profile.greeting_message,
        "personaName": profile.persona_name,
        "businessName": profile.business_name,
        **public_widget_embed(profile.workspace_id, profile.persona_id),
    }


def gate_new_widget_session(profile: ConciergeProfile | None) -> dict[str, Any]:
    """Reject new widget sessions when unpublished."""
    if not profile:
        return {"ok": False, "error_code": "not_found"}
    if not profile.published:
        return {"ok": False, "error_code": "concierge_unpublished"}
    from keprix.customer_concierge.audience_mode import get_audience_mode

    if get_audience_mode(profile.workspace_id) == "team":
        return {"ok": False, "error_code": "customer_concierge_disabled"}
    web = (profile.channel_config or {}).get("web") or {}
    if not web.get("enabled"):
        return {"ok": False, "error_code": "web_channel_disabled"}
    return {"ok": True}
