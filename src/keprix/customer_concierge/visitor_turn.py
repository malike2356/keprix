"""Visitor message turn: grounded knowledge, cases, handoff (Prompt 631)."""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.audience.context import get_audience_context
from keprix.customer_concierge.audience.retrieval_guard import sanitize_visitor_text
from keprix.customer_concierge.audience.tool_policy import is_customer_concierge_tool_allowed
from keprix.customer_concierge.handoff import request_handoff
from keprix.customer_concierge.published_knowledge import (
    build_grounded_answer,
    get_knowledge_store,
    profile_policy,
)
from keprix.customer_concierge.store import get_concierge_store
from keprix.customer_concierge.support_cases import get_support_case_store


def _escalate_reply(profile: Any, reason: str) -> str:
    email = getattr(profile, "escalation_email", None) or "the team"
    if reason.startswith("sensitive_intent"):
        return (
            "This looks like something a person on our team should handle. "
            f"I am connecting you with a teammate (or email {email})."
        )
    if reason == "low_confidence":
        return (
            "I am not confident enough to answer from published business knowledge. "
            f"I can escalate to a teammate, or you can email {email}."
        )
    return (
        "I could not find a published answer for that. "
        f"I can open a support case or you can reach {email}."
    )


def run_visitor_turn(
    *,
    workspace_id: str,
    persona_id: str,
    session_id: str,
    text: str,
    tool_name: str | None = None,
    tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = get_concierge_store().get(workspace_id, persona_id)
    ctx = get_audience_context()
    sanitized = sanitize_visitor_text(text)
    cases = get_support_case_store()
    policy = profile_policy(profile) if profile else {}
    min_conf = float(policy.get("confidenceThreshold") or 0.45)
    sensitive_extra = list(policy.get("sensitiveIntents") or [])

    if sanitized["suspicious"]:
        reply = (
            "I can help with published business questions and bookings. "
            "I cannot access private workspace tools or files."
        )
        cases.append_message(
            workspace_id=workspace_id,
            persona_id=persona_id,
            audience_session_id=session_id,
            role="visitor",
            body=sanitized["text"],
            metadata={"injectionSuspicious": True},
        )
        cases.append_message(
            workspace_id=workspace_id,
            persona_id=persona_id,
            audience_session_id=session_id,
            role="assistant",
            body=reply,
        )
        return {
            "ok": True,
            "reply": reply,
            "grounded": False,
            "citations": [],
            "escalated": False,
            "injectionSuspicious": True,
            "workspaceMember": False,
            "principal": "audience_session",
        }

    # Explicit allowed tools
    if tool_name:
        if not is_customer_concierge_tool_allowed(tool_name):
            return {
                "ok": False,
                "error_code": "audience_tool_denied",
                "tool": tool_name,
            }
        args = tool_args or {}
        result = _execute_tool(
            tool_name=tool_name,
            workspace_id=workspace_id,
            persona_id=persona_id,
            session_id=session_id,
            identity_id=ctx.identity_id if ctx else None,
            channel=ctx.channel if ctx else "web",
            profile=profile,
            args=args,
            text=text,
            policy=policy,
        )
        return result

    if not text.strip():
        reply = (profile.greeting_message if profile else None) or "Hi, how can I help?"
        return {
            "ok": True,
            "reply": reply,
            "grounded": False,
            "citations": [],
            "escalated": False,
            "injectionSuspicious": False,
            "workspaceMember": False,
            "principal": "audience_session",
        }

    cases.append_message(
        workspace_id=workspace_id,
        persona_id=persona_id,
        audience_session_id=session_id,
        role="visitor",
        body=text,
    )

    source_ids = list(getattr(profile, "knowledge_source_ids", None) or []) if profile else []
    hits = get_knowledge_store().search(
        workspace_id=workspace_id,
        persona_id=persona_id,
        query=text,
        knowledge_source_ids=source_ids,
        include_draft=False,
    )
    grounded = build_grounded_answer(
        query=text,
        hits=hits,
        min_confidence=min_conf,
        sensitive_patterns=sensitive_extra,
    )

    if grounded["grounded"]:
        excerpts = grounded["excerpts"]
        reply = excerpts[0] if excerpts else "Here is what our published knowledge says."
        if len(excerpts) > 1:
            reply = reply + "\n\n" + excerpts[1]
        cases.append_message(
            workspace_id=workspace_id,
            persona_id=persona_id,
            audience_session_id=session_id,
            role="assistant",
            body=reply,
            citations=grounded["citations"],
        )
        return {
            "ok": True,
            "reply": reply,
            "grounded": True,
            "confidence": grounded["confidence"],
            "citations": grounded["citations"],
            "escalated": False,
            "fallbackReason": None,
            "injectionSuspicious": False,
            "workspaceMember": False,
            "principal": "audience_session",
            "internalNotesVisible": False,
        }

    reason = str(grounded.get("fallbackReason") or "no_published_match")
    handoff = request_handoff(
        workspace_id=workspace_id,
        persona_id=persona_id,
        audience_session_id=session_id,
        reason=f"Auto-escalation: {reason}",
        identity_id=ctx.identity_id if ctx else None,
        channel=ctx.channel if ctx else "web",
        conversation_summary=text[:500],
        priority="high" if reason.startswith("sensitive") else "normal",
    )
    reply = _escalate_reply(profile, reason)
    cases.append_message(
        workspace_id=workspace_id,
        persona_id=persona_id,
        audience_session_id=session_id,
        role="assistant",
        body=reply,
        case_id=(handoff.get("supportCase") or {}).get("id"),
        metadata={"fallbackReason": reason, "escalated": True},
    )
    return {
        "ok": True,
        "reply": reply,
        "grounded": False,
        "confidence": grounded.get("confidence", 0),
        "citations": grounded.get("citations") or [],
        "escalated": True,
        "fallbackReason": reason,
        "supportCase": handoff.get("supportCase"),
        "handoff": {"status": handoff.get("status"), "channelContinuous": True},
        "injectionSuspicious": False,
        "workspaceMember": False,
        "principal": "audience_session",
        "internalNotesVisible": False,
    }


def _execute_tool(
    *,
    tool_name: str,
    workspace_id: str,
    persona_id: str,
    session_id: str,
    identity_id: str | None,
    channel: str,
    profile: Any,
    args: dict[str, Any],
    text: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    name = tool_name.replace("_", "-")
    cases = get_support_case_store()

    if name in {"concierge-knowledge-search", "concierge_knowledge_search"}:
        q = str(args.get("query") or text)
        hits = get_knowledge_store().search(
            workspace_id=workspace_id,
            persona_id=persona_id,
            query=q,
            knowledge_source_ids=list(getattr(profile, "knowledge_source_ids", None) or []),
            include_draft=False,
        )
        grounded = build_grounded_answer(
            query=q,
            hits=hits,
            min_confidence=float(policy.get("confidenceThreshold") or 0.45),
            sensitive_patterns=list(policy.get("sensitiveIntents") or []),
        )
        return {"ok": True, "tool": name, "hits": [h.to_dict() for h in hits], **grounded}

    if name in {"support-case-create", "support_case_create", "concierge-support-case-create"}:
        subject = str(args.get("subject") or text or "Visitor support request")[:200]
        case = cases.create_case(
            workspace_id=workspace_id,
            persona_id=persona_id,
            subject=subject,
            channel=channel,
            concierge_profile_id=profile.id if profile else None,
            audience_session_id=session_id,
            identity_id=identity_id,
            priority=str(args.get("priority") or "normal"),  # type: ignore[arg-type]
            conversation_summary=str(args.get("summary") or text)[:1000],
            actor_type="visitor",
            sla_first_response_minutes=int(policy.get("slaFirstResponseMinutes") or 60),
            sla_resolution_minutes=int(policy.get("slaResolutionMinutes") or 1440),
        )
        return {
            "ok": True,
            "tool": name,
            "reply": "I opened a support case for you. A teammate will follow up.",
            "supportCase": case,
            "workspaceMember": False,
        }

    if name in {"handoff-request", "handoff_request", "concierge-handoff-request"}:
        result = request_handoff(
            workspace_id=workspace_id,
            persona_id=persona_id,
            audience_session_id=session_id,
            reason=str(args.get("reason") or text or "Visitor requested a human"),
            identity_id=identity_id,
            channel=channel,
            conversation_summary=str(args.get("summary") or text)[:1000],
        )
        return {
            "ok": True,
            "tool": name,
            "reply": "I am handing you over to a human teammate. This chat stays open.",
            **result,
        }

    if name in {"audience-contact-upsert", "audience_contact_upsert"}:
        # Scoped capture only; no broad CRM search
        email = args.get("email")
        display = args.get("displayName") or args.get("name")
        identity = None
        crm_contact_id = None
        if identity_id:
            from keprix.customer_concierge.audience.store import get_audience_store

            aud = get_audience_store()
            identity = aud.get_identity(workspace_id, identity_id)
            if identity:
                # Best-effort CRM contact link (create/find by email); never broad search tools
                if email:
                    try:
                        from keprix.crm.store import get_crm_store

                        cstore = get_crm_store()
                        for contact in cstore.list_contacts(workspace_id, limit=500):
                            for item in contact.get("emails") or []:
                                addr = item.get("address") if isinstance(item, dict) else item
                                if str(addr or "").strip().lower() == str(email).strip().lower():
                                    crm_contact_id = contact["id"]
                                    break
                            if crm_contact_id:
                                break
                        if not crm_contact_id and hasattr(cstore, "create_contact"):
                            created = cstore.create_contact(
                                workspace_id,
                                str(display or email),
                                email=str(email),
                                source="concierge",
                            )
                            crm_contact_id = created.get("id") if isinstance(created, dict) else None
                    except Exception:
                        crm_contact_id = None
                identity = aud.upsert_identity(
                    workspace_id=workspace_id,
                    channel=identity.channel,
                    external_key=identity.external_key,
                    display_name=str(display) if display else None,
                    email=str(email) if email else None,
                    crm_contact_id=crm_contact_id,
                )
        return {
            "ok": True,
            "tool": name,
            "reply": "Thanks, I saved your contact details for this conversation.",
            "contact": identity.to_dict() if identity else {"email": email, "displayName": display},
            "crmContactId": crm_contact_id,
            "workspaceMember": False,
        }

    if name == "safe_reply":
        return {"ok": True, "tool": name, "reply": str(args.get("text") or text)}

    if name in {
        "vical-booking-create",
        "vical_book",
        "outreach-booking-confirm",
    }:
        from datetime import datetime, timezone

        from keprix.vical.conferencing.redact import to_public_booking_view
        from keprix.vical.saga import book_with_saga
        from keprix.vical.seed import ensure_default_consultation

        host_id = workspace_id
        ensure_default_consultation(host_id)
        starts_raw = args.get("startsAt") or args.get("starts_at")
        if not starts_raw:
            return {"ok": False, "error_code": "starts_at_required", "tool": name}
        starts_at = datetime.fromisoformat(str(starts_raw).replace("Z", "+00:00"))
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        guest_email = str(args.get("guestEmail") or args.get("email") or "").strip()
        guest_name = str(args.get("guestName") or args.get("name") or "Guest").strip()
        if not guest_email:
            return {"ok": False, "error_code": "guest_email_required", "tool": name}
        crm_contact_id = args.get("crmContactId") or args.get("crm_contact_id")
        crm_lead_id = args.get("crmLeadId") or args.get("crm_lead_id")
        outreach_lead_id = args.get("outreachLeadId") or args.get("outreach_lead_id")
        if identity_id and not crm_contact_id:
            from keprix.customer_concierge.audience.store import get_audience_store

            ident = get_audience_store().get_identity(workspace_id, identity_id)
            if ident and ident.crm_contact_id:
                crm_contact_id = ident.crm_contact_id

        meta = {
            "workspace_id": workspace_id,
            "persona_id": persona_id,
            "audience_session_id": session_id,
            "concierge": True,
        }
        if crm_contact_id:
            meta["crm_contact_id"] = crm_contact_id
        if crm_lead_id:
            meta["crm_lead_id"] = crm_lead_id
        if outreach_lead_id:
            meta["outreach_lead_id"] = outreach_lead_id
        if session_id:
            meta["conversation_id"] = session_id

        result = book_with_saga(
            host_id,
            guest_name=guest_name,
            guest_email=guest_email,
            starts_at=starts_at,
            slug=str(args.get("slug") or "consultation"),
            source="agent",
            notes=str(args.get("notes") or text or "")[:1000] or None,
            workspace_id=workspace_id,
            persona_id=persona_id,
            contact_id=str(crm_contact_id) if crm_contact_id else None,
            idempotency_key=args.get("idempotencyKey") or args.get("idempotency_key"),
            prefer_managed_zoom=bool(policy.get("bookingEnabled", True)),
            static_room_url=args.get("meetingUrl") or args.get("staticRoomUrl"),
            skip_slot_check=bool(args.get("skipSlotCheck")),
            metadata=meta,
        )
        public = to_public_booking_view(result["booking"].to_dict())
        nurture = None
        mesh = None
        if result["booking"].status == "confirmed" and not result.get("duplicate"):
            from keprix.customer_concierge.nurture_orchestration import (
                orchestrate_after_booking_confirmed,
            )

            # Lifecycle already fires CRM handoff; orchestration returns mesh + cadence stop evidence
            nurture = orchestrate_after_booking_confirmed(
                result["booking"], audience_session_id=session_id
            )
            mesh = nurture.get("mesh")
        elif result["booking"].status == "confirmed":
            from keprix.customer_concierge.capability_mesh import build_booking_mesh

            mesh = build_booking_mesh(
                result["booking"], workspace_id=workspace_id, audience_session_id=session_id
            )
        return {
            "ok": True,
            "tool": name,
            "reply": (
                f"Booked for {guest_name}. "
                + (
                    f"Join: {public.get('meeting_url')}"
                    if public.get("meeting_url")
                    else "ICS will be available for the confirmed booking."
                )
            ),
            "booking": public,
            "duplicate": result.get("duplicate"),
            "conferenceManaged": result.get("conferenceManaged"),
            "actionRequired": result.get("actionRequired"),
            "mesh": mesh,
            "nurture": nurture,
            "workspaceMember": False,
        }

    if name in {"vical-slots-offer", "vical_slots", "outreach-booking-offer-slots"}:
        from datetime import datetime, timedelta, timezone

        from keprix.vical.seed import ensure_default_consultation
        from keprix.vical.slots import SlotEngine

        host_id = workspace_id
        ensure_default_consultation(host_id)
        start = datetime.now(timezone.utc) + timedelta(hours=1)
        slots = SlotEngine().offer_slots(host_id, slug="consultation", start=start, count=5)
        return {
            "ok": True,
            "tool": name,
            "slots": [
                {"startsAt": s.start_at.isoformat(), "endsAt": s.end_at.isoformat()} for s in slots
            ],
            "workspaceMember": False,
        }

    return {"ok": False, "error_code": "tool_not_implemented", "tool": tool_name}


__all__ = ["run_visitor_turn"]
