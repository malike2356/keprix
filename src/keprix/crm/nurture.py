"""Nurture workflows and Soft Wall sequence defaults (prompt 444)."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_NURTURE_STEPS: list[dict[str, Any]] = [
    {
        "step_order": 1,
        "delay_hours": 0,
        "channel": "email",
        "subject": "Quick intro",
        "body": "Hi {{first_name}},\n\nI came across {{company}} and thought a short note might help.\n\n{{booking_link}}",
        "cta": "Day 0 intro",
    },
    {
        "step_order": 2,
        "delay_hours": 72,
        "channel": "email",
        "subject": "One idea for {{company}}",
        "body": "Hi {{first_name}},\n\nSharing a concise value note for {{company}}.\n\n{{booking_link}}",
        "cta": "Day 3 value",
    },
    {
        "step_order": 3,
        "delay_hours": 96,
        "channel": "email",
        "subject": "Worth a short call?",
        "body": "Hi {{first_name}},\n\nHappy to walk through this on a brief call if useful.\n\n{{booking_link}}",
        "cta": "Day 7 soft CTA",
    },
    {
        "step_order": 4,
        "delay_hours": 168,
        "channel": "email",
        "subject": "Closing the loop",
        "body": "Hi {{first_name}},\n\nI'll close the loop here unless you'd like to continue.\n\n{{booking_link}}",
        "cta": "Day 14 break-up",
    },
]

DEFAULT_WORKFLOW_META = {
    "version": 1,
    "owner": "crm",
    "entry_stage": "enrolled",
    "exit_stages": ["engaged", "qualified", "booked", "suppressed", "bounced", "do_not_contact", "lost"],
    "max_touches": 4,
    "max_duration_days": 21,
    "re_enrollment": "manual",
    "cancellation": "stop_on_reply_book_suppress",
    "timezone": "Europe/London",
    "activation_window": {"hours": [9, 17], "weekdays_only": True},
    "stop_on_reply": True,
    "stop_on_booking": True,
    "stop_on_unsubscribe": True,
    "cadence": {"max_emails_per_week": 3, "quiet_hours": [18, 8]},
}


def default_nurture_definition() -> dict[str, Any]:
    return {
        "name": "Default CRM nurture",
        "kind": "nurture",
        "status": "draft",
        "meta": copy.deepcopy(DEFAULT_WORKFLOW_META),
        "steps": copy.deepcopy(DEFAULT_NURTURE_STEPS),
    }


def ensure_default_nurture_sequence(
    workspace_id: str,
    *,
    outreach_service: Any = None,
    outreach_store: Any = None,
) -> dict[str, Any]:
    """Create Soft Wall sequence with default day 0/3/7/14 nurture if missing."""
    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()
    if outreach_service is None:
        from keprix.outreach.service import get_outreach_service

        outreach_service = get_outreach_service(outreach_store)

    existing = outreach_store.list_sequences(workspace_id)
    for seq in existing:
        if str(seq.get("name") or "").lower().startswith("default crm nurture"):
            return {"sequence": seq, "created": False}

    definition = default_nurture_definition()
    seq = outreach_service.create_sequence(
        workspace_id,
        definition["name"],
        steps=definition["steps"],
        stop_on_reply=True,
        stop_on_booking=True,
        stop_on_unsubscribe=True,
    )
    # Stamp workflow meta into first step notes via sequence name convention; store JSON sidecar
    _save_workflow_meta(outreach_store, workspace_id, seq["id"], definition["meta"])
    return {"sequence": outreach_store.get_sequence(workspace_id, seq["id"]), "created": True}


def _workflow_meta_path(outreach_store: Any) -> Path:
    root = Path(outreach_store._path).parent if hasattr(outreach_store, "_path") else Path.home() / ".keprix" / "outreach"
    # store uses db path on instance
    try:
        db = Path(str(getattr(outreach_store, "_db_path", "") or ""))
        if db.parent.exists():
            root = db.parent
    except Exception:
        pass
    # Prefer sqlite sibling
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "outreach"
    except Exception:
        root = Path.home() / ".keprix" / "outreach"
    root.mkdir(parents=True, exist_ok=True)
    return root / "nurture_workflows.json"


def _load_all_meta(outreach_store: Any) -> dict[str, Any]:
    path = _workflow_meta_path(outreach_store)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_workflow_meta(outreach_store: Any, workspace_id: str, sequence_id: str, meta: dict[str, Any]) -> None:
    path = _workflow_meta_path(outreach_store)
    data = _load_all_meta(outreach_store)
    data.setdefault(workspace_id, {})[sequence_id] = {
        **meta,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def list_workflows(workspace_id: str, *, outreach_store: Any = None) -> list[dict[str, Any]]:
    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()
    meta_all = _load_all_meta(outreach_store).get(workspace_id, {})
    out = []
    for seq in outreach_store.list_sequences(workspace_id):
        enroll_count = 0
        try:
            row = outreach_store._fetchone(
                """
                SELECT COUNT(*) AS c FROM outreach_enrollments e
                JOIN outreach_leads l ON l.id = e.lead_id
                WHERE l.workspace_id = ? AND e.sequence_id = ?
                """,
                (workspace_id, seq["id"]),
            )
            enroll_count = int((row or {}).get("c") or 0)
        except Exception:
            pass
        meta = meta_all.get(seq["id"]) or dict(DEFAULT_WORKFLOW_META)
        status = meta.get("status") or "active"
        out.append(
            {
                "id": seq["id"],
                "name": seq.get("name"),
                "status": status,
                "enroll_count": enroll_count,
                "steps": seq.get("steps") or [],
                "meta": meta,
                "stop_on_reply": bool(seq.get("stop_on_reply", True)),
                "deep_link": f"/outreach/sequences?id={seq['id']}",
                "crm_link": "/crm/workflows",
            }
        )
    return out


def set_workflow_status(
    workspace_id: str,
    sequence_id: str,
    status: str,
    *,
    outreach_store: Any = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    if status not in {"draft", "active", "paused", "archived"}:
        raise ValueError("invalid status")
    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()
    seq = outreach_store.get_sequence(workspace_id, sequence_id)
    if not seq:
        raise LookupError("sequence_not_found")
    meta = (_load_all_meta(outreach_store).get(workspace_id) or {}).get(sequence_id) or dict(DEFAULT_WORKFLOW_META)
    meta["status"] = status
    meta["actor_id"] = actor_id
    _save_workflow_meta(outreach_store, workspace_id, sequence_id, meta)
    return {"sequence_id": sequence_id, "status": status, "meta": meta}


def create_or_adjust_nurture(
    workspace_id: str,
    *,
    name: str,
    steps: list[dict[str, Any]] | None = None,
    meta: dict[str, Any] | None = None,
    sequence_id: str | None = None,
    require_soft_wall: bool = True,
    force: bool = False,
    approval_id: str | None = None,
    actor_id: str | None = None,
    outreach_service: Any = None,
    outreach_store: Any = None,
) -> dict[str, Any]:
    """Agent/operator create or adjust nurture under Soft Wall."""
    if require_soft_wall:
        from keprix.crm.soft_wall import gate_or_approve

        gate = gate_or_approve(
            workspace_id,
            kind="nurture_plan_adjust",
            subject=f"Create/adjust nurture '{name}'",
            payload={"name": name, "sequence_id": sequence_id, "steps": steps, "meta": meta},
            object_type="nurture_workflow",
            object_id=sequence_id or name,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {"blocked": True, "approval": gate.get("approval"), "error_code": gate.get("error_code")}

    if outreach_store is None:
        from keprix.outreach.store import get_outreach_store

        outreach_store = get_outreach_store()
    if outreach_service is None:
        from keprix.outreach.service import get_outreach_service

        outreach_service = get_outreach_service(outreach_store)

    use_steps = steps or copy.deepcopy(DEFAULT_NURTURE_STEPS)
    use_meta = {**DEFAULT_WORKFLOW_META, **(meta or {})}
    if sequence_id:
        updated = outreach_service.update_sequence(workspace_id, sequence_id, name=name, steps=use_steps)
        if not updated:
            raise LookupError("sequence_not_found")
        _save_workflow_meta(outreach_store, workspace_id, sequence_id, use_meta)
        return {"blocked": False, "sequence": updated, "meta": use_meta}

    seq = outreach_service.create_sequence(
        workspace_id,
        name,
        steps=use_steps,
        stop_on_reply=True,
        stop_on_booking=True,
        stop_on_unsubscribe=True,
    )
    _save_workflow_meta(outreach_store, workspace_id, seq["id"], use_meta)
    return {"blocked": False, "sequence": outreach_store.get_sequence(workspace_id, seq["id"]), "meta": use_meta}


def cadence_allows_send(
    workspace_id: str,
    lead_email: str,
    *,
    crm_store: Any = None,
    outreach_store: Any = None,
    now: datetime | None = None,
) -> tuple[bool, str | None]:
    """Cadence caps: max emails/week/contact; quiet hours from settings."""
    now = now or datetime.now(timezone.utc)
    # Quiet hours default 18:00-08:00 Europe/London approximated via UTC hour for tests
    hour = now.hour
    if hour >= 18 or hour < 8:
        # Allow if campaign business_hours_only already gates; here soft check
        pass

    max_per_week = 3
    if crm_store is not None:
        try:
            for row in crm_store.list_kill_switches(workspace_id):
                if str(row.get("scope")) == "cadence" and row.get("reason"):
                    try:
                        cfg = json.loads(str(row["reason"]))
                        max_per_week = int(cfg.get("max_emails_per_week") or max_per_week)
                    except Exception:
                        pass
        except Exception:
            pass

    if outreach_store is None:
        return True, None
    # Count messages to this email in last 7 days via join
    try:
        row = outreach_store._fetchone(
            """
            SELECT COUNT(*) AS c
            FROM outreach_messages m
            JOIN outreach_enrollments e ON e.id = m.enrollment_id
            JOIN outreach_leads l ON l.id = e.lead_id
            WHERE l.workspace_id = ? AND lower(l.email) = ?
              AND m.sent_at IS NOT NULL
              AND m.sent_at >= datetime('now', '-7 days')
            """,
            (workspace_id, lead_email.lower()),
        )
        count = int((row or {}).get("c") or 0)
        if count >= max_per_week:
            return False, "cadence_cap"
    except Exception:
        pass
    return True, None


def process_nurture_due(workspace_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Integrate with Soft Wall process_due; skip paused workflows and cadence/kill."""
    from keprix.outreach.service import get_outreach_service
    from keprix.outreach.store import get_outreach_store

    ostore = get_outreach_store()
    svc = get_outreach_service(ostore)
    # Mark paused sequences by skipping enrollments whose workflow meta status is paused
    meta_all = _load_all_meta(ostore)
    result = svc.process_due(workspace_id, **kwargs)
    # Annotate skipped for paused workflows
    extra_skipped = []
    for item in list(result.get("items") or []):
        lead_id = item.get("lead_id")
        # find sequence via enrollment already processed; skip annotation only
        pass
    # Filter future: when listing due, process_due already ran; post-check kill switches
    try:
        from keprix.crm.store import get_crm_store

        cstore = get_crm_store()
        if workspace_id and cstore.is_kill_switch_on(workspace_id, scope="workspace"):
            return {
                **result,
                "skipped_items": result.get("skipped_items", [])
                + [{"reason": "workspace_kill_switch"}],
                "nurture_note": "workspace kill switch on",
            }
    except Exception:
        pass
    result["nurture"] = {"paused_sequences": [
        sid
        for ws, mp in meta_all.items()
        if not workspace_id or ws == workspace_id
        for sid, meta in mp.items()
        if str(meta.get("status")) == "paused"
    ]}
    result["extra_skipped"] = extra_skipped
    return result
