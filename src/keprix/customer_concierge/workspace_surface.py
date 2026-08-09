"""Operator workspace aggregations: bookings, channels, analytics (Prompt 634)."""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.capability_mesh import build_booking_mesh, spreadsheet_rows_for_workspace
from keprix.customer_concierge.capability_health import evaluate_capability_health
from keprix.customer_concierge.store import get_concierge_store


CHANNEL_KEYS = ("web", "telegram", "whatsapp", "email", "sms", "voice")


def list_unified_bookings(workspace_id: str, *, limit: int = 100) -> dict[str, Any]:
    """One booking record set across viCal + Outreach Soft Wall + mesh links."""
    from keprix.vical.store import vical_store

    bookings = vical_store.list_bookings(workspace_id)[:limit]
    items = []
    for b in bookings:
        mesh = build_booking_mesh(b, workspace_id=workspace_id)
        items.append(
            {
                "id": b.id,
                "guestName": b.guest_name,
                "guestEmail": b.guest_email,
                "status": b.status,
                "startsAt": b.starts_at.isoformat() if b.starts_at else None,
                "endsAt": b.ends_at.isoformat() if b.ends_at else None,
                "meetingUrl": b.meeting_url,
                "source": b.source,
                "mesh": mesh["mesh"],
                "chain": mesh["chain"],
                "invitation": mesh.get("invitation"),
                "spreadsheetRow": mesh["spreadsheetRow"],
                "oneRecord": True,
            }
        )

    outreach_rows: list[dict[str, Any]] = []
    try:
        from keprix.outreach.ops import get_outreach_ops_store

        for row in get_outreach_ops_store().list_bookings(workspace_id)[:limit]:
            notes = str(row.get("notes") or "")
            vical_id = None
            if "vical:" in notes:
                vical_id = notes.split("vical:", 1)[1].split()[0]
            outreach_rows.append(
                {
                    "id": row.get("id"),
                    "leadId": row.get("lead_id"),
                    "status": row.get("status"),
                    "startsAt": row.get("starts_at"),
                    "vicalBookingId": vical_id,
                    "linkedToVical": bool(vical_id),
                    "href": "/outreach/bookings",
                }
            )
    except Exception:
        pass

    return {
        "workspaceId": workspace_id,
        "bookings": items,
        "outreachBookings": outreach_rows,
        "spreadsheetRows": spreadsheet_rows_for_workspace(workspace_id, limit=limit),
        "oneRecordSet": True,
        "sources": ["vical", "outreach_soft_wall"],
    }


def channel_surface(workspace_id: str, *, persona_id: str = "default") -> dict[str, Any]:
    profile = get_concierge_store().get(workspace_id, persona_id)
    cfg = dict((profile.channel_config if profile else {}) or {})
    health = evaluate_capability_health(workspace_id=workspace_id, persona_id=persona_id)
    channels = []
    for key in CHANNEL_KEYS:
        entry = cfg.get(key) if isinstance(cfg.get(key), dict) else {"enabled": bool(cfg.get(key))}
        enabled = bool((entry or {}).get("enabled"))
        channels.append(
            {
                "key": key,
                "enabled": enabled,
                "connected": enabled and key == "web" and bool(profile and profile.published),
                "consentRequired": key in {"email", "sms", "whatsapp", "telegram"},
                "originatingThreadOnly": True,
                "suppressionRespected": True,
                "setup": {
                    "web": "Public embed at /embed/concierge/{workspaceId}/{personaId}",
                    "telegram": "Gateway channel/session + bot token in Vault (not owner session)",
                    "whatsapp": "Gateway channel/session + provider credentials",
                    "email": "Inbound mailbox + consent; replies stay in thread",
                    "sms": "Optional; requires KEPRIX_VICAL_SMS_ON_CONFIRM style gate",
                    "voice": "Phone receptionist surface; audience principal only",
                }.get(key),
                "audienceToolsOnly": True,
            }
        )
    return {
        "workspaceId": workspace_id,
        "personaId": persona_id,
        "published": bool(profile.published) if profile else False,
        "channels": channels,
        "embedUrl": (
            f"/embed/concierge/{workspace_id}/{persona_id}" if profile and profile.published else None
        ),
        "gatewaySessionPath": f"/api/customer-concierge/public/{workspace_id}/{persona_id}/channel/session",
        "capabilityHealth": {
            "ready": health.get("ready"),
            "features": {
                k: {"status": v.get("status"), "detail": v.get("detail")}
                for k, v in (health.get("features") or {}).items()
            },
        },
        "note": "Channel replies remain in the originating thread and respect consent/suppression.",
    }


def update_channel_surface(
    workspace_id: str,
    *,
    persona_id: str = "default",
    channels: dict[str, Any],
) -> dict[str, Any]:
    store = get_concierge_store()
    profile = store.get(workspace_id, persona_id)
    if not profile:
        raise ValueError("profile_not_found")
    merged = dict(profile.channel_config or {})
    meeting_types = merged.pop("meetingTypes", None) or []
    for key, value in channels.items():
        if key not in CHANNEL_KEYS and key != "policy":
            continue
        if isinstance(value, dict):
            merged[key] = {**(merged.get(key) if isinstance(merged.get(key), dict) else {}), **value}
        else:
            merged[key] = {"enabled": bool(value)}
    hours = profile.business_hours or {"timezone": "UTC", "windows": []}
    updated = store.upsert_step2(
        workspace_id=workspace_id,
        persona_id=persona_id,
        channels=merged,
        business_hours=hours if isinstance(hours, dict) else {"timezone": "UTC", "windows": []},
        calendar_provider=profile.calendar_provider,
        conferencing_provider=profile.conferencing_provider,
        calendar_connected=bool(profile.calendar_connected),
        conferencing_connected=bool(profile.conferencing_connected),
        meeting_types=meeting_types if isinstance(meeting_types, list) else [],
        ics_fallback_ok=bool(getattr(profile, "ics_fallback_ok", True)),
    )
    return channel_surface(workspace_id, persona_id=persona_id) | {
        "ok": True,
        "profileId": updated.id if updated else None,
    }


def analytics_surface(workspace_id: str, *, persona_id: str = "default") -> dict[str, Any]:
    """Event-derived, privacy-safe metrics (no message bodies or PII dumps)."""
    from keprix.customer_concierge.audience.store import get_audience_store
    from keprix.customer_concierge.support_cases import get_support_case_store
    from keprix.vical.store import vical_store

    audits = get_audience_store().list_audit(workspace_id, limit=500)
    event_counts: dict[str, int] = {}
    for row in audits:
        et = str(row.get("eventType") or "unknown")
        event_counts[et] = event_counts.get(et, 0) + 1

    bookings = vical_store.list_bookings(workspace_id)
    by_status: dict[str, int] = {}
    for b in bookings:
        by_status[b.status] = by_status.get(b.status, 0) + 1

    cases = get_support_case_store().list_cases(workspace_id, persona_id=persona_id)
    case_by_status: dict[str, int] = {}
    for c in cases:
        st = str(c.get("status") if isinstance(c, dict) else getattr(c, "status", "unknown"))
        case_by_status[st] = case_by_status.get(st, 0) + 1

    confirmed = by_status.get("confirmed", 0)
    cancelled = by_status.get("cancelled", 0)
    return {
        "workspaceId": workspace_id,
        "personaId": persona_id,
        "privacySafe": True,
        "includesMessageBodies": False,
        "includesHostStartUrls": False,
        "metrics": {
            "sessionsStarted": event_counts.get("session.opened", 0)
            + event_counts.get("audience.session_opened", 0),
            "handoffs": event_counts.get("handoff.requested", 0),
            "takeovers": event_counts.get("handoff.takeover", 0),
            "bookingsTotal": len(bookings),
            "bookingsByStatus": by_status,
            "confirmedBookings": confirmed,
            "cancelledBookings": cancelled,
            "supportCasesByStatus": case_by_status,
            "auditEvents": len(audits),
        },
        "eventCounts": event_counts,
        "derived": {
            "confirmRate": (confirmed / len(bookings)) if bookings else 0.0,
            "cancelRate": (cancelled / len(bookings)) if bookings else 0.0,
        },
    }


__all__ = [
    "analytics_surface",
    "channel_surface",
    "list_unified_bookings",
    "update_channel_surface",
]
