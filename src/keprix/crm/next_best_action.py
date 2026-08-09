"""Next-best-action suggestions for CRM subjects (Prompt 627).

Returns {action, reason, confidence, requires_approval}. Execution is always
Soft Wall gated; suggestions never bypass suppression or approvals.
"""

from __future__ import annotations

from typing import Any

from keprix.crm.models import CrmStage
from keprix.crm.soft_wall import gate_or_approve

STAGE_ACTIONS: dict[str, tuple[str, str, float]] = {
    CrmStage.DISCOVERED: ("enrich", "Lead has not been enriched yet", 0.82),
    CrmStage.ENRICHED: ("add_to_list", "Enriched lead is ready for a list", 0.78),
    CrmStage.LISTED: ("request_approval", "Listed lead needs Soft Wall enroll approval", 0.8),
    CrmStage.APPROVED: ("enrol_sequence", "Approved lead can enroll in a sequence", 0.85),
    CrmStage.ENROLLED: ("schedule_follow_up", "Enrolled lead may need a follow-up check", 0.55),
    CrmStage.CONTACTED: ("schedule_follow_up", "No recent reply; schedule a follow-up", 0.7),
    CrmStage.ENGAGED: ("draft_reply", "Lead replied; draft a Soft Wall reply", 0.88),
    CrmStage.QUALIFIED: ("create_booking_link", "Qualified lead is ready for a booking link", 0.84),
    CrmStage.BOOKED: ("create_task", "Appointment booked; create a prep task", 0.75),
    CrmStage.CUSTOMER: ("notify_user", "Customer stage; hand off to nurture sequence", 0.65),
    CrmStage.PAYING: ("notify_user", "Paying customer; confirm post-sale nurture", 0.6),
    CrmStage.LOST: ("add_tag", "Closed lost; tag for win-back review", 0.45),
}


def _primary_email(row: dict[str, Any]) -> str | None:
    for item in row.get("emails") or []:
        if isinstance(item, dict):
            addr = str(item.get("address") or "").strip()
            if addr:
                return addr
        elif str(item or "").strip():
            return str(item).strip()
    return None


def suggest_next_best_action(
    workspace_id: str,
    *,
    subject_id: str,
    subject_type: str = "lead",
    crm_store: Any = None,
    outreach_store: Any = None,
) -> dict[str, Any]:
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    getters = {
        "lead": crm_store.get_lead,
        "contact": crm_store.get_contact,
        "deal": crm_store.get_deal,
        "account": crm_store.get_account,
    }
    getter = getters.get(subject_type or "lead")
    row = getter(workspace_id, subject_id) if getter else None
    if not row:
        return {
            "action": None,
            "reason": "subject_not_found",
            "confidence": 0.0,
            "requires_approval": True,
            "ok": False,
            "error_code": "not_found",
        }

    stage = str(row.get("stage") or CrmStage.DISCOVERED)
    email = _primary_email(row)

    if stage in {CrmStage.SUPPRESSED, CrmStage.DO_NOT_CONTACT, CrmStage.BOUNCED}:
        return {
            "action": "notify_user",
            "reason": f"Subject is {stage}; mutating outreach actions are blocked",
            "confidence": 1.0,
            "requires_approval": True,
            "suppressed": True,
            "ok": True,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "stage": stage,
        }
    if email and crm_store.is_suppressed(workspace_id, channel="email", address=email):
        return {
            "action": "notify_user",
            "reason": "Address is suppressed; never bypass Soft Wall or suppression",
            "confidence": 1.0,
            "requires_approval": True,
            "suppressed": True,
            "ok": True,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "stage": stage,
        }

    # Prefer reply-driven draft when last_reply_at is set
    if row.get("last_reply_at") and stage in {CrmStage.CONTACTED, CrmStage.ENGAGED, CrmStage.ENROLLED}:
        return {
            "action": "draft_reply",
            "reason": "Recent reply recorded; draft a Soft Wall response",
            "confidence": 0.9,
            "requires_approval": True,
            "ok": True,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "stage": stage,
        }

    # Active enrollments → wait / follow up
    try:
        if outreach_store is None:
            from keprix.outreach.store import get_outreach_store

            outreach_store = get_outreach_store()
        if email:
            for lead in outreach_store.list_leads(workspace_id, limit=200):
                if str(lead.get("email") or "").lower() != email.lower():
                    continue
                for enr in outreach_store.active_enrollments_for_lead(str(lead["id"])):
                    if str(enr.get("status") or "").startswith("paused"):
                        return {
                            "action": "draft_reply",
                            "reason": "Enrollment paused after engagement; review reply",
                            "confidence": 0.86,
                            "requires_approval": True,
                            "ok": True,
                            "enrollment_id": enr.get("id"),
                            "subject_type": subject_type,
                            "subject_id": subject_id,
                            "stage": stage,
                        }
    except Exception:
        pass

    from keprix.crm.lifecycle import lifecycle_label

    action, reason, confidence = STAGE_ACTIONS.get(
        stage,
        ("create_task", "No strong signal; create a review task", 0.4),
    )
    requires_approval = action in {
        "enrich",
        "enrol_sequence",
        "draft_reply",
        "create_booking_link",
        "request_approval",
        "update_stage",
    }
    return {
        "action": action,
        "reason": reason,
        "confidence": confidence,
        "requires_approval": requires_approval,
        "ok": True,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "stage": stage,
        "lifecycle_label": lifecycle_label(stage),
    }


def execute_next_best_action(
    workspace_id: str,
    *,
    subject_id: str,
    subject_type: str = "lead",
    action: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
    actor_id: str | None = None,
    crm_store: Any = None,
) -> dict[str, Any]:
    """Execute a suggested (or explicit) action under Soft Wall + suppression."""
    suggestion = suggest_next_best_action(
        workspace_id,
        subject_id=subject_id,
        subject_type=subject_type,
        crm_store=crm_store,
    )
    use_action = action or suggestion.get("action")
    if not use_action:
        return {"ok": False, "error_code": "no_action", "suggestion": suggestion}
    if suggestion.get("suppressed") and use_action not in {"notify_user", "create_task", "add_tag"}:
        return {
            "ok": False,
            "error_code": "suppressed",
            "suggestion": suggestion,
            "note": "Suppression never bypassed",
        }

    gate = gate_or_approve(
        workspace_id,
        kind="funnel_nba_execute",
        subject=f"NBA {use_action} for {subject_type}:{subject_id}",
        payload={"action": use_action, "suggestion": suggestion},
        object_type=subject_type,
        object_id=subject_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "ok": False,
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
            "suggestion": suggestion,
        }

    from keprix.crm.funnel_orchestrator import orchestrate

    result = orchestrate(
        workspace_id,
        trigger="stage_changed",
        action=str(use_action),
        subject_id=subject_id,
        subject_type=subject_type,
        idempotency_key=f"nba:{subject_type}:{subject_id}:{use_action}",
        payload={"from_nba": True, "soft_wall_approved": True},
        crm_store=crm_store,
        actor_type="user",
        actor_id=actor_id,
        force=True,  # Soft Wall already cleared above
        require_soft_wall=False,
    )
    return {"ok": bool(result.get("ok")), "suggestion": suggestion, "execution": result, "soft_wall": gate}
