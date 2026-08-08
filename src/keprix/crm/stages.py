"""CRM stage machine: single module for legal transitions (prompt 444)."""

from __future__ import annotations

from typing import Any

from keprix.crm.models import ALL_STAGES, FORWARD_STAGES, TERMINAL_STAGES, CrmStage

CUSTOMER_PAYING = frozenset({"customer", "paying"})

# Forward edges (adjacent moves). Skipping requires Soft Wall or explicit force.
_FORWARD_INDEX = {stage: i for i, stage in enumerate(FORWARD_STAGES)}

# Engagement / system driven targets (not free jumps to customer/paying)
ENGAGEMENT_STAGE_MAP: dict[str, str] = {
    "replied": CrmStage.ENGAGED,
    "interested": CrmStage.ENGAGED,
    "not_interested": CrmStage.LOST,
    "bounce": CrmStage.BOUNCED,
    "unsubscribe": CrmStage.SUPPRESSED,
    "booked_intent": CrmStage.QUALIFIED,
    "booking_intent": CrmStage.QUALIFIED,
    "ooo": CrmStage.CONTACTED,  # do not promote
    "auto_reply": CrmStage.CONTACTED,
}


class StageTransitionError(ValueError):
    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.extra = extra


def is_terminal(stage: str | None) -> bool:
    return str(stage or "") in TERMINAL_STAGES


def is_customer_paying(stage: str | None) -> bool:
    return str(stage or "") in CUSTOMER_PAYING


def can_transition(
    from_stage: str | None,
    to_stage: str,
    *,
    human_confirmed: bool = False,
    business_event: bool = False,
    soft_wall_approved: bool = False,
    force: bool = False,
) -> tuple[bool, str | None]:
    """Return (allowed, reason_code)."""
    src = str(from_stage or CrmStage.DISCOVERED)
    dst = str(to_stage)
    if dst not in ALL_STAGES:
        return False, "invalid_stage"
    if src == dst:
        return True, None
    if force:
        return True, None

    if dst in CUSTOMER_PAYING:
        if not (human_confirmed or business_event or soft_wall_approved):
            return False, "customer_paying_requires_human_or_business_event"
        # Still allow Soft Wall path from booked/qualified+
        if src in TERMINAL_STAGES and src != CrmStage.LOST:
            return False, "terminal_blocked"
        return True, None

    if dst in TERMINAL_STAGES:
        return True, None

    if src in TERMINAL_STAGES:
        if soft_wall_approved or human_confirmed:
            return True, None
        return False, "terminal_blocked"

    if src not in _FORWARD_INDEX or dst not in _FORWARD_INDEX:
        return False, "unknown_forward_stage"

    src_i = _FORWARD_INDEX[src]
    dst_i = _FORWARD_INDEX[dst]
    if dst_i == src_i + 1:
        return True, None
    if dst_i < src_i:
        # Backward moves need Soft Wall except to terminal handled above
        if soft_wall_approved or human_confirmed:
            return True, None
        return False, "backward_requires_soft_wall"
    # Skip ahead
    if soft_wall_approved or human_confirmed:
        return True, None
    return False, "illegal_stage_skip"


def apply_stage(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    to_stage: str,
    human_confirmed: bool = False,
    business_event: bool = False,
    soft_wall_approved: bool = False,
    force: bool = False,
    actor_type: str | None = None,
    actor_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Enforce transition graph and update lead/contact/deal."""
    getters = {
        "lead": store.get_lead,
        "contact": store.get_contact,
        "deal": store.get_deal,
        "account": store.get_account,
    }
    updaters = {
        "lead": store.update_lead,
        "contact": store.update_contact,
        "deal": store.update_deal,
        "account": store.update_account,
    }
    get_fn = getters.get(entity_type)
    upd_fn = updaters.get(entity_type)
    if not get_fn or not upd_fn:
        raise StageTransitionError("unsupported_entity", f"entity_type={entity_type}")

    row = get_fn(workspace_id, entity_id)
    if not row:
        raise StageTransitionError("not_found", f"{entity_type} not found", entity_id=entity_id)

    from_stage = str(row.get("stage") or "")
    ok, code = can_transition(
        from_stage,
        to_stage,
        human_confirmed=human_confirmed,
        business_event=business_event,
        soft_wall_approved=soft_wall_approved,
        force=force,
    )
    if not ok:
        raise StageTransitionError(code or "blocked", f"cannot move {from_stage} -> {to_stage}", from_stage=from_stage, to_stage=to_stage)

    updated = upd_fn(workspace_id, entity_id, stage=to_stage, actor_type=actor_type, actor_id=actor_id)
    try:
        store.create_activity(
            workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type="stage_change",
            channel="system",
            subject=f"Stage {from_stage} -> {to_stage}",
            body=reason or code or "",
            actor_type=actor_type,
            actor_id=actor_id,
        )
    except Exception:
        pass
    return {"ok": True, "from_stage": from_stage, "to_stage": to_stage, "entity": updated}


def suggested_stage_for_engagement(engagement_type: str) -> str | None:
    return ENGAGEMENT_STAGE_MAP.get(str(engagement_type).strip().lower())


def transition_graph() -> dict[str, Any]:
    """Test/docs helper: adjacent forward edges + gated customer/paying."""
    edges = []
    for i, stage in enumerate(FORWARD_STAGES[:-1]):
        edges.append({"from": stage, "to": FORWARD_STAGES[i + 1], "gate": None})
    edges.append({"from": CrmStage.BOOKED, "to": CrmStage.CUSTOMER, "gate": "human_or_business"})
    edges.append({"from": CrmStage.CUSTOMER, "to": CrmStage.PAYING, "gate": "human_or_business"})
    return {"forward": list(FORWARD_STAGES), "terminal": list(TERMINAL_STAGES), "edges": edges}
