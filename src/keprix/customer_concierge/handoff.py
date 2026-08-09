"""AI to human handoff with channel continuity (Prompt 631)."""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.audience.store import get_audience_store
from keprix.customer_concierge.published_knowledge import profile_policy
from keprix.customer_concierge.store import get_concierge_store
from keprix.customer_concierge.support_cases import get_support_case_store


def request_handoff(
    *,
    workspace_id: str,
    persona_id: str,
    audience_session_id: str,
    reason: str,
    identity_id: str | None = None,
    channel: str = "web",
    conversation_summary: str | None = None,
    priority: str = "normal",
    open_case: bool = True,
) -> dict[str, Any]:
    reason_s = (reason or "").strip() or "Visitor requested a human"
    profile = get_concierge_store().get(workspace_id, persona_id)
    policy = profile_policy(profile) if profile else {}
    support_case = None
    if open_case:
        support_case = get_support_case_store().create_case(
            workspace_id=workspace_id,
            persona_id=persona_id,
            subject=reason_s[:200],
            channel=channel,
            concierge_profile_id=profile.id if profile else None,
            audience_session_id=audience_session_id,
            identity_id=identity_id,
            priority=priority,  # type: ignore[arg-type]
            conversation_summary=conversation_summary or reason_s,
            actor_type="ai",
            metadata={"kind": "handoff_request"},
            sla_first_response_minutes=int(policy.get("slaFirstResponseMinutes") or 60),
            sla_resolution_minutes=int(policy.get("slaResolutionMinutes") or 1440),
        )

    aud = get_audience_store()
    session = aud.get_session(workspace_id, audience_session_id)
    if not session:
        return {"ok": False, "error_code": "session_not_found"}

    updated = aud.mark_handed_off(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        case_id=support_case["id"] if support_case else None,
        summary=conversation_summary or reason_s,
    )
    aud.append_audit(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        identity_id=identity_id,
        event_type="handoff.requested",
        actor_type="system",
        detail={
            "caseId": support_case["id"] if support_case else None,
            "reason": reason_s,
            "channel": channel,
        },
    )
    return {
        "ok": True,
        "audienceSessionId": audience_session_id,
        "status": "handed_off",
        "supportCase": support_case,
        "operatorUserId": updated.operator_user_id if updated else None,
        "channelContinuous": True,
    }


def operator_takeover(
    *,
    workspace_id: str,
    audience_session_id: str,
    operator_user_id: str,
) -> dict[str, Any]:
    aud = get_audience_store()
    session = aud.get_session(workspace_id, audience_session_id)
    if not session:
        return {"ok": False, "error_code": "session_not_found"}
    aud.set_operator(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        operator_user_id=operator_user_id,
    )
    case_id = session.active_support_case_id
    if case_id:
        get_support_case_store().assign(
            workspace_id=workspace_id,
            case_id=str(case_id),
            assignee_user_id=operator_user_id,
        )
        get_support_case_store().transition(
            workspace_id=workspace_id,
            case_id=str(case_id),
            status="pending_operator",
            actor_type="operator",
            actor_id=operator_user_id,
        )
    aud.append_audit(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        event_type="handoff.takeover",
        actor_type="operator",
        detail={"operatorUserId": operator_user_id},
    )
    return {
        "ok": True,
        "audienceSessionId": audience_session_id,
        "status": "handed_off",
        "operatorUserId": operator_user_id,
        "liveTakeover": True,
    }


def release_to_ai(
    *,
    workspace_id: str,
    audience_session_id: str,
    operator_user_id: str | None = None,
) -> dict[str, Any]:
    aud = get_audience_store()
    session = aud.get_session(workspace_id, audience_session_id)
    if not session:
        return {"ok": False, "error_code": "session_not_found"}
    aud.set_operator(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        operator_user_id=None,
    )
    aud.append_audit(
        workspace_id=workspace_id,
        session_id=audience_session_id,
        event_type="handoff.released",
        actor_type="operator",
        detail={"operatorUserId": operator_user_id},
    )
    return {
        "ok": True,
        "audienceSessionId": audience_session_id,
        "status": "active",
        "operatorUserId": None,
    }


__all__ = ["operator_takeover", "release_to_ai", "request_handoff"]
