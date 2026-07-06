"""Approval gates for risky opportunity execution actions."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Literal

from keprix.opportunity.models import OpportunityApproval
from keprix.opportunity.workspace import append_approval_log, read_opportunity_json, update_opportunity_json

RiskyAction = Literal[
    "send_outreach",
    "publish_post",
    "create_ad",
    "edit_ad",
    "spend_money",
    "update_crm",
    "send_email_sequence",
    "publish_landing_page",
    "charge_customer",
    "export_personal_data",
    "upload_lead_list",
    "set_ad_budget",
    "create_stripe_product",
]

RISKY_ACTIONS: frozenset[str] = frozenset(
    {
        "send_outreach",
        "publish_post",
        "create_ad",
        "edit_ad",
        "spend_money",
        "update_crm",
        "send_email_sequence",
        "publish_landing_page",
        "charge_customer",
        "export_personal_data",
        "upload_lead_list",
        "set_ad_budget",
        "create_stripe_product",
    }
)

ACTION_LABELS: dict[str, str] = {
    "send_outreach": "Sending outreach",
    "publish_post": "Publishing posts",
    "create_ad": "Creating ads",
    "edit_ad": "Editing ads",
    "spend_money": "Spending money",
    "update_crm": "Updating CRM records",
    "send_email_sequence": "Sending email sequences",
    "publish_landing_page": "Publishing landing pages",
    "charge_customer": "Charging customers",
    "export_personal_data": "Exporting personal data",
    "upload_lead_list": "Uploading lead lists",
    "set_ad_budget": "Setting ad budgets",
    "create_stripe_product": "Creating Stripe products or prices",
}

ACTION_RISK_LEVEL: dict[str, str] = {
    "send_outreach": "high",
    "publish_post": "high",
    "create_ad": "high",
    "edit_ad": "high",
    "spend_money": "high",
    "update_crm": "medium",
    "send_email_sequence": "high",
    "publish_landing_page": "high",
    "charge_customer": "high",
    "export_personal_data": "high",
    "upload_lead_list": "high",
    "set_ad_budget": "high",
    "create_stripe_product": "high",
}


def is_risky_action(action: str) -> bool:
    return action in RISKY_ACTIONS


def request_approval(
    *,
    workspace_id: str,
    opportunity_id: str,
    action: str,
    requested_by: str = "system",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
    source: str = "opportunity_engine",
) -> OpportunityApproval:
    if not is_risky_action(action):
        raise ValueError(f"Action is not gated: {action}")

    approval_id = "appr-" + secrets.token_hex(4)
    now = datetime.now(timezone.utc)
    approval = OpportunityApproval(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        approval_id=approval_id,
        action=action,
        status="pending",
        requested_by=requested_by,
        reason=reason or f"{ACTION_LABELS.get(action, action)} requires explicit approval",
        metadata=metadata or {},
        source=source,
        created_at=now,
        updated_at=now,
    )

    meta = read_opportunity_json(opportunity_id)
    pending = list(meta.get("pending_approvals", []))
    pending.append(approval.model_dump(mode="json"))
    update_opportunity_json(
        opportunity_id,
        {"status": "approval_required", "pending_approvals": pending},
    )
    append_approval_log(
        opportunity_id,
        {
            "timestamp": now.isoformat(),
            "action": action,
            "status": "pending",
            "actor": requested_by,
            "risk_level": ACTION_RISK_LEVEL.get(action, "medium"),
            "preview": (metadata or {}).get("preview", reason),
            "integration": (metadata or {}).get("integration", "opportunity_engine"),
            "requested_by": requested_by,
            "approved_by": "",
            "result": "pending",
        },
    )
    return approval


def resolve_approval(
    *,
    workspace_id: str,
    opportunity_id: str,
    approval_id: str,
    approved: bool,
    approved_by: str,
    source: str = "opportunity_engine",
) -> OpportunityApproval | None:
    meta = read_opportunity_json(opportunity_id)
    pending = list(meta.get("pending_approvals", []))
    resolved: OpportunityApproval | None = None
    remaining: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for row in pending:
        if row.get("approval_id") != approval_id:
            remaining.append(row)
            continue
        resolved = OpportunityApproval(
            workspace_id=workspace_id,
            opportunity_id=opportunity_id,
            approval_id=approval_id,
            action=row.get("action", ""),
            status="approved" if approved else "rejected",
            requested_by=row.get("requested_by", "system"),
            approved_by=approved_by,
            reason=row.get("reason", ""),
            metadata=row.get("metadata", {}),
            source=source,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=now,
        )

    if resolved is None:
        return None

    patch: dict[str, Any] = {"pending_approvals": remaining}
    if not remaining:
        patch["status"] = "assets_ready"
    update_opportunity_json(opportunity_id, patch)
    append_approval_log(
        opportunity_id,
        {
            "timestamp": now.isoformat(),
            "action": resolved.action,
            "status": resolved.status,
            "actor": approved_by,
            "risk_level": ACTION_RISK_LEVEL.get(resolved.action, "medium"),
            "preview": resolved.metadata.get("preview", resolved.reason),
            "integration": resolved.metadata.get("integration", "opportunity_engine"),
            "requested_by": resolved.requested_by,
            "approved_by": approved_by,
            "result": resolved.status,
        },
    )
    return resolved


def check_action_allowed(
    *,
    opportunity_id: str,
    action: str,
    human_approved: bool = False,
) -> tuple[bool, str | None]:
    if not is_risky_action(action):
        return True, None
    if human_approved:
        return True, None
    return False, f"{ACTION_LABELS.get(action, action)} blocked until explicit approval"
