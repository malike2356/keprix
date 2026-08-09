"""Channel spreadsheet journey: import → enrich → list → Soft Wall campaign (Prompt 627).

One durable pipeline for authorised channel attachment instructions. Reply monitoring
reuses existing ``scan_replies``; do not reimplement mailbox reconciliation here.
"""

from __future__ import annotations

import hashlib
from typing import Any

from keprix.crm.models import CrmStage
from keprix.crm.soft_wall import gate_or_approve

JOURNEY_STEPS = (
    "ingest",
    "enrich",
    "add_to_list",
    "draft_campaign",
    "enroll",
    "monitor_replies",
    "digest_outcomes",
)


def _primary_email(row: dict[str, Any]) -> str | None:
    for item in row.get("emails") or []:
        if isinstance(item, dict):
            addr = str(item.get("address") or "").strip()
            if addr:
                return addr
        elif str(item or "").strip():
            return str(item).strip()
    return None


def _eligible_leads(store: Any, workspace_id: str, lead_ids: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for lid in lead_ids:
        lead = store.get_lead(workspace_id, lid)
        if not lead:
            continue
        stage = str(lead.get("stage") or "")
        if stage in {CrmStage.SUPPRESSED, CrmStage.DO_NOT_CONTACT, CrmStage.BOUNCED, CrmStage.LOST}:
            continue
        email = _primary_email(lead)
        if email and store.is_suppressed(workspace_id, channel="email", address=email):
            continue
        out.append(lead)
    return out


def run_channel_journey(
    workspace_id: str,
    *,
    payload: bytes | None = None,
    filename: str | None = None,
    channel: str = "telegram",
    list_name: str | None = None,
    list_id: str | None = None,
    campaign_name: str | None = None,
    sequence_id: str | None = None,
    skip_enrich: bool = False,
    approve_enroll: bool = False,
    approval_id: str | None = None,
    force: bool = False,
    actor_id: str | None = None,
    crm_store: Any = None,
    upload_id: str | None = None,
) -> dict[str, Any]:
    """
    Steps:
    1. ingest_channel_attachment / sheet upload
    2. soft-wall enrich propose (or skip if already enriched)
    3. add eligible leads to list
    4. draft campaign/sequence proposal → Soft Wall approval
    5. after approve: enroll eligible
    6. monitor replies via existing scan_replies hook (pointer only)
    7. report outcomes via funnel digest
    """
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()

    ws = crm_store._require_workspace(workspace_id)
    steps: list[dict[str, Any]] = []
    lead_ids: list[str] = []
    ingest_result: dict[str, Any] | None = None
    enrich_job: dict[str, Any] | None = None

    # 1. Ingest
    if payload is not None and filename:
        from keprix.crm.ingestion import ingest_channel_attachment

        ingest_result = ingest_channel_attachment(
            ws,
            payload,
            filename=filename,
            store=crm_store,
            channel=channel,
        )
        for lid in ingest_result.get("created_ids") or []:
            lead_ids.append(str(lid))
        for lid in ingest_result.get("updated_ids") or []:
            lead_ids.append(str(lid))
        steps.append({"step": "ingest", "status": "completed", "result": {
            "created_count": ingest_result.get("created"),
            "updated_count": ingest_result.get("updated"),
            "lead_ids": lead_ids[:50],
            "job_id": ingest_result.get("job_id"),
        }})
    elif upload_id:
        from keprix.sheet_preprocess import service as sheet_service

        meta = {"upload_id": upload_id}
        steps.append({"step": "ingest", "status": "skipped", "result": meta, "note": "using existing upload_id"})
    else:
        steps.append({"step": "ingest", "status": "skipped", "reason": "no_payload"})

    # 2. Enrich propose (Soft Wall before CRM write on apply)
    if skip_enrich:
        steps.append({"step": "enrich", "status": "skipped", "reason": "skip_enrich"})
    elif payload is not None and filename:
        try:
            from keprix.sheet_preprocess import service as sheet_service

            upload_meta = sheet_service.save_upload(
                ws,
                filename=filename,
                content=payload,
                actor_type="channel",
                actor_id=actor_id or channel,
            )
            enrich_job = sheet_service.propose_sheet(
                ws,
                upload_id=upload_meta["upload_id"],
                actor_type="channel",
                actor_id=actor_id or channel,
            )
            gate = gate_or_approve(
                ws,
                kind="apply_enrichment",
                subject=f"Channel journey enrich ({channel})",
                payload={"upload_id": upload_meta["upload_id"], "job_id": enrich_job.get("id")},
                object_type="enrichment_job",
                object_id=str(enrich_job.get("id") or ""),
                actor_id=actor_id,
                force=force,
            )
            steps.append({
                "step": "enrich",
                "status": "proposed" if gate.get("blocked") else "ready",
                "job": enrich_job,
                "soft_wall": gate,
            })
        except Exception as exc:
            steps.append({"step": "enrich", "status": "failed", "error": str(exc)})
    else:
        steps.append({"step": "enrich", "status": "skipped", "reason": "no_sheet_bytes"})

    # Collect leads if still empty
    if not lead_ids:
        for lead in crm_store.list_leads(ws, limit=100):
            if str(lead.get("source") or "").startswith(channel) or str(lead.get("source_type") or "") == "channel_attachment":
                lead_ids.append(str(lead["id"]))

    eligible = _eligible_leads(crm_store, ws, list(dict.fromkeys(lead_ids)))

    # 3. Add to list
    lst = None
    if list_id:
        lst = crm_store.get_list(ws, list_id)
    if not lst:
        lst = crm_store.create_list(
            ws,
            list_name or f"Channel journey ({channel})",
            source=f"channel_journey:{channel}",
            stage=CrmStage.LISTED,
            actor_type="channel",
            actor_id=actor_id or channel,
        )
    memberships = []
    for lead in eligible:
        memberships.append(
            crm_store.add_list_member(ws, lst["id"], member_type="lead", member_id=lead["id"], stage=lead.get("stage"))
        )
        try:
            from keprix.crm.stages import apply_stage

            if str(lead.get("stage") or "") in {CrmStage.DISCOVERED, CrmStage.ENRICHED}:
                apply_stage(
                    crm_store,
                    ws,
                    entity_type="lead",
                    entity_id=lead["id"],
                    to_stage=CrmStage.LISTED,
                    soft_wall_approved=True,
                    actor_type="channel",
                    actor_id=actor_id or channel,
                    reason="channel_journey_list",
                )
        except Exception:
            pass
    steps.append({
        "step": "add_to_list",
        "status": "completed",
        "list_id": lst["id"],
        "added": len(memberships),
        "eligible": len(eligible),
    })

    # 4. Draft campaign Soft Wall proposal
    from keprix.outreach.service import get_outreach_service
    from keprix.outreach.store import get_outreach_store
    from keprix.crm.nurture import ensure_default_nurture_sequence

    ostore = get_outreach_store()
    svc = get_outreach_service(ostore)
    if not sequence_id:
        nurture = ensure_default_nurture_sequence(ws, outreach_service=svc, outreach_store=ostore)
        sequence_id = (nurture.get("sequence") or {}).get("id")
    campaign = svc.create_campaign(
        ws,
        campaign_name or f"Channel journey campaign ({channel})",
        default_sequence_id=sequence_id,
        status="draft",
        require_approval=True,
    )
    audience_key = hashlib.sha256(
        f"{ws}:{lst['id']}:{sequence_id}:{len(eligible)}".encode()
    ).hexdigest()[:16]
    draft_gate = gate_or_approve(
        ws,
        kind="channel_journey_campaign",
        subject=f"Approve channel campaign '{campaign.get('name')}' ({len(eligible)} leads)",
        payload={
            "campaign_id": campaign.get("id"),
            "sequence_id": sequence_id,
            "list_id": lst["id"],
            "eligible_count": len(eligible),
            "audience_key": audience_key,
            "channel": channel,
        },
        object_type="list",
        object_id=lst["id"],
        actor_id=actor_id,
        force=force or approve_enroll,
        approval_id=approval_id,
    )
    steps.append({
        "step": "draft_campaign",
        "status": "blocked" if draft_gate.get("blocked") else "approved",
        "campaign": campaign,
        "sequence_id": sequence_id,
        "soft_wall": draft_gate,
    })

    # 5. Enroll after approve
    enroll_result: dict[str, Any] | None = None
    if draft_gate.get("blocked") and not (force or approve_enroll):
        steps.append({"step": "enroll", "status": "waiting_approval", "approval": draft_gate.get("approval")})
    else:
        from keprix.crm.enroll import enroll_list

        enroll_result = enroll_list(
            workspace_id=ws,
            list_id=lst["id"],
            sequence_id=sequence_id,
            campaign_id=campaign.get("id"),
            require_soft_wall=not (force or approve_enroll or approval_id),
            force=force or approve_enroll,
            approval_id=approval_id or (draft_gate.get("approval") or {}).get("id") if not draft_gate.get("blocked") else approval_id,
            actor_id=actor_id,
            crm_store=crm_store,
            outreach_store=ostore,
            outreach_service=svc,
        )
        steps.append({
            "step": "enroll",
            "status": "blocked" if enroll_result.get("blocked") else "completed",
            "result": enroll_result,
        })

    # 6. Monitor replies: hook pointer only (626 owns mailbox)
    steps.append({
        "step": "monitor_replies",
        "status": "hooked",
        "hook": "outreach.scan_replies",
        "note": "Use existing mailbox scan; do not reconcile via email_ingest.",
    })

    # 7. Digest
    from keprix.crm.funnel_analytics import build_digest

    digest = build_digest(ws, hours=24, crm_store=crm_store)
    steps.append({"step": "digest_outcomes", "status": "completed", "digest": digest})

    status = "waiting_approval" if any(s.get("status") == "waiting_approval" or s.get("status") == "blocked" for s in steps if s.get("step") in {"draft_campaign", "enroll"}) else "completed"
    return {
        "ok": True,
        "workspace_id": ws,
        "channel": channel,
        "status": status,
        "list_id": lst["id"],
        "campaign_id": campaign.get("id"),
        "sequence_id": sequence_id,
        "lead_ids": [l["id"] for l in eligible],
        "steps": steps,
        "ingest": ingest_result,
        "enrich_job": enrich_job,
        "enroll": enroll_result,
        "digest": digest,
        "deep_links": {
            "list": f"/crm/lists/{lst['id']}",
            "jobs": "/crm/jobs",
            "approvals": "/crm",
            "outreach": "/outreach",
        },
    }


def journey_status(workspace_id: str, *, list_id: str | None = None, crm_store: Any = None) -> dict[str, Any]:
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    from keprix.crm.soft_wall import pending_crm_approvals
    from keprix.crm.funnel_analytics import funnel_snapshot

    pending = [
        a for a in pending_crm_approvals(workspace_id)
        if str(a.get("approval_kind") or "") in {"channel_journey_campaign", "apply_enrichment", "crm.list.enroll"}
    ]
    snap = funnel_snapshot(workspace_id, crm_store=crm_store)
    return {
        "workspace_id": workspace_id,
        "list_id": list_id,
        "pending_approvals": pending,
        "funnel": snap.get("metrics"),
        "steps": list(JOURNEY_STEPS),
    }
