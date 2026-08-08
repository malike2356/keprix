"""Soft Wall list enroll preflight (eligible vs suppressed / contactability)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _audience_hash(lead_ids: list[str], sequence_id: str, campaign_id: str | None) -> str:
    payload = {
        "leads": sorted(lead_ids),
        "sequence_id": sequence_id,
        "campaign_id": campaign_id or "",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def preflight_list_enroll(
    *,
    workspace_id: str,
    lead_ids: list[str],
    sequence_id: str,
    campaign_id: str | None = None,
    outreach_store: Any = None,
    crm_store: Any = None,
) -> dict[str, Any]:
    """Classify Soft Wall list members before Soft Wall enroll approve."""
    leads: list[dict[str, Any]] = []
    missing: list[str] = []
    if outreach_store is not None:
        for lid in lead_ids:
            row = outreach_store.get_lead(workspace_id, lid)
            if row:
                leads.append(row)
            else:
                missing.append(lid)

    eligible: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    contactability_deny: list[dict[str, Any]] = []
    duplicate: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    ineligible: list[dict[str, Any]] = []

    seen_emails: dict[str, str] = {}

    for lead in leads:
        lead_id = str(lead.get("id"))
        email = str(lead.get("email") or "").strip().lower()
        status = str(lead.get("status") or "").lower()
        item = {
            "lead_id": lead_id,
            "email": email or None,
            "crm_lead_id": (lead.get("metadata") or {}).get("crm_lead_id")
            if isinstance(lead.get("metadata"), dict)
            else lead.get("crm_lead_id"),
            "status": status,
        }

        if status in {"unsubscribed", "bounced", "do_not_contact", "stopped"}:
            ineligible.append({**item, "reason": f"lead_status_{status}"})
            continue

        if email and email in seen_emails:
            duplicate.append({**item, "reason": "duplicate_email", "other_lead_id": seen_emails[email]})
            continue
        if email:
            seen_emails[email] = lead_id

        if crm_store is not None and email:
            try:
                if crm_store.is_suppressed(workspace_id, channel="email", address=email):
                    suppressed.append(
                        {
                            **item,
                            "reason": "suppressed",
                            "fix_href": "/outreach/suppressions",
                        }
                    )
                    continue
            except Exception:
                pass

            try:
                decisions = crm_store.list_contactability(workspace_id)
                denied = [
                    d
                    for d in decisions
                    if str(d.get("decision")) == "deny"
                    and (
                        str(d.get("subject_id")) == lead_id
                        or str(d.get("subject_id")) == str(item.get("crm_lead_id") or "")
                    )
                    and str(d.get("channel") or "email") == "email"
                ]
                if denied:
                    contactability_deny.append(
                        {
                            **item,
                            "reason": denied[0].get("reason") or "contactability_deny",
                            "fix_href": "/outreach/contactability",
                        }
                    )
                    continue
            except Exception:
                pass

        if not email and not lead.get("phone"):
            ambiguous.append({**item, "reason": "no_channel"})
            continue

        eligible.append(item)

    for mid in missing:
        ineligible.append({"lead_id": mid, "reason": "lead_missing"})

    counts = {
        "total": len(lead_ids),
        "eligible": len(eligible),
        "suppressed": len(suppressed),
        "contactability_deny": len(contactability_deny),
        "duplicate": len(duplicate),
        "ambiguous": len(ambiguous),
        "ineligible": len(ineligible),
    }

    return {
        "workspace_id": workspace_id,
        "sequence_id": sequence_id,
        "campaign_id": campaign_id,
        "audience_hash": _audience_hash([str(x) for x in lead_ids], sequence_id, campaign_id),
        "counts": counts,
        "eligible": eligible,
        "suppressed": suppressed,
        "contactability_deny": contactability_deny,
        "duplicate": duplicate,
        "ambiguous": ambiguous,
        "ineligible": ineligible,
        "note": "Material list or campaign change changes audience_hash and invalidates prior Soft Wall enroll approval.",
    }
