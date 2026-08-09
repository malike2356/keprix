"""UI-facing outreach / Sales engagement under /api/outreach (session auth).

Mirrors the Aiva Soft Wall sales engagement surface for standalone Keprix.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from keprix.api.auth import require_api_auth
from keprix.outreach.ops import get_outreach_ops_store
from keprix.outreach.service import get_outreach_service
from keprix.outreach.store import get_outreach_store

router = APIRouter(prefix="/api/outreach", tags=["outreach-ui"])


def _workspace(workspace_id: str | None, x_workspace_id: str | None) -> str:
    return (workspace_id or x_workspace_id or "default").strip() or "default"


def _svc():
    return get_outreach_service()


def _ops():
    return get_outreach_ops_store()


def _store():
    return get_outreach_store()


def _lead_from_body(body: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single-lead create payload (name/email style) into store fields."""
    email = str(body.get("email") or "").strip()
    name = str(body.get("name") or "").strip()
    first = str(body.get("first_name") or "").strip()
    last = str(body.get("last_name") or "").strip()
    if name and not (first or last):
        parts = name.split(None, 1)
        first = parts[0] if parts else name
        last = parts[1] if len(parts) > 1 else ""
    return {
        "email": email,
        "first_name": first or None,
        "last_name": last or None,
        "company": body.get("company"),
        "phone": body.get("phone"),
        "source": body.get("source") or "manual",
        "source_url": body.get("source_url"),
        "tags": body.get("tags"),
        "notes": body.get("notes"),
    }


# ── Overview + control ─────────────────────────────────────────


@router.get("/overview")
def overview(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    return _svc().get_overview(_workspace(workspace_id, x_workspace_id))


@router.get("/control")
def get_control(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    state = _ops().get_control(ws)
    return {
        "state": {
            **state,
            "paused": bool(state.get("paused")),
        }
    }


@router.patch("/control")
def patch_control(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    action = str(body.get("action") or "").strip().lower()
    if action not in ("pause", "resume"):
        raise HTTPException(status_code=422, detail="action must be pause or resume")
    state = _ops().set_control(
        ws,
        paused=(action == "pause"),
        reason=body.get("reason") or (f"Operator {action} from control center"),
        updated_by=str(_user or "web-ui"),
    )
    return {"state": {**state, "paused": bool(state.get("paused"))}}


# ── Pipeline ───────────────────────────────────────────────────


@router.get("/pipeline")
def pipeline(
    workspace_id: str | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    return _svc().get_pipeline(_workspace(workspace_id, x_workspace_id), campaign_id=campaign_id)


@router.get("/pipeline/board")
def pipeline_board(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    return _svc().get_pipeline_board(_workspace(workspace_id, x_workspace_id))


# ── Leads ──────────────────────────────────────────────────────


@router.get("/leads")
def list_leads(
    workspace_id: str | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = [_svc()._present_lead(x) for x in _store().list_leads(ws, campaign_id=campaign_id, status=status, limit=limit)]
    return {"workspace_id": ws, "leads": items, "count": len(items)}


@router.post("/leads")
def create_or_add_leads(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    if body.get("leads") or body.get("csv_text") or body.get("csv"):
        return _svc().add_leads(
            ws,
            leads=body.get("leads"),
            csv_text=body.get("csv_text") or body.get("csv"),
            campaign_id=body.get("campaign_id"),
        )
    lead = _lead_from_body(body)
    if not lead.get("email"):
        raise HTTPException(status_code=422, detail="email is required")
    result = _svc().add_leads(ws, leads=[lead], campaign_id=body.get("campaign_id"))
    created = result.get("leads") or []
    return {
        "created": result.get("created"),
        "leads": created,
        "lead": created[0] if created else None,
    }


@router.post("/leads/import")
def import_leads(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    leads = list(body.get("leads") or [])
    csv_text = body.get("csv_text") or body.get("csv")
    lines = body.get("lines")
    if lines and not leads and not csv_text:
        leads = _svc().parse_pipe_leads(str(lines))
    return _svc().add_leads(ws, leads=leads or None, csv_text=csv_text, campaign_id=body.get("campaign_id"))


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    lead = _store().get_lead(ws, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return {"lead": _svc()._present_lead(lead), "deliveries": []}


@router.patch("/leads/{lead_id}")
def patch_lead(
    lead_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    lead = _store().get_lead(ws, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if body.get("status"):
        try:
            lead = _svc().move_lead(ws, lead_id, str(body["status"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    notes = body.get("notes")
    tags = body.get("tags")
    if notes is not None or tags is not None:
        import json

        with _store()._lock:
            if notes is not None:
                _store()._conn.execute(
                    "UPDATE outreach_leads SET notes = ?, updated_at = outreach_leads.updated_at WHERE id = ? AND workspace_id = ?",
                    (str(notes), lead_id, ws),
                )
            if tags is not None:
                _store()._conn.execute(
                    "UPDATE outreach_leads SET tags = ? WHERE id = ? AND workspace_id = ?",
                    (json.dumps(tags) if not isinstance(tags, str) else tags, lead_id, ws),
                )
            _store()._conn.commit()
        lead = _store().get_lead(ws, lead_id)
    return {"lead": _svc()._present_lead(lead or {})}


# ── Enrollments ────────────────────────────────────────────────


@router.post("/enrollments")
def enroll(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    lead_id = str(body.get("lead_id") or "").strip()
    sequence_id = str(body.get("sequence_id") or "").strip()
    if not lead_id or not sequence_id:
        raise HTTPException(status_code=422, detail="lead_id and sequence_id are required")
    try:
        result = _svc().enroll_lead(ws, lead_id, sequence_id, start_immediately=bool(body.get("start_immediately", True)))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    campaign_id = body.get("campaign_id")
    if campaign_id:
        with _store()._lock:
            _store()._conn.execute(
                "UPDATE outreach_leads SET campaign_id = ? WHERE id = ? AND workspace_id = ?",
                (str(campaign_id), lead_id, ws),
            )
            _store()._conn.commit()
    return result


# ── Campaigns ──────────────────────────────────────────────────


@router.get("/campaigns")
def list_campaigns(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = _store().list_campaigns(ws)
    return {"workspace_id": ws, "campaigns": items, "count": len(items)}


@router.post("/campaigns")
def create_campaign(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    campaign = _svc().create_campaign(
        ws,
        name,
        status=body.get("status") or "active",
        source_type=body.get("source_type"),
        daily_cap=body.get("daily_cap"),
        timezone=body.get("timezone"),
        business_hours_only=body.get("business_hours_only"),
        warmup_days=body.get("warmup_days"),
        require_approval=body.get("require_approval", True),
        default_sequence_id=body.get("default_sequence_id"),
        default_booking_link=body.get("default_booking_link"),
    )
    return {"campaign": campaign}


@router.patch("/campaigns/{campaign_id}")
def patch_campaign(
    campaign_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    campaign = _svc().update_campaign(ws, campaign_id, **body)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign_not_found")
    return {"campaign": campaign}


# ── Sequences ──────────────────────────────────────────────────


@router.get("/sequences")
def list_sequences(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = _store().list_sequences(ws)
    return {"workspace_id": ws, "sequences": items, "count": len(items)}


@router.post("/sequences")
def create_sequence(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    name = str(body.get("name") or "").strip()
    steps = body.get("steps")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if not isinstance(steps, list) or len(steps) < 1:
        raise HTTPException(status_code=422, detail="steps must be a non-empty array")
    try:
        sequence = _svc().create_sequence(
            ws,
            name,
            steps=steps,
            channel_default=body.get("channel_default"),
            stop_on_reply=body.get("stop_on_reply"),
            stop_on_booking=body.get("stop_on_booking"),
            stop_on_unsubscribe=body.get("stop_on_unsubscribe"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"sequence": sequence}


@router.patch("/sequences/{sequence_id}")
def patch_sequence(
    sequence_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    sequence = _svc().update_sequence(ws, sequence_id, **body)
    if not sequence:
        raise HTTPException(status_code=404, detail="sequence_not_found")
    return {"sequence": sequence}


# ── Replies ────────────────────────────────────────────────────


@router.get("/replies")
def list_replies(
    workspace_id: str | None = Query(default=None),
    resolved: int | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    resolved_flag: bool | None = None if resolved is None else bool(resolved)
    items = _svc().list_replies(ws, resolved=resolved_flag)
    return {"workspace_id": ws, "replies": items, "reviews": items, "count": len(items)}


@router.post("/replies/inbound")
def inbound_reply(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    from_email = str(body.get("from_email") or body.get("fromEmail") or "").strip()
    if not from_email and not body.get("lead_id"):
        raise HTTPException(status_code=422, detail="from_email or lead_id is required")
    try:
        result = _svc().classify_and_apply_reply(
            ws,
            from_address=from_email or "unknown@invalid",
            body=str(body.get("body") or ""),
            subject=str(body.get("subject") or ""),
            lead_id=body.get("lead_id"),
            classification=body.get("classification"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/replies/{reply_id}/resolve")
def resolve_reply(
    reply_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _svc().resolve_reply(
        ws,
        reply_id,
        classification=body.get("classification"),
        note=body.get("note"),
    )
    if not row:
        raise HTTPException(status_code=404, detail="reply_not_found")
    return {"reply": row}


# ── Lists ──────────────────────────────────────────────────────


@router.get("/lists")
def list_lists(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = _ops().list_lists(ws)
    return {"workspace_id": ws, "lists": items, "count": len(items)}


@router.post("/lists")
def create_list(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    row = _ops().create_list(
        ws,
        name,
        description=body.get("description"),
        tags=body.get("tags"),
        lead_ids=body.get("lead_ids"),
    )
    return {"list": row}


@router.patch("/lists/{list_id}")
def patch_list(
    list_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _ops().update_list(ws, list_id, **body)
    if not row:
        raise HTTPException(status_code=404, detail="list_not_found")
    return {"list": row}


@router.post("/lists/{list_id}/leads")
def add_list_leads(
    list_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    lead_ids = body.get("lead_ids") or []
    if not isinstance(lead_ids, list):
        raise HTTPException(status_code=422, detail="lead_ids must be an array")
    row = _ops().add_list_members(ws, list_id, [str(x) for x in lead_ids])
    if not row:
        raise HTTPException(status_code=404, detail="list_not_found")
    return {"list": row}


@router.post("/lists/{list_id}/enroll-preflight")
def list_enroll_preflight(
    list_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    """Preflight Soft Wall list -> sequence enroll with eligibility counts."""
    from keprix.outreach.enroll_preflight import preflight_list_enroll

    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    lists = _ops().list_lists(ws)
    lst = next((x for x in lists if x.get("id") == list_id), None)
    if not lst:
        raise HTTPException(status_code=404, detail="list_not_found")
    sequence_id = str(body.get("sequence_id") or "").strip()
    if not sequence_id:
        raise HTTPException(status_code=422, detail="sequence_id is required")
    campaign_id = body.get("campaign_id")
    lead_ids = [str(x) for x in (lst.get("lead_ids") or [])]
    crm_store = None
    try:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    except Exception:
        crm_store = None
    report = preflight_list_enroll(
        workspace_id=ws,
        lead_ids=lead_ids,
        sequence_id=sequence_id,
        campaign_id=str(campaign_id) if campaign_id else None,
        outreach_store=_store(),
        crm_store=crm_store,
    )
    report["list_id"] = list_id
    report["list_name"] = lst.get("name")
    report["deep_links"] = {
        "suppressions": "/outreach/suppressions",
        "contactability": "/outreach/contactability",
        "outbox": "/outreach/outbox",
        "approvals": "/outreach/approvals",
        "settings": "/outreach/settings",
    }
    return report


@router.post("/lists/{list_id}/enroll")
def list_enroll_execute(
    list_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    """Enroll eligible Soft Wall list members after Soft Wall preflight.

    Requires audience_hash from enroll-preflight. Skips suppressed / deny.
    Creates Soft Wall approval when require_soft_wall is true (default).
    """
    from keprix.crm.soft_wall import gate_or_approve
    from keprix.outreach.enroll_preflight import preflight_list_enroll

    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    lists = _ops().list_lists(ws)
    lst = next((x for x in lists if x.get("id") == list_id), None)
    if not lst:
        raise HTTPException(status_code=404, detail="list_not_found")
    sequence_id = str(body.get("sequence_id") or "").strip()
    if not sequence_id:
        raise HTTPException(status_code=422, detail="sequence_id is required")
    campaign_id = body.get("campaign_id")
    expected_hash = str(body.get("audience_hash") or "").strip()
    lead_ids = [str(x) for x in (lst.get("lead_ids") or [])]
    crm_store = None
    try:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    except Exception:
        crm_store = None
    report = preflight_list_enroll(
        workspace_id=ws,
        lead_ids=lead_ids,
        sequence_id=sequence_id,
        campaign_id=str(campaign_id) if campaign_id else None,
        outreach_store=_store(),
        crm_store=crm_store,
    )
    if expected_hash and expected_hash != report["audience_hash"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "audience_hash_mismatch",
                "message": "List or campaign changed since preflight; run Soft Wall preflight again.",
                "audience_hash": report["audience_hash"],
            },
        )
    if body.get("require_soft_wall", True):
        gate = gate_or_approve(
            ws,
            kind="approve_list_enroll",
            subject=f"Enroll Soft Wall list '{lst.get('name')}' ({report['counts']['eligible']} eligible)",
            payload={
                "list_id": list_id,
                "sequence_id": sequence_id,
                "campaign_id": campaign_id,
                "audience_hash": report["audience_hash"],
                "counts": report["counts"],
            },
            object_type="outreach_list",
            object_id=list_id,
            actor_id=str(_user),
            force=bool(body.get("force")),
            approval_id=body.get("approval_id"),
        )
        if gate.get("blocked"):
            return {
                "blocked": True,
                "error_code": gate.get("error_code"),
                "approval": gate.get("approval"),
                "preflight": report,
            }

    enrolled = []
    errors = []
    for item in report["eligible"]:
        try:
            result = _svc().enroll_lead(
                ws,
                item["lead_id"],
                sequence_id,
                start_immediately=bool(body.get("start_immediately", True)),
            )
            enrolled.append({"lead_id": item["lead_id"], "enrollment": result.get("enrollment")})
            if campaign_id:
                with _store()._lock:
                    _store()._conn.execute(
                        "UPDATE outreach_leads SET campaign_id = ? WHERE id = ? AND workspace_id = ?",
                        (str(campaign_id), item["lead_id"], ws),
                    )
                    _store()._conn.commit()
            # Outbox visibility for enroll event
            if crm_store is not None:
                try:
                    crm_store.enqueue_outbox(
                        ws,
                        kind="soft_wall_enroll",
                        idempotency_key=f"enroll:{list_id}:{item['lead_id']}:{sequence_id}",
                        payload={"lead_id": item["lead_id"], "sequence_id": sequence_id},
                        entity_type="lead",
                        entity_id=item["lead_id"],
                        status="pending",
                    )
                except Exception:
                    pass
        except Exception as exc:
            errors.append({"lead_id": item["lead_id"], "error": str(exc)})

    return {
        "blocked": False,
        "enrolled_count": len(enrolled),
        "enrolled": enrolled,
        "errors": errors,
        "skipped": {
            "suppressed": report["counts"]["suppressed"],
            "contactability_deny": report["counts"]["contactability_deny"],
            "duplicate": report["counts"]["duplicate"],
            "ambiguous": report["counts"]["ambiguous"],
            "ineligible": report["counts"]["ineligible"],
        },
        "audience_hash": report["audience_hash"],
        "preflight": report,
    }


# ── Bookings ───────────────────────────────────────────────────


@router.get("/bookings")
def list_bookings(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = _ops().list_bookings(ws)
    return {"workspace_id": ws, "bookings": items, "count": len(items)}


@router.post("/bookings")
def create_booking(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    lead_id = str(body.get("lead_id") or "").strip()
    starts_at = str(body.get("starts_at") or "").strip()
    if not lead_id or not starts_at:
        raise HTTPException(status_code=422, detail="lead_id and starts_at are required")
    row = _ops().create_booking(
        ws,
        lead_id,
        starts_at,
        ends_at=body.get("ends_at"),
        status=body.get("status"),
        notes=body.get("notes"),
        attendee_name=body.get("attendee_name"),
        attendee_email=body.get("attendee_email"),
    )
    try:
        _svc().move_lead(ws, lead_id, "booking")
    except Exception:
        pass
    return {"booking": row}


@router.post("/bookings/{booking_id}/status")
def booking_status(
    booking_id: str,
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    status = str(body.get("status") or "").strip()
    if not status:
        raise HTTPException(status_code=422, detail="status is required")
    row = _ops().update_booking_status(ws, booking_id, status)
    if not row:
        raise HTTPException(status_code=404, detail="booking_not_found")
    return {"booking": row}


# ── Soft Wall approvals ────────────────────────────────────────


@router.get("/approvals")
def list_approvals(
    workspace_id: str | None = Query(default=None),
    status: str = Query("pending"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    items = _ops().list_approvals(ws, status=status)
    return {"workspace_id": ws, "approvals": items, "count": len(items)}


@router.post("/approvals/{approval_id}/approve")
def approve_send(
    approval_id: str,
    body: dict[str, Any] | None = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    body = body or {}
    try:
        result = _svc().approve_soft_wall(
            ws,
            approval_id,
            dry_run=bool(body.get("dry_run") or False),
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="approval_not_found") from None
    if not result.get("ok"):
        return {**result, "approval": result.get("approval")}
    return {"ok": True, **result}


@router.post("/approvals/{approval_id}/reject")
def reject_send(
    approval_id: str,
    body: dict[str, Any] | None = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    body = body or {}
    try:
        result = _svc().reject_soft_wall(
            ws,
            approval_id,
            stop_status=str(body.get("stop_status") or "cancelled"),
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="approval_not_found") from None
    return {"ok": True, **result}


# ── Process due + Companies House ──────────────────────────────


@router.post("/process-due")
def process_due(
    body: dict[str, Any] | None = None,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    body = body or {}
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    # Soft Wall default: queue approvals unless caller asks for dry_run
    dry_run = body.get("dry_run")
    if dry_run is None:
        dry_run = False
    return _svc().process_due(
        ws,
        limit=int(body.get("limit") or 50),
        dry_run=bool(dry_run),
        worker_id=str(body.get("worker_id") or "") or None,
        lease_seconds=int(body.get("lease_seconds") or 60),
    )


@router.get("/scheduler/health")
def scheduler_health(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    return _svc().get_scheduler_health(ws)


@router.post("/enrollments/{enrollment_id}/pause")
def pause_enrollment(
    enrollment_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _store().get_enrollment(enrollment_id, workspace_id=ws)
    if not row:
        raise HTTPException(status_code=404, detail="enrollment_not_found")
    updated = _store().pause_enrollment(enrollment_id, reason="operator_pause")
    return {"ok": True, "enrollment": updated}


@router.post("/enrollments/{enrollment_id}/resume")
def resume_enrollment(
    enrollment_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _store().get_enrollment(enrollment_id, workspace_id=ws)
    if not row:
        raise HTTPException(status_code=404, detail="enrollment_not_found")
    updated = _store().resume_enrollment(enrollment_id)
    return {"ok": True, "enrollment": updated}


@router.post("/enrollments/{enrollment_id}/cancel")
def cancel_enrollment(
    enrollment_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _store().get_enrollment(enrollment_id, workspace_id=ws)
    if not row:
        raise HTTPException(status_code=404, detail="enrollment_not_found")
    updated = _store().cancel_enrollment(enrollment_id, reason="operator_cancel")
    return {"ok": True, "enrollment": updated}


@router.post("/enrollments/{enrollment_id}/retry")
def retry_enrollment(
    enrollment_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id)
    row = _store().get_enrollment(enrollment_id, workspace_id=ws)
    if not row:
        raise HTTPException(status_code=404, detail="enrollment_not_found")
    updated = _store().retry_dead_letter(enrollment_id)
    return {"ok": True, "enrollment": updated}


@router.post("/companies-house/import-lead")
def import_ch_lead(
    body: dict[str, Any],
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: str = Depends(require_api_auth),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id)
    if not str(body.get("company_name") or body.get("company_number") or "").strip():
        raise HTTPException(status_code=422, detail="company_name or company_number is required")
    return _svc().import_companies_house_lead(ws, body)
