"""Capability mesh: one booking chain across viCal, calendar, CRM, outreach (634)."""

from __future__ import annotations

from typing import Any


def _booking_fields(booking: Any) -> dict[str, Any]:
    if isinstance(booking, dict):
        meta = dict(booking.get("metadata") or {})
        return {
            "id": str(booking.get("id") or ""),
            "guestEmail": str(booking.get("guest_email") or booking.get("guestEmail") or ""),
            "guestName": str(booking.get("guest_name") or booking.get("guestName") or ""),
            "status": str(booking.get("status") or ""),
            "startsAt": str(booking.get("starts_at") or booking.get("startsAt") or ""),
            "endsAt": str(booking.get("ends_at") or booking.get("endsAt") or ""),
            "meetingUrl": booking.get("meeting_url") or booking.get("meetingUrl"),
            "contactId": booking.get("contact_id") or booking.get("contactId"),
            "workspaceEventId": booking.get("workspace_event_id") or booking.get("workspaceEventId"),
            "metadata": meta,
            "userId": str(booking.get("user_id") or booking.get("userId") or ""),
        }
    meta = dict(getattr(booking, "metadata", None) or {})
    return {
        "id": str(booking.id),
        "guestEmail": str(booking.guest_email or ""),
        "guestName": str(booking.guest_name or ""),
        "status": str(booking.status),
        "startsAt": booking.starts_at.isoformat() if booking.starts_at else "",
        "endsAt": booking.ends_at.isoformat() if booking.ends_at else "",
        "meetingUrl": booking.meeting_url,
        "contactId": booking.contact_id,
        "workspaceEventId": booking.workspace_event_id,
        "metadata": meta,
        "userId": str(booking.user_id),
    }


def build_booking_mesh(
    booking: Any,
    *,
    workspace_id: str | None = None,
    audience_session_id: str | None = None,
    support_case_id: str | None = None,
) -> dict[str, Any]:
    """Return the complete operator-visible chain for one booking record."""
    fields = _booking_fields(booking)
    meta = fields["metadata"]
    ws = (
        workspace_id
        or meta.get("workspace_id")
        or meta.get("outreach_workspace_id")
        or fields["userId"]
        or "default"
    )
    booking_id = fields["id"]

    crm_lead_id = meta.get("crm_lead_id")
    crm_contact_id = meta.get("crm_contact_id") or fields.get("contactId")
    outreach_lead_id = meta.get("outreach_lead_id") or meta.get("lead_id")
    campaign_id = meta.get("campaign_id") or meta.get("outreach_campaign_id")
    sequence_id = meta.get("sequence_id")
    conversation_id = meta.get("conversation_id") or audience_session_id
    case_id = support_case_id or meta.get("support_case_id")
    zoom_meeting_id = meta.get("zoomMeetingId") or meta.get("zoom_meeting_id")
    calendar_provider = meta.get("calendarProvider") or meta.get("calendar_provider")
    outcome = meta.get("session_outcome") or meta.get("outcome")
    conversion = meta.get("conversion") or meta.get("converted")

    calendar_projection = None
    invitation = None
    try:
        from keprix.vical.calendar.delivery_state import booking_invitation_view
        from keprix.vical.calendar.projection_store import get_projection_store

        projection = get_projection_store().get_projection(str(ws), booking_id)
        calendar_projection = projection
        invitation = booking_invitation_view(projection)
        if projection and not calendar_provider:
            calendar_provider = projection.get("provider")
    except Exception:
        pass

    conference = None
    try:
        from keprix.vical.saga.ledger import get_saga_ledger

        conference = get_saga_ledger().get_conference_artifact(str(ws), booking_id, provider="zoom")
        if conference and not zoom_meeting_id:
            zoom_meeting_id = conference.get("meetingId")
    except Exception:
        pass

    chain = [
        {"key": "audienceSession", "id": conversation_id, "href": f"/concierge?session={conversation_id}" if conversation_id else None},
        {"key": "contact", "id": crm_contact_id, "href": f"/crm/contacts/{crm_contact_id}" if crm_contact_id else None},
        {"key": "lead", "id": crm_lead_id, "href": f"/crm/leads/{crm_lead_id}" if crm_lead_id else None},
        {"key": "company", "id": meta.get("company_id"), "href": f"/crm/companies/{meta.get('company_id')}" if meta.get("company_id") else None},
        {"key": "campaign", "id": campaign_id, "href": f"/outreach/campaigns/{campaign_id}" if campaign_id else None},
        {"key": "sequence", "id": sequence_id, "href": f"/outreach/sequences/{sequence_id}" if sequence_id else None},
        {"key": "outreachLead", "id": outreach_lead_id, "href": f"/outreach/leads/{outreach_lead_id}" if outreach_lead_id else None},
        {"key": "conversation", "id": conversation_id, "href": f"/concierge?tab=conversations&session={conversation_id}" if conversation_id else None},
        {"key": "supportCase", "id": case_id, "href": f"/concierge?tab=conversations&case={case_id}" if case_id else None},
        {"key": "booking", "id": booking_id, "href": f"/vical?booking={booking_id}"},
        {
            "key": "workspaceCalendarEvent",
            "id": fields.get("workspaceEventId"),
            "href": "/calendar" if fields.get("workspaceEventId") else None,
        },
        {
            "key": "externalCalendarEvent",
            "id": (calendar_projection or {}).get("providerEventId") if calendar_projection else None,
            "provider": calendar_provider,
            "href": (calendar_projection or {}).get("htmlLink") if calendar_projection else None,
        },
        {
            "key": "zoomArtifact",
            "id": zoom_meeting_id,
            "managed": bool(meta.get("conferenceManaged")),
            "joinUrl": fields.get("meetingUrl") if meta.get("conferenceProvider") == "zoom" else None,
        },
        {"key": "outcome", "id": outcome},
        {"key": "conversion", "id": conversion},
    ]

    return {
        "workspaceId": ws,
        "bookingId": booking_id,
        "status": fields["status"],
        "guest": {"email": fields["guestEmail"], "name": fields["guestName"]},
        "startsAt": fields["startsAt"],
        "endsAt": fields["endsAt"],
        "meetingUrl": fields["meetingUrl"],
        "invitation": invitation,
        "calendarProjection": {
            "provider": (calendar_projection or {}).get("provider") if calendar_projection else None,
            "providerEventId": (calendar_projection or {}).get("providerEventId") if calendar_projection else None,
            "hostEventCreated": bool((calendar_projection or {}).get("hostEventCreated")) if calendar_projection else False,
            "invitationDeliveryState": (calendar_projection or {}).get("invitationDeliveryState") if calendar_projection else "unknown",
        },
        "conference": {
            "provider": meta.get("conferenceProvider") or ("zoom" if conference else None),
            "meetingId": zoom_meeting_id,
            "managed": bool(meta.get("conferenceManaged")),
            "joinUrl": fields.get("meetingUrl"),
        },
        "chain": chain,
        "mesh": {
            "vical": f"/vical?booking={booking_id}",
            "calendar": "/calendar",
            "crmLead": f"/crm/leads/{crm_lead_id}" if crm_lead_id else None,
            "crmContact": f"/crm/contacts/{crm_contact_id}" if crm_contact_id else None,
            "outreachLead": f"/outreach/leads/{outreach_lead_id}" if outreach_lead_id else None,
            "outreachBookings": "/outreach/bookings",
            "concierge": "/concierge",
            "oneRecord": True,
        },
        "spreadsheetRow": {
            "bookingId": booking_id,
            "guestEmail": fields["guestEmail"],
            "guestName": fields["guestName"],
            "status": fields["status"],
            "startsAt": fields["startsAt"],
            "crmLeadId": crm_lead_id,
            "crmContactId": crm_contact_id,
            "outreachLeadId": outreach_lead_id,
            "campaignId": campaign_id,
            "supportCaseId": case_id,
            "audienceSessionId": conversation_id,
            "calendarProvider": calendar_provider,
            "zoomMeetingId": zoom_meeting_id,
            "outcome": outcome,
            "conversion": conversion,
        },
    }


def spreadsheet_rows_for_workspace(workspace_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """Lead/booking rows for CRM spreadsheet + concierge Bookings table."""
    from keprix.vical.store import vical_store

    bookings = vical_store.list_bookings(workspace_id)[:limit]
    rows = []
    for b in bookings:
        mesh = build_booking_mesh(b, workspace_id=workspace_id)
        rows.append(mesh["spreadsheetRow"])
    return rows


__all__ = ["build_booking_mesh", "spreadsheet_rows_for_workspace"]
