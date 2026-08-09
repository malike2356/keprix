"""Lifecycle stage aliases and Soft Wall conversion helpers (Prompt 627).

Prompt labels are UI/docs aliases only. Canonical stages remain ``CrmStage``.
Do not invent a third stage vocabulary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.crm.models import CrmStage
from keprix.crm.soft_wall import gate_or_approve

# Prompt / operator labels -> canonical CrmStage (docs and UI aliases only).
LIFECYCLE_ALIASES: dict[str, str] = {
    "new lead": CrmStage.DISCOVERED,
    "new_lead": CrmStage.DISCOVERED,
    "discovered": CrmStage.DISCOVERED,
    "enriched": CrmStage.ENRICHED,
    "ready for outreach": CrmStage.LISTED,
    "ready_for_outreach": CrmStage.LISTED,
    "listed": CrmStage.LISTED,
    "approved": CrmStage.APPROVED,
    "contacted": CrmStage.CONTACTED,
    "replied": CrmStage.ENGAGED,
    "engaged": CrmStage.ENGAGED,
    "qualified": CrmStage.QUALIFIED,
    "appointment booked": CrmStage.BOOKED,
    "appointment_booked": CrmStage.BOOKED,
    "booked": CrmStage.BOOKED,
    "proposal": CrmStage.BOOKED,  # closest forward stage before customer; not a new enum
    "offered": CrmStage.BOOKED,
    "customer": CrmStage.CUSTOMER,
    "paying": CrmStage.PAYING,
    "closed lost": CrmStage.LOST,
    "closed_lost": CrmStage.LOST,
    "lost": CrmStage.LOST,
    "suppressed": CrmStage.SUPPRESSED,
}

# Human-readable labels for CRM UI (canonical stage -> prompt label).
LIFECYCLE_LABELS: dict[str, str] = {
    CrmStage.DISCOVERED: "New Lead",
    CrmStage.ENRICHED: "Enriched",
    CrmStage.LISTED: "Ready for Outreach",
    CrmStage.APPROVED: "Ready for Outreach",
    CrmStage.ENROLLED: "Ready for Outreach",
    CrmStage.CONTACTED: "Contacted",
    CrmStage.ENGAGED: "Replied",
    CrmStage.QUALIFIED: "Qualified",
    CrmStage.BOOKED: "Appointment Booked",
    CrmStage.CUSTOMER: "Customer",
    CrmStage.PAYING: "Customer",
    CrmStage.LOST: "Closed Lost",
    CrmStage.SUPPRESSED: "Suppressed",
    CrmStage.BOUNCED: "Suppressed",
    CrmStage.DO_NOT_CONTACT: "Suppressed",
}

# Post-customer nurture uses sequence kind, not a new CrmStage.
POST_CUSTOMER_SEQUENCE_KIND = "nurture"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_stage_alias(label: str | None, *, default: str | None = None) -> str | None:
    """Map a prompt/UI label to a canonical CrmStage value."""
    if label is None:
        return default
    raw = str(label).strip()
    if not raw:
        return default
    key = raw.lower().replace("-", " ").replace("_", " ")
    key_compact = key.replace(" ", "_")
    if raw in LIFECYCLE_ALIASES.values() or raw in {s.value for s in CrmStage}:
        return raw
    if key in LIFECYCLE_ALIASES:
        return LIFECYCLE_ALIASES[key]
    if key_compact in LIFECYCLE_ALIASES:
        return LIFECYCLE_ALIASES[key_compact]
    spaced = " ".join(key.split())
    if spaced in LIFECYCLE_ALIASES:
        return LIFECYCLE_ALIASES[spaced]
    return default if default is not None else raw


def lifecycle_label(stage: str | None) -> str:
    s = str(stage or "")
    return LIFECYCLE_LABELS.get(s, s.replace("_", " ") or "unknown")


def lifecycle_alias_map() -> dict[str, Any]:
    return {
        "aliases": dict(LIFECYCLE_ALIASES),
        "labels": dict(LIFECYCLE_LABELS),
        "post_customer_nurture_kind": POST_CUSTOMER_SEQUENCE_KIND,
        "note": "Aliases only; CrmStage remains source of truth.",
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


def _attribution_fields(lead: dict[str, Any]) -> dict[str, Any]:
    """Preserve source / campaign / sequence / agent attribution across conversion."""
    keys = (
        "source",
        "source_type",
        "source_name",
        "source_url",
        "source_captured_at",
        "source_job_id",
        "campaign_id",
        "sequence_id",
        "list_id",
        "assigned_agent",
        "owner_agent_id",
        "owner_user_id",
        "domain_pack",
        "external_source_id",
    )
    return {k: lead.get(k) for k in keys if lead.get(k) is not None}


def convert_lead_to_contact(
    workspace_id: str,
    lead_id: str,
    *,
    crm_store: Any = None,
    actor_type: str | None = "user",
    actor_id: str | None = None,
    soft_wall_approved: bool = False,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    """Lead -> Contact conversion. Soft Wall when gates enabled; merge already exists separately."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    lead = crm_store.get_lead(workspace_id, lead_id)
    if not lead:
        return {"ok": False, "error_code": "lead_not_found"}

    email = _primary_email(lead)
    if email and crm_store.is_suppressed(workspace_id, channel="email", address=email):
        return {"ok": False, "error_code": "suppressed", "address": email}

    gate = gate_or_approve(
        workspace_id,
        kind="lead_convert_contact",
        subject=f"Convert lead {lead_id} to contact",
        payload={"lead_id": lead_id, "target": "contact"},
        object_type="lead",
        object_id=lead_id,
        actor_id=actor_id,
        force=force or soft_wall_approved,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "ok": False,
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
        }

    attribution = _attribution_fields(lead)
    contact = crm_store.create_contact(
        workspace_id,
        display_name=str(lead.get("name") or lead.get("company_name") or email or lead_id),
        emails=lead.get("emails") or [],
        phones=lead.get("phones") or [],
        account_id=lead.get("account_id"),
        stage=lead.get("stage") or CrmStage.QUALIFIED,
        tags=list(lead.get("tags") or []) + ["converted_from_lead"],
        actor_type=actor_type,
        actor_id=actor_id,
        **{k: v for k, v in attribution.items() if k in {"source", "domain_pack", "assigned_agent", "external_source_id"}},
    )
    crm_store.update_lead(
        workspace_id,
        lead_id,
        converted_at=_utcnow(),
        custom_fields={
            **(lead.get("custom_fields") if isinstance(lead.get("custom_fields"), dict) else {}),
            "converted_contact_id": contact["id"],
            "attribution_preserved": attribution,
        },
        actor_type=actor_type,
        actor_id=actor_id,
    )
    crm_store.create_activity(
        workspace_id,
        entity_type="lead",
        entity_id=lead_id,
        activity_type="converted_to_contact",
        subject="Lead converted to contact",
        body=f"Contact {contact['id']}",
        metadata={"contact_id": contact["id"], "attribution": attribution},
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return {
        "ok": True,
        "lead_id": lead_id,
        "contact": contact,
        "attribution": attribution,
    }


def convert_lead_to_customer(
    workspace_id: str,
    lead_id: str,
    *,
    paying: bool = True,
    crm_store: Any = None,
    actor_type: str | None = "user",
    actor_id: str | None = None,
    soft_wall_approved: bool = False,
    force: bool = False,
    approval_id: str | None = None,
    human_confirmed: bool = False,
) -> dict[str, Any]:
    """Lead -> customer/paying via Soft Wall + stage machine. Preserves attribution."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    lead = crm_store.get_lead(workspace_id, lead_id)
    if not lead:
        return {"ok": False, "error_code": "lead_not_found"}

    email = _primary_email(lead)
    if email and crm_store.is_suppressed(workspace_id, channel="email", address=email):
        return {"ok": False, "error_code": "suppressed", "address": email}

    target = CrmStage.PAYING if paying else CrmStage.CUSTOMER
    gate = gate_or_approve(
        workspace_id,
        kind="stage_customer_paying",
        subject=f"Convert lead {lead_id} to {target}",
        payload={"lead_id": lead_id, "to_stage": target},
        object_type="lead",
        object_id=lead_id,
        actor_id=actor_id,
        force=force or soft_wall_approved,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "ok": False,
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
        }

    from keprix.crm.stages import apply_stage

    attribution = _attribution_fields(lead)
    stage_result = apply_stage(
        crm_store,
        workspace_id,
        entity_type="lead",
        entity_id=lead_id,
        to_stage=target,
        soft_wall_approved=True,
        human_confirmed=human_confirmed or True,
        actor_type=actor_type,
        actor_id=actor_id,
        reason="lifecycle_convert_customer",
    )
    crm_store.update_lead(
        workspace_id,
        lead_id,
        converted_at=_utcnow(),
        custom_fields={
            **(lead.get("custom_fields") if isinstance(lead.get("custom_fields"), dict) else {}),
            "converted_to": target,
            "attribution_preserved": attribution,
        },
        actor_type=actor_type,
        actor_id=actor_id,
    )
    crm_store.create_activity(
        workspace_id,
        entity_type="lead",
        entity_id=lead_id,
        activity_type="converted_to_customer",
        subject=f"Lead converted to {target}",
        metadata={"attribution": attribution, "stage": target},
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return {
        "ok": True,
        "lead_id": lead_id,
        "stage": stage_result,
        "target_stage": target,
        "attribution": attribution,
    }
