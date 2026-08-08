"""Engagement ingest: Soft Wall replies + Telegram -> CRM Activity/stage (prompt 443)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from keprix.crm.models import CrmStage
from keprix.crm.stages import apply_stage, suggested_stage_for_engagement, StageTransitionError

ENGAGEMENT_TYPES = frozenset(
    {
        "replied",
        "interested",
        "not_interested",
        "bounce",
        "unsubscribe",
        "booked_intent",
        "booking_intent",
        "ooo",
        "complaint",
        "question",
        "objection",
        "human_takeover",
    }
)

HIGH_CONFIDENCE = 0.8
AUTO_APPLY_TYPES = frozenset({"unsubscribe", "bounce", "interested", "not_interested", "booked_intent", "booking_intent"})
HUMAN_QUEUE_TYPES = frozenset({"complaint", "objection", "question", "human_takeover"})
LEGALISH = ("solicitor", "lawyer", "gdpr", "ico", "lawsuit", "harassment", "complaint")


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _event_id(provider: str, external_id: str | None, body: str) -> str:
    raw = f"{provider}:{external_id or ''}:{hashlib.sha256((body or '').encode()).hexdigest()[:16]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def resolve_crm_from_outreach_lead(crm_store: Any, workspace_id: str, outreach_lead: dict[str, Any]) -> dict[str, Any]:
    meta = {}
    raw_meta = outreach_lead.get("metadata_json") or outreach_lead.get("metadata")
    if isinstance(raw_meta, str):
        try:
            meta = json.loads(raw_meta)
        except json.JSONDecodeError:
            meta = {}
    elif isinstance(raw_meta, dict):
        meta = raw_meta
    notes = outreach_lead.get("notes")
    if isinstance(notes, str) and notes.strip().startswith("{"):
        try:
            parsed = json.loads(notes)
            crm = parsed.get("crm") if isinstance(parsed, dict) else None
            if isinstance(crm, dict):
                meta = {**meta, **crm}
        except json.JSONDecodeError:
            pass

    crm_lead_id = meta.get("crm_lead_id")
    crm_contact_id = meta.get("crm_contact_id")
    if crm_lead_id and crm_store.get_lead(workspace_id, str(crm_lead_id)):
        return {"entity_type": "lead", "entity_id": str(crm_lead_id), "meta": meta}
    if crm_contact_id and crm_store.get_contact(workspace_id, str(crm_contact_id)):
        return {"entity_type": "contact", "entity_id": str(crm_contact_id), "meta": meta}

    email = str(outreach_lead.get("email") or "").strip().lower()
    if email:
        for lead in crm_store.list_leads(workspace_id, limit=500):
            for item in lead.get("emails") or []:
                addr = item.get("address") if isinstance(item, dict) else item
                if str(addr or "").strip().lower() == email:
                    return {"entity_type": "lead", "entity_id": lead["id"], "meta": meta}
        for contact in crm_store.list_contacts(workspace_id, limit=500):
            for item in contact.get("emails") or []:
                addr = item.get("address") if isinstance(item, dict) else item
                if str(addr or "").strip().lower() == email:
                    return {"entity_type": "contact", "entity_id": contact["id"], "meta": meta}
    return {"entity_type": None, "entity_id": None, "meta": meta}


def _pause_pending_sends(outreach_store: Any, workspace_id: str, outreach_lead_id: str) -> list[str]:
    stopped: list[str] = []
    try:
        for enrollment in outreach_store.active_enrollments_for_lead(str(outreach_lead_id)):
            outreach_store.update_enrollment(enrollment["id"], status="paused_engagement", next_run_at=None)
            stopped.append(str(enrollment["id"]))
    except Exception:
        pass
    return stopped


def _needs_human_queue(classification: str, body: str, confidence: float) -> bool:
    text = (body or "").lower()
    if classification in HUMAN_QUEUE_TYPES:
        return True
    if confidence < HIGH_CONFIDENCE:
        return True
    if any(w in text for w in LEGALISH):
        return True
    if "negotiat" in text or "regulated" in text or "advice" in text:
        return True
    return False


def ensure_inbox_table(store: Any) -> None:
    store._conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crm_inbox_items (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            entity_type TEXT,
            entity_id TEXT,
            outreach_lead_id TEXT,
            classification TEXT,
            confidence REAL,
            subject TEXT,
            body TEXT,
            raw_metadata_json TEXT,
            classification_json TEXT,
            assignee TEXT,
            sla_due_at TEXT,
            provider_event_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(workspace_id, provider_event_id)
        )
        """
    )
    store._conn.commit()


def enqueue_inbox(
    store: Any,
    workspace_id: str,
    *,
    kind: str,
    entity_type: str | None,
    entity_id: str | None,
    classification: str | None,
    confidence: float | None,
    subject: str | None,
    body: str | None,
    raw_metadata: dict[str, Any] | None = None,
    classification_meta: dict[str, Any] | None = None,
    outreach_lead_id: str | None = None,
    provider_event_id: str | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    import uuid

    ensure_inbox_table(store)
    now = _utcnow()
    row_id = str(uuid.uuid4())
    event_id = provider_event_id or _event_id(kind, None, body or "")
    existing = store._fetchone(
        "SELECT * FROM crm_inbox_items WHERE workspace_id = ? AND provider_event_id = ?",
        (workspace_id, event_id),
    )
    if existing:
        return existing
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_inbox_items (
                id, workspace_id, kind, status, entity_type, entity_id, outreach_lead_id,
                classification, confidence, subject, body, raw_metadata_json, classification_json,
                assignee, sla_due_at, provider_event_id, created_at, updated_at
            ) VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                workspace_id,
                kind,
                entity_type,
                entity_id,
                outreach_lead_id,
                classification,
                confidence,
                subject,
                body,
                json.dumps(raw_metadata or {}, default=str),
                json.dumps(classification_meta or {}, default=str),
                assignee,
                None,
                event_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return store._fetchone("SELECT * FROM crm_inbox_items WHERE id = ?", (row_id,))  # type: ignore[return-value]


def list_inbox(store: Any, workspace_id: str, *, status: str | None = "open", kind: str | None = None) -> list[dict[str, Any]]:
    ensure_inbox_table(store)
    sql = "SELECT * FROM crm_inbox_items WHERE workspace_id = ?"
    params: list[Any] = [workspace_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY created_at DESC LIMIT 200"
    return store._fetchall(sql, tuple(params))


def update_inbox_item(store: Any, workspace_id: str, item_id: str, **fields: Any) -> dict[str, Any] | None:
    ensure_inbox_table(store)
    allowed = {"status", "assignee", "kind"}
    clean = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not clean:
        return store._fetchone(
            "SELECT * FROM crm_inbox_items WHERE id = ? AND workspace_id = ?",
            (item_id, workspace_id),
        )
    clean["updated_at"] = _utcnow()
    sets = ", ".join(f"{k} = ?" for k in clean)
    with store._lock:
        store._conn.execute(
            f"UPDATE crm_inbox_items SET {sets} WHERE id = ? AND workspace_id = ?",
            (*clean.values(), item_id, workspace_id),
        )
        store._conn.commit()
    return store._fetchone(
        "SELECT * FROM crm_inbox_items WHERE id = ? AND workspace_id = ?",
        (item_id, workspace_id),
    )


def ingest_engagement(
    *,
    workspace_id: str,
    engagement_type: str,
    body: str = "",
    subject: str = "",
    from_address: str | None = None,
    outreach_lead_id: str | None = None,
    outreach_lead: dict[str, Any] | None = None,
    confidence: float = 1.0,
    method: str = "provided",
    provider: str = "soft_wall",
    provider_event_id: str | None = None,
    raw_metadata: dict[str, Any] | None = None,
    channel: str = "email",
    auto_apply_policy: bool = True,
    crm_store: Any = None,
    outreach_store: Any = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Write Activity, optionally stage-change, suppress, pause sends."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    if outreach_store is None:
        try:
            from keprix.outreach.store import get_outreach_store

            outreach_store = get_outreach_store()
        except Exception:
            outreach_store = None

    label = str(engagement_type).strip().lower()
    if label == "booking_intent":
        label = "booked_intent"
    if label not in ENGAGEMENT_TYPES and label not in {"ooo", "question", "objection", "complaint"}:
        label = "replied"

    event_id = provider_event_id or _event_id(provider, outreach_lead_id, f"{subject}|{body}|{from_address}")

    # Dedupe via outbox idempotency
    try:
        existing = crm_store._fetchone(
            "SELECT * FROM crm_outbox WHERE workspace_id = ? AND idempotency_key = ?",
            (workspace_id, f"engagement:{event_id}"),
        )
        if existing:
            return {"ok": True, "deduped": True, "outbox": existing}
    except Exception:
        pass

    olead = outreach_lead
    if not olead and outreach_lead_id and outreach_store is not None:
        olead = outreach_store.get_lead(workspace_id, outreach_lead_id)
    if not olead and from_address and outreach_store is not None:
        olead = outreach_store.find_lead_by_email(workspace_id, from_address)

    resolved = {"entity_type": None, "entity_id": None, "meta": {}}
    if olead:
        resolved = resolve_crm_from_outreach_lead(crm_store, workspace_id, olead)
        outreach_lead_id = str(olead.get("id") or outreach_lead_id or "")
    elif from_address:
        # Direct CRM email resolution when Soft Wall lead is absent
        email = str(from_address).strip().lower()
        for lead in crm_store.list_leads(workspace_id, limit=500):
            for item in lead.get("emails") or []:
                addr = item.get("address") if isinstance(item, dict) else item
                if str(addr or "").strip().lower() == email:
                    resolved = {"entity_type": "lead", "entity_id": lead["id"], "meta": {}}
                    break
            if resolved.get("entity_id"):
                break
        if not resolved.get("entity_id"):
            for contact in crm_store.list_contacts(workspace_id, limit=500):
                for item in contact.get("emails") or []:
                    addr = item.get("address") if isinstance(item, dict) else item
                    if str(addr or "").strip().lower() == email:
                        resolved = {"entity_type": "contact", "entity_id": contact["id"], "meta": {}}
                        break
                if resolved.get("entity_id"):
                    break

    # Pause pending sends before classification effects
    paused = []
    if outreach_store is not None and outreach_lead_id and label not in {"ooo"}:
        paused = _pause_pending_sends(outreach_store, workspace_id, outreach_lead_id)

    # OOO / auto-reply: activity only, no stage promote
    is_ooo = label in {"ooo", "auto_reply"}
    needs_human = (not is_ooo) and _needs_human_queue(label, body, float(confidence))

    activity = None
    entity_type = resolved.get("entity_type")
    entity_id = resolved.get("entity_id")
    if entity_type and entity_id:
        activity = crm_store.create_activity(
            workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type=f"engagement_{label}",
            channel=channel,
            subject=subject or f"Engagement: {label}",
            body=body[:4000] if body else "",
            actor_type="system",
            actor_id=actor_id or provider,
        )

    stage_result = None
    soft_wall_suggestion = None
    suppression = None

    if label in {"unsubscribe", "bounce"} and (from_address or (olead or {}).get("email")):
        from keprix.crm.compliance import suppress_address

        addr = str(from_address or (olead or {}).get("email") or "").lower()
        suppression = suppress_address(
            crm_store,
            workspace_id,
            address=addr,
            channel="email",
            reason=label,
            source="engagement_ingest",
            permanent=label == "unsubscribe",
            subject_type=entity_type,
            subject_id=entity_id,
            actor_type="system",
            actor_id=actor_id or provider,
        )
        try:
            from keprix.crm.funnel_analytics import record_funnel_event

            record_funnel_event(
                workspace_id,
                "unsubscribes" if label == "unsubscribe" else "complaints",
            )
        except Exception:
            pass

    suggested = None if is_ooo else suggested_stage_for_engagement(label)
    high = float(confidence) >= HIGH_CONFIDENCE and label in AUTO_APPLY_TYPES and auto_apply_policy

    if suggested and entity_type and entity_id and not is_ooo:
        if high and not needs_human:
            try:
                # Engagement promotions may skip contacted when reply arrives on enrolled.
                stage_result = apply_stage(
                    crm_store,
                    workspace_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    to_stage=suggested,
                    soft_wall_approved=suggested
                    not in {CrmStage.CUSTOMER, CrmStage.PAYING},
                    human_confirmed=False,
                    force=suggested
                    in {CrmStage.SUPPRESSED, CrmStage.BOUNCED, CrmStage.LOST, CrmStage.DO_NOT_CONTACT},
                    actor_type="system",
                    actor_id=actor_id or provider,
                    reason=f"engagement:{label}",
                )
            except StageTransitionError as exc:
                soft_wall_suggestion = {
                    "from_error": exc.code,
                    "suggested_stage": suggested,
                    "needs_soft_wall": True,
                }
                needs_human = True
        else:
            soft_wall_suggestion = {
                "suggested_stage": suggested,
                "confidence": confidence,
                "needs_soft_wall": True,
                "reason": "low_confidence_or_policy",
            }
            needs_human = True

    inbox_item = None
    if needs_human or soft_wall_suggestion or label in HUMAN_QUEUE_TYPES:
        kind = "complaint" if label == "complaint" else ("stage_suggestion" if soft_wall_suggestion else "reply")
        if label == "human_takeover":
            kind = "takeover"
        inbox_item = enqueue_inbox(
            crm_store,
            workspace_id,
            kind=kind,
            entity_type=entity_type,
            entity_id=entity_id,
            classification=label,
            confidence=float(confidence),
            subject=subject,
            body=body,
            raw_metadata={
                **(raw_metadata or {}),
                "provider": provider,
                "from_address": from_address,
                "immutable": True,
            },
            classification_meta={
                "classification": label,
                "confidence": confidence,
                "method": method,
                "model_version": method,
                "mutable": True,
            },
            outreach_lead_id=outreach_lead_id,
            provider_event_id=event_id,
        )

    try:
        crm_store.enqueue_outbox(
            workspace_id,
            kind="engagement_ingest",
            idempotency_key=f"engagement:{event_id}",
            payload={
                "engagement_type": label,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "activity_id": (activity or {}).get("id"),
            },
            entity_type=entity_type,
            entity_id=entity_id,
            status="sent",
        )
    except Exception:
        pass

    try:
        from keprix.crm.funnel_analytics import record_funnel_event

        if label in {"replied", "interested", "question", "objection"}:
            record_funnel_event(workspace_id, "replied")
    except Exception:
        pass

    return {
        "ok": True,
        "engagement_type": label,
        "activity": activity,
        "stage": stage_result,
        "soft_wall_suggestion": soft_wall_suggestion,
        "suppression": suppression,
        "paused_enrollments": paused,
        "inbox_item": inbox_item,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "provider_event_id": event_id,
        "confidence": confidence,
        "method": method,
    }


def hook_soft_wall_reply(
    workspace_id: str,
    soft_wall_result: dict[str, Any],
    *,
    crm_store: Any = None,
) -> dict[str, Any]:
    """Bridge OutreachService.classify_and_apply_reply result into CRM."""
    reply = soft_wall_result.get("reply") or {}
    classification = soft_wall_result.get("classification") or {}
    lead = soft_wall_result.get("lead") or {}
    label = str(classification.get("classification") or reply.get("classification") or "replied")
    return ingest_engagement(
        workspace_id=workspace_id,
        engagement_type=label,
        body=str(reply.get("body") or ""),
        subject=str(reply.get("subject") or ""),
        from_address=str(reply.get("from_address") or lead.get("email") or ""),
        outreach_lead_id=str(lead.get("id") or ""),
        outreach_lead=lead,
        confidence=float(classification.get("confidence") or 0.5),
        method=str(classification.get("method") or "soft_wall"),
        provider="soft_wall_email",
        provider_event_id=str(reply.get("id") or "") or None,
        raw_metadata={"reply_id": reply.get("id"), "stopped": soft_wall_result.get("stopped_enrollments")},
        channel="email",
        crm_store=crm_store,
    )


def ingest_telegram_message(
    *,
    workspace_id: str,
    text: str,
    telegram_handle: str | None = None,
    lead_id: str | None = None,
    contact_id: str | None = None,
    crm_store: Any = None,
) -> dict[str, Any]:
    """Best-effort Telegram operator chat tagged to a lead."""
    if crm_store is None:
        from keprix.crm.store import get_crm_store

        crm_store = get_crm_store()
    entity_type = "lead" if lead_id else ("contact" if contact_id else None)
    entity_id = lead_id or contact_id
    if not entity_id and telegram_handle:
        handle = telegram_handle.lstrip("@").lower()
        for lead in crm_store.list_leads(workspace_id, limit=500):
            tags = [str(t).lower() for t in (lead.get("tags") or [])]
            tids = [str(t).lower() for t in (lead.get("telegram_ids") or [])]
            if handle in tags or handle in tids or f"tg:{handle}" in tags:
                entity_type, entity_id = "lead", lead["id"]
                break
    if not entity_id:
        return {"ok": False, "reason": "lead_not_resolved"}
    return ingest_engagement(
        workspace_id=workspace_id,
        engagement_type="replied",
        body=text,
        subject="Telegram message",
        channel="telegram",
        provider="telegram",
        provider_event_id=_event_id("telegram", entity_id, text),
        raw_metadata={"telegram_handle": telegram_handle},
        crm_store=crm_store,
        confidence=0.7,
        method="telegram_tag",
    )
