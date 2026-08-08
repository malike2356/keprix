"""CRM list -> Soft Wall outreach enroll glue (prompt 442)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from keprix.crm.models import CrmStage


def _primary_email(row: dict[str, Any]) -> str | None:
    emails = row.get("emails") or []
    for item in emails:
        if isinstance(item, dict):
            addr = str(item.get("address") or "").strip().lower()
            if addr:
                return addr
        else:
            addr = str(item or "").strip().lower()
            if addr:
                return addr
    return None


def _primary_phone(row: dict[str, Any]) -> str | None:
    phones = row.get("phones") or []
    for item in phones:
        if isinstance(item, dict):
            num = str(item.get("number") or item.get("value") or "").strip()
            if num:
                return num
        else:
            num = str(item or "").strip()
            if num:
                return num
    return None


def _audience_hash(member_keys: list[str], sequence_id: str, campaign_id: str | None) -> str:
    payload = {
        "members": sorted(member_keys),
        "sequence_id": sequence_id,
        "campaign_id": campaign_id or "",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _content_hash(sequence_id: str, campaign: dict[str, Any] | None) -> str:
    payload = {
        "sequence_id": sequence_id,
        "campaign_status": (campaign or {}).get("status"),
        "booking": (campaign or {}).get("default_booking_link") or (campaign or {}).get("vical_event_type_id"),
        "daily_cap": (campaign or {}).get("daily_cap"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def preflight_crm_list_enroll(
    *,
    workspace_id: str,
    list_id: str,
    sequence_id: str,
    campaign_id: str | None = None,
    crm_store: Any = None,
    outreach_store: Any = None,
) -> dict[str, Any]:
    """Classify CRM list members before Soft Wall enroll."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()

    lst = crm_store.get_list(workspace_id, list_id)
    if not lst:
        raise LookupError("list_not_found")

    members = crm_store.list_memberships(workspace_id, list_id)
    campaign = None
    if campaign_id:
        campaign = outreach_store.get_campaign(workspace_id, campaign_id)

    # Kill switches
    kill_reasons: list[str] = []
    if crm_store.is_kill_switch_on(workspace_id, scope="workspace"):
        kill_reasons.append("workspace_kill_switch")
    if campaign_id and crm_store.is_kill_switch_on(workspace_id, scope="campaign", scope_id=campaign_id):
        kill_reasons.append("campaign_kill_switch")

    eligible: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    contactability_deny: list[dict[str, Any]] = []
    duplicate: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    ineligible: list[dict[str, Any]] = []
    seen_emails: dict[str, str] = {}
    member_keys: list[str] = []

    for mem in members:
        member_type = str(mem.get("member_type") or "lead")
        member_id = str(mem.get("member_id") or "")
        member_keys.append(f"{member_type}:{member_id}")
        row = None
        if member_type == "contact":
            row = crm_store.get_contact(workspace_id, member_id)
        else:
            row = crm_store.get_lead(workspace_id, member_id)
        if not row:
            ineligible.append(
                {
                    "member_type": member_type,
                    "member_id": member_id,
                    "reason": "member_missing",
                }
            )
            continue

        stage = str(row.get("stage") or "").lower()
        email = _primary_email(row)
        phone = _primary_phone(row)
        item = {
            "member_type": member_type,
            "member_id": member_id,
            "crm_lead_id": member_id if member_type == "lead" else None,
            "crm_contact_id": member_id if member_type == "contact" else None,
            "email": email,
            "phone": phone,
            "name": row.get("name") or row.get("display_name"),
            "stage": stage,
            "company": row.get("company_name"),
        }

        if stage in {"suppressed", "bounced", "do_not_contact", "lost"}:
            ineligible.append({**item, "reason": f"stage_{stage}"})
            continue

        if email and email in seen_emails:
            duplicate.append({**item, "reason": "duplicate_email", "other": seen_emails[email]})
            continue
        if email:
            seen_emails[email] = f"{member_type}:{member_id}"

        if email and crm_store.is_suppressed(workspace_id, channel="email", address=email):
            suppressed.append(
                {
                    **item,
                    "reason": "suppressed",
                    "fix_href": "/crm/suppressions",
                }
            )
            continue
        if phone and crm_store.is_suppressed(workspace_id, channel="phone", address=phone):
            suppressed.append({**item, "reason": "suppressed_phone", "fix_href": "/crm/suppressions"})
            continue

        # Contactability deny
        denied = [
            d
            for d in crm_store.list_contactability(workspace_id)
            if str(d.get("decision")) == "deny"
            and str(d.get("subject_id")) == member_id
            and str(d.get("channel") or "email") in {"email", "any", "*"}
        ]
        if denied:
            contactability_deny.append(
                {
                    **item,
                    "reason": denied[0].get("reason") or "contactability_deny",
                    "fix_href": "/crm/contactability",
                }
            )
            continue

        # ICP exclusions (list stamp or active ICP)
        try:
            from keprix.crm import icp as icp_mod

            icp_id = lst.get("icp_id")
            icp_version = lst.get("icp_version")
            filt = icp_mod.apply_icp_exclusions(
                crm_store,
                workspace_id,
                [row],
                icp_id=str(icp_id) if icp_id else None,
                icp_version=int(icp_version) if icp_version is not None else None,
            )
            if filt.get("excluded"):
                ineligible.append(
                    {
                        **item,
                        "reason": "icp_exclude",
                        "icp_id": (filt.get("icp") or {}).get("id"),
                        "icp_version": (filt.get("icp") or {}).get("version"),
                        "fix_href": "/crm/icp",
                    }
                )
                continue
        except Exception:
            pass

        if not email and not phone:
            ambiguous.append({**item, "reason": "no_channel"})
            continue

        # Consent policy check (soft: missing LI still eligible for Soft Wall review)
        try:
            from keprix.crm.compliance import evaluate_send_policy

            decision = evaluate_send_policy(
                crm_store,
                workspace_id,
                subject_type=member_type,
                subject_id=member_id,
                channel="email" if email else "phone",
                address=email or phone or "",
                purpose="cold_outreach",
            )
            if decision.get("decision") == "deny":
                ineligible.append({**item, "reason": decision.get("reason") or "policy_deny"})
                continue
        except Exception:
            pass

        eligible.append(item)

    counts = {
        "total": len(members),
        "eligible": len(eligible),
        "suppressed": len(suppressed),
        "contactability_deny": len(contactability_deny),
        "duplicate": len(duplicate),
        "ambiguous": len(ambiguous),
        "ineligible": len(ineligible),
        "kill_switch": len(kill_reasons),
    }

    return {
        "workspace_id": workspace_id,
        "list_id": list_id,
        "list_name": lst.get("name"),
        "sequence_id": sequence_id,
        "campaign_id": campaign_id,
        "audience_hash": _audience_hash(member_keys, sequence_id, campaign_id),
        "content_hash": _content_hash(sequence_id, campaign),
        "counts": counts,
        "eligible": eligible,
        "suppressed": suppressed,
        "contactability_deny": contactability_deny,
        "duplicate": duplicate,
        "ambiguous": ambiguous,
        "ineligible": ineligible,
        "kill_reasons": kill_reasons,
        "deep_links": {
            "suppressions": "/crm/suppressions",
            "contactability": "/crm/contactability",
            "outbox": "/crm/outbox",
            "settings": "/crm/settings",
            "deliverability": "/crm/deliverability",
        },
        "note": "Material list or campaign change changes audience_hash and invalidates prior Soft Wall enroll approval.",
    }


def _ensure_outreach_metadata_column(outreach_store: Any) -> None:
    cols = {r[1] for r in outreach_store._conn.execute("PRAGMA table_info(outreach_leads)").fetchall()}
    if "metadata_json" in cols:
        return
    with outreach_store._lock:
        outreach_store._conn.execute("ALTER TABLE outreach_leads ADD COLUMN metadata_json TEXT")
        outreach_store._conn.commit()


def _stamp_lead_metadata(outreach_store: Any, workspace_id: str, lead_id: str, meta: dict[str, Any]) -> None:
    _ensure_outreach_metadata_column(outreach_store)
    with outreach_store._lock:
        outreach_store._conn.execute(
            "UPDATE outreach_leads SET metadata_json = ?, updated_at = datetime('now') WHERE id = ? AND workspace_id = ?",
            (json.dumps(meta, default=str), lead_id, workspace_id),
        )
        outreach_store._conn.commit()


def enroll_list(
    *,
    workspace_id: str,
    list_id: str,
    sequence_id: str | None = None,
    campaign_id: str | None = None,
    audience_hash: str | None = None,
    content_hash: str | None = None,
    require_soft_wall: bool = True,
    force: bool = False,
    approval_id: str | None = None,
    start_immediately: bool = True,
    actor_id: str | None = None,
    crm_store: Any = None,
    outreach_store: Any = None,
    outreach_service: Any = None,
) -> dict[str, Any]:
    """Map CRM list members to Soft Wall leads and enroll after Soft Wall gate.

    Soft Wall approval kind: ``crm.list.enroll``.
    """
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()
    if outreach_service is None:
        from keprix.outreach.service import get_outreach_service

        outreach_service = get_outreach_service(outreach_store)

    seq_id = str(sequence_id or "").strip()
    if not seq_id and campaign_id:
        camp = outreach_store.get_campaign(workspace_id, str(campaign_id))
        seq_id = str((camp or {}).get("default_sequence_id") or "").strip()
    if not seq_id:
        raise ValueError("sequence_id is required")

    # Sender readiness gate for cold campaigns
    try:
        from keprix.crm.deliverability import compute_deliverability_snapshot

        snap = compute_deliverability_snapshot(crm_store, workspace_id)
        if snap.get("soft_wall_block_cold_send") and not force and not approval_id:
            return {
                "blocked": True,
                "error_code": "sender_readiness_required",
                "message": snap.get("soft_wall_block_reason") or "Sender readiness checklist incomplete",
                "deep_link": "/crm/deliverability",
                "deliverability": snap,
            }
    except Exception:
        pass

    report = preflight_crm_list_enroll(
        workspace_id=workspace_id,
        list_id=list_id,
        sequence_id=seq_id,
        campaign_id=campaign_id,
        crm_store=crm_store,
        outreach_store=outreach_store,
    )

    if report.get("kill_reasons"):
        return {
            "blocked": True,
            "error_code": "kill_switch_active",
            "kill_reasons": report["kill_reasons"],
            "preflight": report,
            "deep_link": "/crm/settings",
        }

    if audience_hash and audience_hash != report["audience_hash"]:
        return {
            "blocked": True,
            "error_code": "audience_hash_mismatch",
            "message": "List or campaign changed since preflight; run Soft Wall preflight again.",
            "audience_hash": report["audience_hash"],
            "preflight": report,
        }
    if content_hash and content_hash != report["content_hash"]:
        return {
            "blocked": True,
            "error_code": "content_hash_mismatch",
            "message": "Campaign content changed since preflight; re-run Soft Wall preflight.",
            "content_hash": report["content_hash"],
            "preflight": report,
        }

    if require_soft_wall:
        from keprix.crm.soft_wall import gate_or_approve

        gate = gate_or_approve(
            workspace_id,
            kind="crm.list.enroll",
            subject=f"Enroll CRM list '{report.get('list_name')}' ({report['counts']['eligible']} eligible)",
            payload={
                "list_id": list_id,
                "sequence_id": seq_id,
                "campaign_id": campaign_id,
                "audience_hash": report["audience_hash"],
                "content_hash": report["content_hash"],
                "counts": report["counts"],
                "eligible_ids": [
                    f"{x['member_type']}:{x['member_id']}" for x in report["eligible"]
                ],
            },
            object_type="list",
            object_id=list_id,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "preflight": report,
            }

    # Re-check suppression immediately before enroll (approval-to-send race)
    enrolled: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped_race: list[dict[str, Any]] = []

    for item in report["eligible"]:
        email = item.get("email")
        if email and crm_store.is_suppressed(workspace_id, channel="email", address=email):
            skipped_race.append({**item, "reason": "suppressed_at_send"})
            continue

        idem_key = f"crm_enroll:{list_id}:{item['member_type']}:{item['member_id']}:{seq_id}"
        existing_out = None
        try:
            existing_out = crm_store._fetchone(
                "SELECT * FROM crm_outbox WHERE workspace_id = ? AND idempotency_key = ?",
                (workspace_id, idem_key),
            )
        except Exception:
            pass
        if existing_out and str(existing_out.get("status")) in {"pending", "sent"}:
            skipped_race.append({**item, "reason": "idempotent_duplicate"})
            continue

        try:
            name = str(item.get("name") or "").strip()
            parts = name.split(None, 1) if name else []
            meta = {
                "crm_lead_id": item.get("crm_lead_id"),
                "crm_contact_id": item.get("crm_contact_id"),
                "crm_list_id": list_id,
                "member_type": item["member_type"],
                "member_id": item["member_id"],
            }
            notes = json.dumps({"crm": meta}, default=str)
            created = outreach_store.add_leads(
                workspace_id,
                [
                    {
                        "email": email or f"{item['member_id']}@crm.invalid",
                        "first_name": parts[0] if parts else name or None,
                        "last_name": parts[1] if len(parts) > 1 else None,
                        "company": item.get("company"),
                        "phone": item.get("phone"),
                        "source": "crm_list_enroll",
                        "notes": notes,
                        "tags": ["crm", f"list:{list_id}"],
                        "campaign_id": campaign_id,
                    }
                ],
                campaign_id=campaign_id,
            )
            olead = (created or [None])[0]
            if not olead:
                errors.append({**item, "error": "outreach_lead_create_failed"})
                continue
            _stamp_lead_metadata(outreach_store, workspace_id, olead["id"], meta)
            # Re-fetch with metadata
            result = outreach_service.enroll_lead(
                workspace_id,
                olead["id"],
                seq_id,
                start_immediately=start_immediately,
            )
            # Update CRM stage enrolled
            if item["member_type"] == "lead":
                try:
                    from keprix.crm.stages import apply_stage

                    apply_stage(
                        crm_store,
                        workspace_id,
                        entity_type="lead",
                        entity_id=item["member_id"],
                        to_stage=CrmStage.ENROLLED,
                        soft_wall_approved=True,
                        actor_type="system",
                        actor_id=actor_id or "crm_enroll",
                        reason="list_enroll",
                    )
                except Exception:
                    crm_store.update_lead(workspace_id, item["member_id"], stage=CrmStage.ENROLLED)
            elif item["member_type"] == "contact":
                try:
                    crm_store.update_contact(workspace_id, item["member_id"], stage=CrmStage.ENROLLED)
                except Exception:
                    pass

            crm_store.enqueue_outbox(
                workspace_id,
                kind="crm_list_enroll",
                idempotency_key=idem_key,
                payload={
                    "list_id": list_id,
                    "sequence_id": seq_id,
                    "outreach_lead_id": olead["id"],
                    "member_type": item["member_type"],
                    "member_id": item["member_id"],
                },
                entity_type=item["member_type"],
                entity_id=item["member_id"],
                status="sent",
            )
            try:
                from keprix.crm.funnel_analytics import record_funnel_event

                record_funnel_event(workspace_id, "enrolled", campaign_id=campaign_id)
            except Exception:
                pass

            enrolled.append(
                {
                    "member_type": item["member_type"],
                    "member_id": item["member_id"],
                    "outreach_lead_id": olead["id"],
                    "enrollment": result.get("enrollment"),
                    "crm_deep_link": f"/crm/{'leads' if item['member_type']=='lead' else 'contacts'}/{item['member_id']}",
                }
            )
        except Exception as exc:
            errors.append({**item, "error": str(exc)})
            try:
                crm_store.enqueue_outbox(
                    workspace_id,
                    kind="crm_list_enroll",
                    idempotency_key=f"{idem_key}:err:{hash(str(exc)) % 10_000}",
                    payload={"error": str(exc), "member": item},
                    entity_type=item["member_type"],
                    entity_id=item["member_id"],
                    status="dead_letter",
                )
            except Exception:
                pass

    try:
        crm_store.update_list(workspace_id, list_id, status="enrolled", stage=CrmStage.ENROLLED)
    except Exception:
        pass

    return {
        "blocked": False,
        "enrolled_count": len(enrolled),
        "enrolled": enrolled,
        "errors": errors,
        "skipped_race": skipped_race,
        "skipped": {
            "suppressed": report["counts"]["suppressed"],
            "contactability_deny": report["counts"]["contactability_deny"],
            "duplicate": report["counts"]["duplicate"],
            "ambiguous": report["counts"]["ambiguous"],
            "ineligible": report["counts"]["ineligible"],
        },
        "audience_hash": report["audience_hash"],
        "content_hash": report["content_hash"],
        "preflight": report,
    }
