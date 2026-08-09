"""Durable CRM funnel trigger→action orchestrator (Prompt 627).

Persists runs in ``crm_funnel_runs`` / ``crm_funnel_run_steps``. Soft Wall gates
high-risk actions; suppression always wins. Idempotent on
(workspace_id, trigger, subject_id, action, idempotency_key).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.crm.lifecycle import resolve_stage_alias
from keprix.crm.models import CrmStage
from keprix.crm.soft_wall import gate_or_approve

TRIGGERS = frozenset(
    {
        "lead_created",
        "enriched",
        "list_joined",
        "stage_changed",
        "campaign_enrolled",
        "provider_event",
        "reply_received",
        "booking_created",
        "no_response_after_delay",
        "task_overdue",
        "converted",
        "suppressed",
    }
)

ACTIONS = frozenset(
    {
        "assign_agent",
        "add_tag",
        "add_to_list",
        "update_stage",
        "create_task",
        "request_approval",
        "enrol_sequence",
        "pause_sequence",
        "draft_reply",
        "notify_user",
        "schedule_follow_up",
        "enrich",
        "create_booking_link",
    }
)

HIGH_RISK_ACTIONS = frozenset(
    {
        "update_stage",
        "enrol_sequence",
        "request_approval",
        "draft_reply",
        "create_booking_link",
        "enrich",
        "pause_sequence",
    }
)

FUNNEL_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS crm_funnel_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    trigger_name TEXT NOT NULL,
    subject_type TEXT NOT NULL DEFAULT 'lead',
    subject_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    actor_type TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, trigger_name, subject_id, action_name, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_crm_funnel_runs_ws ON crm_funnel_runs(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS ix_crm_funnel_runs_subject ON crm_funnel_runs(workspace_id, subject_id);

CREATE TABLE IF NOT EXISTS crm_funnel_run_steps (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 0,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_funnel_steps_run ON crm_funnel_run_steps(workspace_id, run_id);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_funnel_run_tables(conn) -> None:
    conn.executescript(FUNNEL_RUNS_DDL)
    conn.commit()


def _ensure(store: Any) -> None:
    ensure_funnel_run_tables(store._conn)


def _dumps(obj: Any) -> str:
    return json.dumps(obj if obj is not None else {}, default=str)


def _loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _primary_email(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    for item in row.get("emails") or []:
        if isinstance(item, dict):
            addr = str(item.get("address") or "").strip()
            if addr:
                return addr
        elif str(item or "").strip():
            return str(item).strip()
    return None


def _subject_row(store: Any, workspace_id: str, subject_type: str, subject_id: str) -> dict[str, Any] | None:
    getters = {
        "lead": store.get_lead,
        "contact": store.get_contact,
        "account": store.get_account,
        "deal": store.get_deal,
    }
    fn = getters.get(subject_type or "lead")
    if not fn:
        return None
    return fn(workspace_id, subject_id)


def _is_suppressed(store: Any, workspace_id: str, subject_type: str, subject_id: str) -> tuple[bool, str | None]:
    row = _subject_row(store, workspace_id, subject_type, subject_id)
    if not row:
        return False, None
    stage = str(row.get("stage") or "")
    if stage in {CrmStage.SUPPRESSED, CrmStage.DO_NOT_CONTACT, CrmStage.BOUNCED}:
        return True, stage
    email = _primary_email(row)
    if email and store.is_suppressed(workspace_id, channel="email", address=email):
        return True, email
    return False, None


def _find_run(
    store: Any,
    workspace_id: str,
    *,
    trigger: str,
    subject_id: str,
    action: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    row = store._fetchone(
        """
        SELECT * FROM crm_funnel_runs
        WHERE workspace_id = ? AND trigger_name = ? AND subject_id = ?
          AND action_name = ? AND idempotency_key = ?
        """,
        (workspace_id, trigger, subject_id, action, idempotency_key),
    )
    if not row:
        return None
    row["payload"] = _loads(row.pop("payload_json", None) or row.get("payload"))
    row["result"] = _loads(row.pop("result_json", None) or row.get("result"))
    return row


def _insert_run(
    store: Any,
    workspace_id: str,
    *,
    trigger: str,
    subject_type: str,
    subject_id: str,
    action: str,
    idempotency_key: str,
    payload: dict[str, Any],
    actor_type: str | None,
    actor_id: str | None,
) -> dict[str, Any]:
    now = _utcnow()
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_funnel_runs (
                id, workspace_id, trigger_name, subject_type, subject_id, action_name,
                idempotency_key, status, payload_json, result_json, actor_type, actor_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, '{}', ?, ?, ?, ?)
            """,
            (
                rid,
                workspace_id,
                trigger,
                subject_type,
                subject_id,
                action,
                idempotency_key,
                _dumps(payload),
                actor_type,
                actor_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return _find_run(store, workspace_id, trigger=trigger, subject_id=subject_id, action=action, idempotency_key=idempotency_key) or {
        "id": rid,
        "status": "running",
    }


def _add_step(
    store: Any,
    workspace_id: str,
    run_id: str,
    *,
    step_order: int,
    step_name: str,
    status: str,
    detail: dict[str, Any] | None = None,
) -> None:
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_funnel_run_steps (
                id, workspace_id, run_id, step_order, step_name, status, detail_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), workspace_id, run_id, step_order, step_name, status, _dumps(detail or {}), now, now),
        )
        store._conn.commit()


def _finish_run(
    store: Any,
    workspace_id: str,
    run_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            """
            UPDATE crm_funnel_runs
            SET status = ?, result_json = ?, error = ?, updated_at = ?
            WHERE id = ? AND workspace_id = ?
            """,
            (status, _dumps(result or {}), error, now, run_id, workspace_id),
        )
        store._conn.commit()
    row = store._fetchone(
        "SELECT * FROM crm_funnel_runs WHERE id = ? AND workspace_id = ?",
        (run_id, workspace_id),
    )
    if row:
        row["payload"] = _loads(row.pop("payload_json", None))
        row["result"] = _loads(row.pop("result_json", None))
    return row or {"id": run_id, "status": status, "result": result or {}}


def _execute_action(
    store: Any,
    workspace_id: str,
    *,
    action: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any],
    actor_type: str | None,
    actor_id: str | None,
) -> dict[str, Any]:
    row = _subject_row(store, workspace_id, subject_type, subject_id)

    if action == "assign_agent":
        agent = payload.get("agent_id") or payload.get("assigned_agent")
        if not agent or not row:
            return {"ok": False, "error_code": "missing_agent_or_subject"}
        updater = getattr(store, f"update_{subject_type}", None)
        if not updater:
            return {"ok": False, "error_code": "unsupported_subject"}
        updated = updater(workspace_id, subject_id, assigned_agent=str(agent), actor_type=actor_type, actor_id=actor_id)
        return {"ok": True, "entity": updated}

    if action == "add_tag":
        tag = str(payload.get("tag") or "").strip()
        if not tag or not row:
            return {"ok": False, "error_code": "missing_tag_or_subject"}
        tags = list(row.get("tags") or [])
        if tag not in tags:
            tags.append(tag)
        updater = getattr(store, f"update_{subject_type}")
        updated = updater(workspace_id, subject_id, tags=tags, actor_type=actor_type, actor_id=actor_id)
        return {"ok": True, "entity": updated, "tags": tags}

    if action == "add_to_list":
        list_id = payload.get("list_id")
        if not list_id:
            name = payload.get("list_name") or f"Funnel {workspace_id}"
            lst = store.create_list(workspace_id, str(name), source="funnel_orchestrator", actor_type=actor_type, actor_id=actor_id)
            list_id = lst["id"]
        member = store.add_list_member(
            workspace_id,
            str(list_id),
            member_type=subject_type,
            member_id=subject_id,
            stage=(row or {}).get("stage"),
        )
        return {"ok": True, "list_id": list_id, "membership": member}

    if action == "update_stage":
        to_stage = resolve_stage_alias(payload.get("stage") or payload.get("to_stage"))
        if not to_stage:
            return {"ok": False, "error_code": "missing_stage"}
        from keprix.crm.stages import apply_stage

        result = apply_stage(
            store,
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            to_stage=to_stage,
            soft_wall_approved=bool(payload.get("soft_wall_approved")),
            human_confirmed=bool(payload.get("human_confirmed")),
            force=bool(payload.get("force")),
            actor_type=actor_type,
            actor_id=actor_id,
            reason=payload.get("reason") or "funnel_orchestrator",
        )
        return {"ok": True, "stage": result}

    if action == "create_task":
        activity = store.create_activity(
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            activity_type="task",
            subject=str(payload.get("subject") or "Funnel task"),
            body=str(payload.get("body") or ""),
            metadata={"due_at": payload.get("due_at"), "source": "funnel_orchestrator"},
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return {"ok": True, "activity": activity}

    if action == "request_approval":
        gate = gate_or_approve(
            workspace_id,
            kind=str(payload.get("kind") or "funnel_request_approval"),
            subject=str(payload.get("subject") or f"Funnel approval for {subject_id}"),
            payload={"subject_type": subject_type, "subject_id": subject_id, **payload},
            object_type=subject_type,
            object_id=subject_id,
            actor_id=actor_id,
            force=False,
        )
        return {"ok": True, "blocked": gate.get("blocked", True), "approval": gate.get("approval"), "gate": gate}

    if action == "enrol_sequence":
        sequence_id = payload.get("sequence_id")
        if not sequence_id:
            return {"ok": False, "error_code": "missing_sequence_id"}
        from keprix.outreach.service import get_outreach_service
        from keprix.outreach.store import get_outreach_store

        ostore = get_outreach_store()
        svc = get_outreach_service(ostore)
        email = _primary_email(row) or payload.get("email")
        if not email:
            return {"ok": False, "error_code": "missing_email"}
        meta = {
            "crm_lead_id": subject_id if subject_type == "lead" else None,
            "crm_contact_id": subject_id if subject_type == "contact" else None,
        }
        created = svc.add_leads(
            workspace_id,
            leads=[
                {
                    "email": str(email),
                    "company": (row or {}).get("company_name") or (row or {}).get("name"),
                    "notes": json.dumps({"crm": meta}),
                }
            ],
            campaign_id=payload.get("campaign_id"),
        )
        leads_list = created.get("leads") if isinstance(created, dict) else []
        outreach_lead = (leads_list or [None])[0]
        lead_id = (outreach_lead or {}).get("id")
        if not lead_id:
            for cand in ostore.list_leads(workspace_id, limit=500):
                if str(cand.get("email") or "").lower() == str(email).lower():
                    lead_id = cand["id"]
                    outreach_lead = cand
                    break
        if not lead_id:
            return {"ok": False, "error_code": "outreach_lead_create_failed", "created": created}
        enrollment = svc.enroll_lead(workspace_id, str(lead_id), str(sequence_id))
        return {"ok": True, "outreach_lead": outreach_lead, "enrollment": enrollment}

    if action == "pause_sequence":
        enrollment_id = payload.get("enrollment_id")
        from keprix.outreach.store import get_outreach_store

        ostore = get_outreach_store()
        if enrollment_id:
            updated = ostore.update_enrollment(str(enrollment_id), status="paused", next_run_at=None)
            return {"ok": True, "enrollment": updated}
        return {"ok": False, "error_code": "missing_enrollment_id"}

    if action == "draft_reply":
        gate = gate_or_approve(
            workspace_id,
            kind="funnel_draft_reply",
            subject=f"Draft reply for {subject_id}",
            payload={"subject_type": subject_type, "subject_id": subject_id, "body": payload.get("body")},
            object_type=subject_type,
            object_id=subject_id,
            actor_id=actor_id,
        )
        activity = store.create_activity(
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            activity_type="draft_reply",
            subject=str(payload.get("subject") or "Draft reply"),
            body=str(payload.get("body") or ""),
            metadata={"approval": (gate.get("approval") or {}).get("id"), "soft_wall": True},
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return {"ok": True, "blocked": gate.get("blocked", True), "approval": gate.get("approval"), "activity": activity}

    if action == "notify_user":
        activity = store.create_activity(
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            activity_type="notify",
            subject=str(payload.get("subject") or "Funnel notification"),
            body=str(payload.get("body") or payload.get("message") or ""),
            metadata={"channel": payload.get("channel") or "in_app", "user_id": payload.get("user_id")},
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return {"ok": True, "activity": activity}

    if action == "schedule_follow_up":
        activity = store.create_activity(
            workspace_id,
            entity_type=subject_type,
            entity_id=subject_id,
            activity_type="follow_up",
            subject=str(payload.get("subject") or "Follow up"),
            body=str(payload.get("body") or ""),
            metadata={"due_at": payload.get("due_at") or payload.get("at")},
            actor_type=actor_type,
            actor_id=actor_id,
        )
        if hasattr(store, "update_lead") and subject_type == "lead" and payload.get("due_at"):
            store.update_lead(workspace_id, subject_id, next_action_at=str(payload.get("due_at")), actor_type=actor_type, actor_id=actor_id)
        return {"ok": True, "activity": activity}

    if action == "enrich":
        gate = gate_or_approve(
            workspace_id,
            kind="apply_enrichment",
            subject=f"Enrich {subject_type} {subject_id}",
            payload={"subject_type": subject_type, "subject_id": subject_id},
            object_type=subject_type,
            object_id=subject_id,
            actor_id=actor_id,
            force=bool(payload.get("force")),
            approval_id=payload.get("approval_id"),
        )
        if gate.get("blocked"):
            return {"ok": True, "blocked": True, "approval": gate.get("approval"), "error_code": gate.get("error_code")}
        if subject_type == "lead" and row:
            from keprix.crm.stages import apply_stage

            apply_stage(
                store,
                workspace_id,
                entity_type="lead",
                entity_id=subject_id,
                to_stage=CrmStage.ENRICHED,
                soft_wall_approved=True,
                actor_type=actor_type,
                actor_id=actor_id,
                reason="funnel_enrich",
            )
        return {"ok": True, "enriched": True}

    if action == "create_booking_link":
        from keprix.crm.booking import offer_booking

        result = offer_booking(
            workspace_id,
            contact_id=subject_id if subject_type == "contact" else None,
            lead_id=subject_id if subject_type == "lead" else None,
            host_user_id=payload.get("host_user_id") or actor_id,
            event_type_id=payload.get("event_type_id"),
            campaign_id=payload.get("campaign_id"),
            crm_store=store,
        )
        return {"ok": True, "booking": result}

    return {"ok": False, "error_code": "unknown_action"}


def orchestrate(
    workspace_id: str,
    *,
    trigger: str,
    action: str,
    subject_id: str,
    subject_type: str = "lead",
    idempotency_key: str | None = None,
    payload: dict[str, Any] | None = None,
    crm_store: Any = None,
    actor_type: str | None = "system",
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
    require_soft_wall: bool = True,
) -> dict[str, Any]:
    """Run one trigger→action with durable idempotency, Soft Wall, and suppression."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    _ensure(crm_store)

    trigger = str(trigger or "").strip()
    action = str(action or "").strip()
    if trigger not in TRIGGERS:
        return {"ok": False, "error_code": "invalid_trigger", "allowed": sorted(TRIGGERS)}
    if action not in ACTIONS:
        return {"ok": False, "error_code": "invalid_action", "allowed": sorted(ACTIONS)}

    ws = crm_store._require_workspace(workspace_id)
    payload = dict(payload or {})
    key = str(idempotency_key or f"{trigger}:{action}:{subject_id}").strip()

    existing = _find_run(crm_store, ws, trigger=trigger, subject_id=subject_id, action=action, idempotency_key=key)
    if existing and existing.get("status") in {"completed", "blocked", "suppressed"}:
        return {
            "ok": True,
            "idempotent": True,
            "run": existing,
            "status": existing.get("status"),
            "result": existing.get("result") or {},
        }

    suppressed, reason = _is_suppressed(crm_store, ws, subject_type, subject_id)
    if suppressed and action not in {"notify_user", "create_task", "add_tag"}:
        run = existing or _insert_run(
            crm_store,
            ws,
            trigger=trigger,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            idempotency_key=key,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        finished = _finish_run(
            crm_store,
            ws,
            run["id"],
            status="suppressed",
            result={"error_code": "suppressed", "reason": reason},
            error="suppressed",
        )
        _add_step(crm_store, ws, run["id"], step_order=0, step_name="suppression_gate", status="blocked", detail={"reason": reason})
        return {"ok": False, "error_code": "suppressed", "run": finished, "reason": reason}

    soft_wall_payload = None
    if require_soft_wall and action in HIGH_RISK_ACTIONS and not force:
        # Paying stage updates always Soft Wall
        to_stage = resolve_stage_alias(payload.get("stage") or payload.get("to_stage"))
        kind = "funnel_orchestrate"
        if action == "update_stage" and to_stage in {CrmStage.CUSTOMER, CrmStage.PAYING}:
            kind = "stage_customer_paying"
        elif action == "enrol_sequence":
            kind = "crm.list.enroll"
        elif action == "enrich":
            kind = "apply_enrichment"
        gate = gate_or_approve(
            ws,
            kind=kind,
            subject=f"Funnel {action} on {subject_type}:{subject_id}",
            payload={"trigger": trigger, "action": action, "subject_id": subject_id, "payload": payload},
            object_type=subject_type,
            object_id=subject_id,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            run = existing or _insert_run(
                crm_store,
                ws,
                trigger=trigger,
                subject_type=subject_type,
                subject_id=subject_id,
                action=action,
                idempotency_key=key,
                payload=payload,
                actor_type=actor_type,
                actor_id=actor_id,
            )
            finished = _finish_run(
                crm_store,
                ws,
                run["id"],
                status="blocked",
                result={"error_code": gate.get("error_code"), "approval": gate.get("approval")},
                error=gate.get("error_code"),
            )
            _add_step(
                crm_store,
                ws,
                run["id"],
                step_order=0,
                step_name="soft_wall",
                status="blocked",
                detail={"approval_id": (gate.get("approval") or {}).get("id")},
            )
            return {
                "ok": False,
                "blocked": True,
                "error_code": gate.get("error_code") or "soft_wall_required",
                "approval": gate.get("approval"),
                "run": finished,
            }
        soft_wall_payload = gate
        payload["soft_wall_approved"] = True

    run = existing or _insert_run(
        crm_store,
        ws,
        trigger=trigger,
        subject_type=subject_type,
        subject_id=subject_id,
        action=action,
        idempotency_key=key,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    _add_step(crm_store, ws, run["id"], step_order=1, step_name="execute", status="running", detail={"action": action})

    try:
        result = _execute_action(
            crm_store,
            ws,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        status = "completed" if result.get("ok") else "failed"
        if result.get("blocked"):
            status = "blocked"
        finished = _finish_run(crm_store, ws, run["id"], status=status, result=result, error=result.get("error_code"))
        _add_step(crm_store, ws, run["id"], step_order=2, step_name="done", status=status, detail=result)
        return {
            "ok": bool(result.get("ok")) and status == "completed",
            "run": finished,
            "result": result,
            "soft_wall": soft_wall_payload,
            "idempotent": False,
        }
    except Exception as exc:
        finished = _finish_run(crm_store, ws, run["id"], status="failed", result={}, error=str(exc))
        _add_step(crm_store, ws, run["id"], step_order=2, step_name="error", status="failed", detail={"error": str(exc)})
        return {"ok": False, "error_code": "orchestrate_failed", "error": str(exc), "run": finished}


def list_funnel_runs(workspace_id: str, *, crm_store: Any = None, limit: int = 100) -> list[dict[str, Any]]:
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    _ensure(crm_store)
    ws = crm_store._require_workspace(workspace_id)
    rows = crm_store._fetchall(
        """
        SELECT * FROM crm_funnel_runs
        WHERE workspace_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (ws, int(limit)),
    )
    out = []
    for row in rows:
        row["payload"] = _loads(row.pop("payload_json", None))
        row["result"] = _loads(row.pop("result_json", None))
        out.append(row)
    return out
