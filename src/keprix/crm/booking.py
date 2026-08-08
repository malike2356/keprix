"""viCal booking handoff helpers for CRM (prompt 445)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from keprix.crm.models import CrmStage
from keprix.crm.stages import apply_stage, StageTransitionError


def resolve_booking_link(
    *,
    host_user_id: str | None = None,
    event_type_id: str | None = None,
    campaign: dict[str, Any] | None = None,
    crm_lead_id: str | None = None,
    crm_contact_id: str | None = None,
    utm_source: str = "keprix_crm",
) -> dict[str, Any]:
    """Prefer viCal public book URL; fall back to campaign default_booking_link."""
    campaign = campaign or {}
    vical_event_type_id = event_type_id or campaign.get("vical_event_type_id")
    default_link = campaign.get("default_booking_link")

    profile = None
    public_slug = None
    try:
        from keprix.vical.store import vical_store

        uid = host_user_id or campaign.get("host_user_id")
        if uid:
            profile = vical_store.get_host_profile(str(uid))
            public_slug = (profile or {}).get("public_slug") or uid
        if vical_event_type_id and not public_slug:
            # Best-effort: list hosts not available; fail honestly later
            pass
    except Exception as exc:
        return {
            "ok": False,
            "reason": "vical_unavailable",
            "error": str(exc),
            "fallback_link": default_link,
        }

    if not public_slug and not default_link:
        return {
            "ok": False,
            "reason": "missing_vical_host",
            "message": "No viCal host profile or default_booking_link configured",
            "fallback_link": None,
        }

    query = {
        "utm_source": utm_source,
        "utm_medium": "email",
        "utm_campaign": str(campaign.get("id") or "crm"),
    }
    if crm_lead_id:
        query["crm_lead_id"] = crm_lead_id
    if crm_contact_id:
        query["crm_contact_id"] = crm_contact_id
    if vical_event_type_id:
        query["event_type_id"] = str(vical_event_type_id)

    path = f"/book/{public_slug}" if public_slug else None
    book_url = f"{path}?{urlencode(query)}" if path else default_link
    return {
        "ok": True,
        "public_slug": public_slug,
        "vical_event_type_id": vical_event_type_id,
        "book_path": path,
        "book_url": book_url,
        "fallback_link": default_link,
        "mesh": {
            "vical": "/vical",
            "book": path,
            "calendar": "/calendar",
            "crm": f"/crm/leads/{crm_lead_id}" if crm_lead_id else (
                f"/crm/contacts/{crm_contact_id}" if crm_contact_id else "/crm"
            ),
        },
    }


def offer_booking(
    workspace_id: str,
    contact_id: str | None = None,
    lead_id: str | None = None,
    *,
    host_user_id: str | None = None,
    event_type_id: str | None = None,
    campaign_id: str | None = None,
    crm_store: Any = None,
    outreach_store: Any = None,
) -> dict[str, Any]:
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    entity = None
    entity_type = None
    entity_id = None
    if contact_id:
        entity = crm_store.get_contact(workspace_id, contact_id)
        entity_type, entity_id = "contact", contact_id
    elif lead_id:
        entity = crm_store.get_lead(workspace_id, lead_id)
        entity_type, entity_id = "lead", lead_id
    if not entity:
        return {"ok": False, "reason": "not_found"}

    campaign = None
    if campaign_id and outreach_store is not None:
        campaign = outreach_store.get_campaign(workspace_id, campaign_id)
    elif campaign_id:
        try:
            from keprix.outreach.store import get_outreach_store

            campaign = get_outreach_store().get_campaign(workspace_id, campaign_id)
        except Exception:
            campaign = None

    link = resolve_booking_link(
        host_user_id=host_user_id or workspace_id,
        event_type_id=event_type_id,
        campaign=campaign,
        crm_lead_id=lead_id if entity_type == "lead" else None,
        crm_contact_id=contact_id if entity_type == "contact" else None,
    )
    if not link.get("ok") and not link.get("fallback_link"):
        return link

    # Soft Wall stage suggestion toward qualified when offering booking
    suggestion = None
    stage = str(entity.get("stage") or "")
    if stage in {"enrolled", "contacted", "engaged"}:
        suggestion = {
            "suggested_stage": CrmStage.QUALIFIED,
            "needs_soft_wall": True,
            "inbox_kind": "stage_suggestion",
        }
        try:
            from keprix.crm.engagement import enqueue_inbox

            enqueue_inbox(
                crm_store,
                workspace_id,
                kind="stage_suggestion",
                entity_type=entity_type,
                entity_id=entity_id,
                classification="booked_intent",
                confidence=0.6,
                subject="Offer booking / qualified suggestion",
                body=f"Booking link offered: {link.get('book_url') or link.get('fallback_link')}",
                raw_metadata={"offer_booking": True},
                classification_meta={"suggested_stage": CrmStage.QUALIFIED},
                provider_event_id=f"offer_booking:{entity_id}",
            )
        except Exception:
            pass

    return {
        "ok": True,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "booking": link,
        "gui": {
            "open_booking": link.get("book_url") or link.get("fallback_link"),
            "open_calendar": "/calendar",
            "open_vical": "/vical",
            "open_crm": f"/crm/{'contacts' if entity_type=='contact' else 'leads'}/{entity_id}",
        },
        "soft_wall_suggestion": suggestion,
    }


def on_vical_booking_confirmed_crm(booking: Any, *, crm_store: Any = None) -> dict[str, Any]:
    """Extend Soft Wall handoff: set booked, activity, deal touch."""
    from keprix.outreach.vical_handoff import soft_wall_handoff_on_vical_confirmed

    base = soft_wall_handoff_on_vical_confirmed(booking)
    if crm_store is None:
        try:
            from keprix.crm.store import get_crm_store

            crm_store = get_crm_store()
        except Exception:
            return base

    meta = dict(getattr(booking, "metadata", None) or {})
    if isinstance(booking, dict):
        meta = dict(booking.get("metadata") or {})
        booking_id = str(booking.get("id") or "")
        guest_email = str(booking.get("guest_email") or "").strip().lower()
        status = str(booking.get("status") or "")
    else:
        booking_id = str(booking.id)
        guest_email = str(booking.guest_email or "").strip().lower()
        status = str(booking.status)

    if status != "confirmed":
        return base

    workspace_id = str(meta.get("workspace_id") or base.get("workspace_id") or "default")
    crm_lead_id = meta.get("crm_lead_id") or base.get("crm_lead_id")
    crm_contact_id = meta.get("crm_contact_id")

    target_type = None
    target_id = None
    if crm_lead_id and crm_store.get_lead(workspace_id, str(crm_lead_id)):
        target_type, target_id = "lead", str(crm_lead_id)
    elif crm_contact_id and crm_store.get_contact(workspace_id, str(crm_contact_id)):
        target_type, target_id = "contact", str(crm_contact_id)
    elif guest_email:
        for lead in crm_store.list_leads(workspace_id, limit=500):
            for item in lead.get("emails") or []:
                addr = item.get("address") if isinstance(item, dict) else item
                if str(addr or "").lower() == guest_email:
                    target_type, target_id = "lead", lead["id"]
                    break

    if not target_type or not target_id:
        base["crm_booking"] = {"ok": False, "reason": "crm_entity_not_found"}
        return base

    try:
        apply_stage(
            crm_store,
            workspace_id,
            entity_type=target_type,
            entity_id=target_id,
            to_stage=CrmStage.BOOKED,
            business_event=True,
            actor_type="system",
            actor_id="vical",
            reason=f"vical_booking:{booking_id}",
        )
    except StageTransitionError as exc:
        base["crm_stage_error"] = exc.code

    activity = crm_store.create_activity(
        workspace_id,
        entity_type=target_type,
        entity_id=target_id,
        activity_type="booking_confirmed",
        channel="vical",
        subject=f"viCal booking {booking_id} confirmed",
        body=f"guest={guest_email}; vical_booking_id={booking_id}",
    )

    deal = None
    try:
        # Touch or create a thin deal
        deals = [
            d
            for d in crm_store.list_deals(workspace_id, limit=200)
            if str(d.get("lead_id") or "") == target_id or str(d.get("contact_id") or "") == target_id
        ]
        if deals:
            deal = crm_store.update_deal(
                workspace_id,
                deals[0]["id"],
                stage=CrmStage.BOOKED,
                metadata={"vical_booking_id": booking_id} if hasattr(crm_store, "update_deal") else None,
            )
            # metadata may not be allowed; ignore
            if deal is None:
                deal = deals[0]
        else:
            deal = crm_store.create_deal(
                workspace_id,
                name=f"Booking {booking_id}",
                stage=CrmStage.BOOKED,
                lead_id=target_id if target_type == "lead" else None,
                contact_id=target_id if target_type == "contact" else None,
                external_source_id=f"vical:{booking_id}",
            )
    except Exception as exc:
        base["deal_error"] = str(exc)

    try:
        from keprix.crm.funnel_analytics import record_funnel_event

        record_funnel_event(workspace_id, "booked")
    except Exception:
        pass

    # Soft Wall stage suggestion visibility for booked/qualified in inbox
    try:
        from keprix.crm.engagement import enqueue_inbox

        enqueue_inbox(
            crm_store,
            workspace_id,
            kind="stage_suggestion",
            entity_type=target_type,
            entity_id=target_id,
            classification="booked",
            confidence=1.0,
            subject="Booking confirmed",
            body=f"vical_booking_id={booking_id}",
            raw_metadata={"vical_booking_id": booking_id},
            classification_meta={"stage": CrmStage.BOOKED},
            provider_event_id=f"vical:{booking_id}",
        )
    except Exception:
        pass

    base["crm_booking"] = {
        "ok": True,
        "entity_type": target_type,
        "entity_id": target_id,
        "activity": activity,
        "deal": deal,
        "vical_booking_id": booking_id,
        "mesh": {
            "crm": f"/crm/{'leads' if target_type=='lead' else 'contacts'}/{target_id}",
            "vical": f"/vical?booking={booking_id}",
            "calendar": "/calendar",
            "open_booking": f"/vical?booking={booking_id}",
        },
    }
    return base
