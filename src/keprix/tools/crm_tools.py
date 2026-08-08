"""Keprix agent tools: CRM read/write + ask-data (prompt 435)."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry

from keprix.crm.ask import ask_crm, format_telegram_reply
from keprix.crm.soft_wall import PAYING_STAGES, gate_or_approve
from keprix.crm.store import ConflictError, get_crm_store

TOOLSET = "crm"

_MASS_THRESHOLD = 2


def check_crm_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _store():
    return get_crm_store()


def _require_workspace(args: dict[str, Any]) -> str | None:
    ws = str(args.get("workspace_id") or "").strip()
    return ws or None


def _actor(args: dict[str, Any]) -> tuple[str, str]:
    return "agent", str(args.get("actor_id") or args.get("user_id") or "agent")


def _blocked(gate: dict[str, Any]) -> str:
    return _ok(
        {
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
        }
    )


def _gate(
    workspace_id: str,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_type: str | None = None,
    object_id: str | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any] | None:
    """Return blocked response dict when Soft Wall holds, else None."""
    gate = gate_or_approve(
        workspace_id,
        kind=kind,
        subject=subject,
        payload=payload,
        object_type=object_type,
        object_id=object_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
        }
    return None


def _filter_like_search(
    rows: list[dict[str, Any]],
    *,
    q: str | None = None,
    stage: str | None = None,
    source: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    from keprix.crm.ask import filter_rows

    return filter_rows(
        rows,
        q=q,
        stage=stage,
        source=source,
        domain_pack=domain_pack,
        tag=tag,
    )


def _get_entity(store: Any, workspace_id: str, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    et = str(entity_type or "").strip().lower()
    if et in {"lead", "leads"}:
        return store.get_lead(workspace_id, entity_id)
    if et in {"contact", "contacts"}:
        return store.get_contact(workspace_id, entity_id)
    if et in {"account", "accounts"}:
        return store.get_account(workspace_id, entity_id)
    if et in {"deal", "deals"}:
        return store.get_deal(workspace_id, entity_id)
    if et in {"list", "lists"}:
        return store.get_list(workspace_id, entity_id)
    return None


def _update_stage(
    store: Any,
    workspace_id: str,
    entity_type: str,
    entity_id: str,
    stage: str,
    *,
    expected_version: int | None = None,
) -> dict[str, Any] | None:
    et = str(entity_type or "").strip().lower()
    if et in {"lead", "leads"}:
        return store.update_lead(workspace_id, entity_id, stage=stage, expected_version=expected_version)
    if et in {"contact", "contacts"}:
        return store.update_contact(workspace_id, entity_id, stage=stage, expected_version=expected_version)
    if et in {"account", "accounts"}:
        return store.update_account(workspace_id, entity_id, stage=stage, expected_version=expected_version)
    if et in {"deal", "deals"}:
        return store.update_deal(workspace_id, entity_id, stage=stage, expected_version=expected_version)
    return None


def _soft_delete_entity(
    store: Any, workspace_id: str, entity_type: str, entity_id: str
) -> dict[str, Any] | None:
    et = str(entity_type or "").strip().lower()
    if et in {"lead", "leads"}:
        return store.delete_lead(workspace_id, entity_id)
    if et in {"contact", "contacts"}:
        return store.delete_contact(workspace_id, entity_id)
    if et in {"account", "accounts"}:
        return store.delete_account(workspace_id, entity_id)
    if et in {"deal", "deals"}:
        return store.delete_deal(workspace_id, entity_id)
    if et in {"list", "lists"}:
        return store.delete_list(workspace_id, entity_id)
    return None


def _maybe_memory_bridge(
    workspace_id: str,
    *,
    note: str,
    crm_ids: dict[str, Any],
) -> dict[str, Any] | None:
    """Optional high-signal note to workspace memory with CRM ids in metadata."""
    text = str(note or "").strip()
    if not text:
        return None
    try:
        from keprix.memory.manager import MemoryManager

        mm = MemoryManager()
        meta = {"workspace_id": workspace_id, "crm": crm_ids, "source": "crm_tools"}
        fact = f"[crm {workspace_id}] {text} | ids={json.dumps(crm_ids, default=str)}"
        if hasattr(mm, "remember"):
            mm.remember(fact)
        return {"written": True, "metadata": meta}
    except Exception as exc:
        return {"written": False, "error": str(exc)}


# ── Handlers ──────────────────────────────────────────────────


def crm_search(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    entity = str(args.get("entity") or args.get("entity_type") or "leads").strip().lower()
    if entity in {"lead", "leads"}:
        entity = "leads"
    elif entity in {"contact", "contacts"}:
        entity = "contacts"
    elif entity in {"account", "accounts"}:
        entity = "accounts"
    elif entity in {"deal", "deals"}:
        entity = "deals"
    else:
        entity = "leads"
    store = _store()
    if entity == "leads":
        rows = store.list_leads(workspace_id, limit=5000)
    elif entity == "contacts":
        rows = store.list_contacts(workspace_id, limit=5000)
    elif entity == "accounts":
        rows = store.list_accounts(workspace_id, limit=5000)
    else:
        rows = store.list_deals(workspace_id, limit=5000)
    filtered = _filter_like_search(
        rows,
        q=args.get("q") or args.get("query"),
        stage=args.get("stage"),
        source=args.get("source"),
        domain_pack=args.get("domain_pack"),
        tag=args.get("tag"),
    )
    limit = max(1, min(int(args.get("limit") or 50), 200))
    offset = max(0, int(args.get("offset") or 0))
    page = filtered[offset : offset + limit]
    return _ok(
        {
            "workspace_id": workspace_id,
            "entity": entity,
            "count": len(filtered),
            "limit": limit,
            "offset": offset,
            "items": page,
            "citations": [{"id": r["id"], "entity_type": entity[:-1]} for r in page if r.get("id")],
            "telegram_reply": format_telegram_reply(
                f"{len(filtered)} {entity} found; showing {len(page)}."
            ),
        }
    )


def crm_get(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    entity_type = str(args.get("entity_type") or args.get("entity") or "lead").strip()
    entity_id = str(args.get("entity_id") or args.get("id") or "").strip()
    if not entity_id:
        return _err("entity_id is required")
    row = _get_entity(_store(), workspace_id, entity_type, entity_id)
    if not row:
        return _err("not_found", error_code="crm_not_found", workspace_id=workspace_id)
    # Fail closed: store already scopes by workspace; double-check.
    if str(row.get("workspace_id") or "") != workspace_id:
        return _err("cross_workspace_denied", error_code="cross_workspace_denied")
    key = entity_type[:-1] if entity_type.endswith("s") else entity_type
    return _ok({"workspace_id": workspace_id, key: row, "citations": [{"id": row["id"], "entity_type": key}]})


def crm_upsert_lead(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    store = _store()
    actor_type, actor_id = _actor(args)
    force = bool(args.get("force"))
    approval_id = args.get("approval_id")

    if args.get("delete") is True or str(args.get("action") or "").lower() == "delete":
        lead_id = str(args.get("lead_id") or args.get("id") or "").strip()
        if not lead_id:
            return _err("lead_id is required for delete")
        existing = store.get_lead(workspace_id, lead_id)
        if not existing:
            return _err("not_found", error_code="lead_not_found")
        blocked = _gate(
            workspace_id,
            kind="delete",
            subject=f"Delete lead {lead_id}",
            payload={"lead_id": lead_id},
            object_type="lead",
            object_id=lead_id,
            actor_id=actor_id,
            force=force,
            approval_id=str(approval_id) if approval_id else None,
        )
        if blocked:
            return _ok(blocked)
        deleted = store.delete_lead(workspace_id, lead_id)
        return _ok({"ok": True, "deleted": True, "lead": deleted})

    fields = {
        k: v
        for k, v in args.items()
        if k
        not in {
            "workspace_id",
            "delete",
            "action",
            "force",
            "approval_id",
            "actor_id",
            "user_id",
            "write_memory",
        }
        and v is not None
    }
    fields["actor_type"] = actor_type
    fields["actor_id"] = actor_id
    try:
        lead = store.upsert_lead(workspace_id, **fields)
    except (ValueError, ConflictError) as exc:
        return _err(str(exc))
    out: dict[str, Any] = {"lead": lead, "workspace_id": workspace_id}
    if args.get("write_memory"):
        out["memory"] = _maybe_memory_bridge(
            workspace_id,
            note=str(args.get("memory_note") or lead.get("name") or "lead upsert"),
            crm_ids={"lead_id": lead.get("id")},
        )
    return _ok(out)


def crm_upsert_contact(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    store = _store()
    actor_type, actor_id = _actor(args)
    force = bool(args.get("force"))
    approval_id = args.get("approval_id")

    if args.get("delete") is True or str(args.get("action") or "").lower() == "delete":
        contact_id = str(args.get("contact_id") or args.get("id") or "").strip()
        if not contact_id:
            return _err("contact_id is required for delete")
        existing = store.get_contact(workspace_id, contact_id)
        if not existing:
            return _err("not_found", error_code="contact_not_found")
        blocked = _gate(
            workspace_id,
            kind="delete",
            subject=f"Delete contact {contact_id}",
            payload={"contact_id": contact_id},
            object_type="contact",
            object_id=contact_id,
            actor_id=actor_id,
            force=force,
            approval_id=str(approval_id) if approval_id else None,
        )
        if blocked:
            return _ok(blocked)
        deleted = store.delete_contact(workspace_id, contact_id)
        return _ok({"ok": True, "deleted": True, "contact": deleted})

    fields = {
        k: v
        for k, v in args.items()
        if k
        not in {
            "workspace_id",
            "delete",
            "action",
            "force",
            "approval_id",
            "actor_id",
            "user_id",
            "write_memory",
        }
        and v is not None
    }
    fields["actor_type"] = actor_type
    fields["actor_id"] = actor_id
    try:
        contact = store.upsert_contact(workspace_id, **fields)
    except (ValueError, ConflictError) as exc:
        return _err(str(exc))
    return _ok({"contact": contact, "workspace_id": workspace_id})


def crm_add_activity(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    entity_type = str(args.get("entity_type") or "").strip()
    entity_id = str(args.get("entity_id") or "").strip()
    activity_type = str(args.get("activity_type") or args.get("type") or "note").strip()
    if not entity_type or not entity_id:
        return _err("entity_type and entity_id are required")
    store = _store()
    # Fail closed: entity must exist in this workspace.
    if not _get_entity(store, workspace_id, entity_type, entity_id):
        return _err("not_found", error_code="crm_not_found")
    actor_type, actor_id = _actor(args)
    activity = store.create_activity(
        workspace_id,
        entity_type=entity_type if not entity_type.endswith("s") else entity_type[:-1],
        entity_id=entity_id,
        activity_type=activity_type,
        channel=args.get("channel"),
        subject=args.get("subject"),
        body=args.get("body"),
        metadata=args.get("metadata") or {},
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=args.get("occurred_at"),
    )
    out: dict[str, Any] = {"activity": activity, "workspace_id": workspace_id}
    if args.get("write_memory") and args.get("body"):
        out["memory"] = _maybe_memory_bridge(
            workspace_id,
            note=str(args.get("body")),
            crm_ids={"entity_type": entity_type, "entity_id": entity_id, "activity_id": activity.get("id")},
        )
    out["telegram_reply"] = format_telegram_reply(
        f"Logged {activity_type} on {entity_type} {entity_id}."
    )
    return _ok(out)


def crm_list_create(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    name = str(args.get("name") or "").strip()
    if not name:
        return _err("name is required")
    row = _store().create_list(
        workspace_id,
        name,
        description=args.get("description"),
        domain_pack=args.get("domain_pack"),
        source=args.get("source"),
        tags=args.get("tags"),
        assigned_agent=args.get("assigned_agent"),
    )
    return _ok({"list": row, "workspace_id": workspace_id})


def crm_list_add_members(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    list_id = str(args.get("list_id") or "").strip()
    if not list_id:
        return _err("list_id is required")
    store = _store()
    lst = store.get_list(workspace_id, list_id)
    if not lst:
        return _err("not_found", error_code="list_not_found")

    members = args.get("members")
    if not members:
        # Single-member shorthand.
        member_type = str(args.get("member_type") or "lead").strip()
        member_id = str(args.get("member_id") or "").strip()
        if not member_id:
            return _err("members or member_id is required")
        members = [{"member_type": member_type, "member_id": member_id, "stage": args.get("stage")}]
    if not isinstance(members, list) or not members:
        return _err("members must be a non-empty array")

    force = bool(args.get("force"))
    approval_id = args.get("approval_id")
    actor_type, actor_id = _actor(args)
    if len(members) >= _MASS_THRESHOLD:
        blocked = _gate(
            workspace_id,
            kind="mass_update",
            subject=f"Add {len(members)} members to list {list_id}",
            payload={"list_id": list_id, "member_count": len(members)},
            object_type="list",
            object_id=list_id,
            actor_id=actor_id,
            force=force,
            approval_id=str(approval_id) if approval_id else None,
        )
        if blocked:
            return _ok(blocked)

    added = []
    for m in members:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("member_id") or "").strip()
        mtype = str(m.get("member_type") or "lead").strip()
        if not mid:
            continue
        # Fail closed: member must live in this workspace.
        if not _get_entity(store, workspace_id, mtype, mid):
            return _err(
                "member_not_found_in_workspace",
                error_code="cross_workspace_denied",
                member_id=mid,
            )
        try:
            row = store.add_list_member(
                workspace_id,
                list_id,
                member_type=mtype,
                member_id=mid,
                stage=m.get("stage"),
            )
        except LookupError as exc:
            return _err(str(exc))
        added.append(row)
    return _ok(
        {
            "list_id": list_id,
            "count": len(added),
            "memberships": added,
            "workspace_id": workspace_id,
        }
    )


def crm_set_stage(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    stage = str(args.get("stage") or "").strip()
    if not stage:
        return _err("stage is required")
    entity_type = str(args.get("entity_type") or args.get("entity") or "lead").strip()
    ids: list[str] = []
    if args.get("ids") and isinstance(args["ids"], list):
        ids = [str(i).strip() for i in args["ids"] if str(i).strip()]
    elif args.get("entity_id") or args.get("id"):
        ids = [str(args.get("entity_id") or args.get("id")).strip()]
    if not ids:
        return _err("entity_id or ids is required")

    store = _store()
    force = bool(args.get("force"))
    approval_id = args.get("approval_id")
    actor_type, actor_id = _actor(args)
    is_mass = len(ids) >= _MASS_THRESHOLD
    paying = stage in PAYING_STAGES

    if is_mass:
        blocked = _gate(
            workspace_id,
            kind="mass_update",
            subject=f"Mass set stage={stage} on {len(ids)} {entity_type}(s)",
            payload={"ids": ids, "stage": stage, "entity_type": entity_type},
            object_type=entity_type if not entity_type.endswith("s") else entity_type[:-1],
            object_id=ids[0],
            actor_id=actor_id,
            force=force,
            approval_id=str(approval_id) if approval_id else None,
        )
        if blocked:
            return _ok(blocked)
    elif paying:
        existing = _get_entity(store, workspace_id, entity_type, ids[0])
        if not existing:
            return _err("not_found", error_code="crm_not_found")
        if existing.get("stage") != stage:
            blocked = _gate(
                workspace_id,
                kind="stage_customer_paying",
                subject=f"Promote {entity_type} {ids[0]} to {stage}",
                payload={"id": ids[0], "from": existing.get("stage"), "to": stage},
                object_type=entity_type if not entity_type.endswith("s") else entity_type[:-1],
                object_id=ids[0],
                actor_id=actor_id,
                force=force,
                approval_id=str(approval_id) if approval_id else None,
            )
            if blocked:
                return _ok(blocked)

    updated = []
    for eid in ids:
        existing = _get_entity(store, workspace_id, entity_type, eid)
        if not existing:
            return _err("not_found", error_code="crm_not_found", entity_id=eid)
        if str(existing.get("workspace_id") or "") != workspace_id:
            return _err("cross_workspace_denied", error_code="cross_workspace_denied")
        try:
            row = _update_stage(store, workspace_id, entity_type, eid, stage)
        except ConflictError as exc:
            return _err(str(exc), error_code="version_conflict")
        if row:
            updated.append(row)
    return _ok(
        {
            "workspace_id": workspace_id,
            "stage": stage,
            "count": len(updated),
            "items": updated,
            "citations": [{"id": r["id"], "entity_type": entity_type} for r in updated],
            "telegram_reply": format_telegram_reply(
                f"Set stage={stage} on {len(updated)} {entity_type}(s)."
            ),
        }
    )


def crm_ask(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    try:
        result = ask_crm(
            _store(),
            workspace_id,
            question=args.get("question") or args.get("q_nl"),
            entity=args.get("entity") or args.get("entity_type"),
            stage=args.get("stage"),
            domain_pack=args.get("domain_pack"),
            tag=args.get("tag"),
            source=args.get("source"),
            q=args.get("q") or args.get("query"),
            open_only=args.get("open_only"),
            limit=int(args.get("limit") or 25),
        )
    except ValueError as exc:
        return _err(str(exc))
    return _ok(result)


def crm_suppress(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    store = _store()
    actor_type, actor_id = _actor(args)
    force = bool(args.get("force"))
    approval_id = args.get("approval_id")
    action = str(args.get("action") or "add").strip().lower()

    if action in {"undo", "lift", "remove", "delete"}:
        entry_id = str(args.get("suppression_id") or args.get("id") or "").strip()
        address = str(args.get("address") or "").strip().lower()
        channel = str(args.get("channel") or "email").strip()
        entry = None
        if entry_id:
            rows = store.list_suppressions(workspace_id, limit=5000)
            entry = next((r for r in rows if r.get("id") == entry_id), None)
        elif address:
            rows = store.list_suppressions(workspace_id, limit=5000)
            entry = next(
                (
                    r
                    for r in rows
                    if str(r.get("address") or "").lower() == address
                    and str(r.get("channel") or "") == channel
                ),
                None,
            )
        if not entry:
            return _err("not_found", error_code="suppression_not_found")
        blocked = _gate(
            workspace_id,
            kind="suppress_undo",
            subject=f"Undo suppression {entry.get('id')}",
            payload={"suppression_id": entry.get("id"), "address": entry.get("address")},
            object_type="suppression_entry",
            object_id=entry.get("id"),
            actor_id=actor_id,
            force=force,
            approval_id=str(approval_id) if approval_id else None,
        )
        if blocked:
            return _ok(blocked)
        deleted = store.delete_suppression_entry(workspace_id, entry["id"])
        return _ok({"ok": True, "undone": True, "suppression": deleted, "workspace_id": workspace_id})

    address = str(args.get("address") or "").strip().lower()
    if not address:
        return _err("address is required")
    try:
        row = store.create_suppression_entry(
            workspace_id,
            address=address,
            channel=args.get("channel") or "email",
            reason=args.get("reason"),
            source=args.get("source") or "agent",
            subject_type=args.get("subject_type"),
            subject_id=args.get("subject_id"),
            actor_type=actor_type,
            actor_id=actor_id,
        )
    except ValueError as exc:
        return _err(str(exc))
    # Optionally mark subject stage suppressed (single, not mass).
    subject_type = str(args.get("subject_type") or "").strip()
    subject_id = str(args.get("subject_id") or "").strip()
    subject_updated = None
    if subject_type and subject_id:
        existing = _get_entity(store, workspace_id, subject_type, subject_id)
        if existing and str(existing.get("workspace_id") or "") == workspace_id:
            subject_updated = _update_stage(store, workspace_id, subject_type, subject_id, "suppressed")
    return _ok(
        {
            "suppression": row,
            "subject": subject_updated,
            "workspace_id": workspace_id,
            "telegram_reply": format_telegram_reply(f"Suppressed {address}."),
        }
    )


# ── Registration ──────────────────────────────────────────────


def _ws_props(**extra: Any) -> dict[str, Any]:
    props = {"workspace_id": {"type": "string"}}
    props.update(extra)
    return props


registry.register(
    name="crm_search",
    toolset=TOOLSET,
    schema={
        "name": "crm_search",
        "description": "Search CRM leads/contacts/accounts/deals in a workspace (filter by q, stage, tag, pack).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity={"type": "string"},
                q={"type": "string"},
                query={"type": "string"},
                stage={"type": "string"},
                source={"type": "string"},
                domain_pack={"type": "string"},
                tag={"type": "string"},
                limit={"type": "integer"},
                offset={"type": "integer"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_search,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_get",
    toolset=TOOLSET,
    schema={
        "name": "crm_get",
        "description": "Get one CRM record by entity_type and id (workspace-scoped).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity_type={"type": "string"},
                entity={"type": "string"},
                entity_id={"type": "string"},
                id={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_get,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_upsert_lead",
    toolset=TOOLSET,
    schema={
        "name": "crm_upsert_lead",
        "description": "Create or update a CRM lead. Soft Wall gates delete=true.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                name={"type": "string"},
                company_name={"type": "string"},
                company_number={"type": "string"},
                email={"type": "string"},
                emails={"type": "array"},
                phones={"type": "array"},
                source={"type": "string"},
                domain_pack={"type": "string"},
                stage={"type": "string"},
                tags={"type": "array", "items": {"type": "string"}},
                account_id={"type": "string"},
                external_source_id={"type": "string"},
                lead_id={"type": "string"},
                id={"type": "string"},
                delete={"type": "boolean"},
                action={"type": "string"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
                write_memory={"type": "boolean"},
                memory_note={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_upsert_lead,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_upsert_contact",
    toolset=TOOLSET,
    schema={
        "name": "crm_upsert_contact",
        "description": "Create or update a CRM contact. Soft Wall gates delete=true.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                display_name={"type": "string"},
                name={"type": "string"},
                email={"type": "string"},
                emails={"type": "array"},
                phones={"type": "array"},
                account_id={"type": "string"},
                source={"type": "string"},
                domain_pack={"type": "string"},
                stage={"type": "string"},
                tags={"type": "array", "items": {"type": "string"}},
                contact_id={"type": "string"},
                id={"type": "string"},
                delete={"type": "boolean"},
                action={"type": "string"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_upsert_contact,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_add_activity",
    toolset=TOOLSET,
    schema={
        "name": "crm_add_activity",
        "description": "Log a CRM activity (note/call/email) on a lead or contact.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity_type={"type": "string"},
                entity_id={"type": "string"},
                activity_type={"type": "string"},
                type={"type": "string"},
                channel={"type": "string"},
                subject={"type": "string"},
                body={"type": "string"},
                metadata={"type": "object"},
                write_memory={"type": "boolean"},
                occurred_at={"type": "string"},
            ),
            "required": ["workspace_id", "entity_type", "entity_id"],
        },
    },
    handler=crm_add_activity,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_list_create",
    toolset=TOOLSET,
    schema={
        "name": "crm_list_create",
        "description": "Create a CRM list (campaign/batch target set).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                name={"type": "string"},
                description={"type": "string"},
                domain_pack={"type": "string"},
                source={"type": "string"},
                tags={"type": "array", "items": {"type": "string"}},
            ),
            "required": ["workspace_id", "name"],
        },
    },
    handler=crm_list_create,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_list_add_members",
    toolset=TOOLSET,
    schema={
        "name": "crm_list_add_members",
        "description": "Add members to a CRM list. Soft Wall gates mass adds (2+).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                list_id={"type": "string"},
                member_type={"type": "string"},
                member_id={"type": "string"},
                stage={"type": "string"},
                members={"type": "array", "items": {"type": "object"}},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id", "list_id"],
        },
    },
    handler=crm_list_add_members,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_set_stage",
    toolset=TOOLSET,
    schema={
        "name": "crm_set_stage",
        "description": "Set CRM stage. Soft Wall for paying/customer and mass updates.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity_type={"type": "string"},
                entity={"type": "string"},
                entity_id={"type": "string"},
                id={"type": "string"},
                ids={"type": "array", "items": {"type": "string"}},
                stage={"type": "string"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id", "stage"],
        },
    },
    handler=crm_set_stage,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_ask",
    toolset=TOOLSET,
    schema={
        "name": "crm_ask",
        "description": (
            "Ask-data over CRM: filter/SQL-style counts from real rows only. "
            "Always cites record ids; never invents rows."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                question={"type": "string"},
                entity={"type": "string"},
                entity_type={"type": "string"},
                stage={"type": "string"},
                domain_pack={"type": "string"},
                tag={"type": "string"},
                source={"type": "string"},
                q={"type": "string"},
                query={"type": "string"},
                open_only={"type": "boolean"},
                limit={"type": "integer"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_ask,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_suppress",
    toolset=TOOLSET,
    schema={
        "name": "crm_suppress",
        "description": "Add a suppression entry, or undo/lift with Soft Wall (action=undo).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                address={"type": "string"},
                channel={"type": "string"},
                reason={"type": "string"},
                source={"type": "string"},
                subject_type={"type": "string"},
                subject_id={"type": "string"},
                action={"type": "string"},
                suppression_id={"type": "string"},
                id={"type": "string"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_suppress,
    check_fn=check_crm_requirements,
)


def crm_enroll_list(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    list_id = str(args.get("list_id") or "").strip()
    sequence_id = str(args.get("sequence_id") or "").strip() or None
    campaign_id = str(args.get("campaign_id") or "").strip() or None
    if not list_id:
        return _err("list_id is required")
    if not sequence_id and not campaign_id:
        return _err("sequence_id or campaign_id is required")
    actor_type, actor_id = _actor(args)
    preflight_only = bool(args.get("preflight_only"))
    from keprix.crm.enroll import enroll_list, preflight_crm_list_enroll

    if preflight_only:
        try:
            report = preflight_crm_list_enroll(
                workspace_id=workspace_id,
                list_id=list_id,
                sequence_id=sequence_id or "",
                campaign_id=campaign_id,
            )
        except LookupError:
            return _err("list_not_found", error_code="list_not_found")
        return _ok(report)

    result = enroll_list(
        workspace_id=workspace_id,
        list_id=list_id,
        sequence_id=sequence_id,
        campaign_id=campaign_id,
        audience_hash=args.get("audience_hash"),
        content_hash=args.get("content_hash"),
        require_soft_wall=bool(args.get("require_soft_wall", True)),
        force=bool(args.get("force")),
        approval_id=args.get("approval_id"),
        start_immediately=bool(args.get("start_immediately", True)),
        actor_id=actor_id,
    )
    return _ok(result)


def crm_offer_booking(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = _require_workspace(args)
    if not workspace_id:
        return _err("workspace_id is required")
    contact_id = str(args.get("contact_id") or "").strip() or None
    lead_id = str(args.get("lead_id") or "").strip() or None
    if not contact_id and not lead_id:
        return _err("contact_id or lead_id is required")
    from keprix.crm.booking import offer_booking

    result = offer_booking(
        workspace_id,
        contact_id=contact_id,
        lead_id=lead_id,
        host_user_id=args.get("host_user_id") or workspace_id,
        event_type_id=args.get("event_type_id") or args.get("vical_event_type_id"),
        campaign_id=args.get("campaign_id"),
    )
    return _ok(result)


registry.register(
    name="crm_enroll_list",
    toolset=TOOLSET,
    schema={
        "name": "crm_enroll_list",
        "description": (
            "Soft Wall gated enroll of a CRM List into Soft Wall outreach sequence. "
            "Use preflight_only to get eligible/suppressed counts before approve."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                list_id={"type": "string"},
                sequence_id={"type": "string"},
                campaign_id={"type": "string"},
                audience_hash={"type": "string"},
                content_hash={"type": "string"},
                preflight_only={"type": "boolean"},
                require_soft_wall={"type": "boolean"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id", "list_id"],
        },
    },
    handler=crm_enroll_list,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_offer_booking",
    toolset=TOOLSET,
    schema={
        "name": "crm_offer_booking",
        "description": "Return viCal /book/{slug} deep links for a CRM contact or lead (GUI mesh).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                contact_id={"type": "string"},
                lead_id={"type": "string"},
                host_user_id={"type": "string"},
                event_type_id={"type": "string"},
                vical_event_type_id={"type": "string"},
                campaign_id={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_offer_booking,
    check_fn=check_crm_requirements,
)


def discovery_run(args: dict[str, Any], **_kwargs: Any) -> str:
    """Agent tool: run a discovery adapter into a CRM DiscoveryJob (+ optional List)."""
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    adapter = str(args.get("adapter") or "").strip().lower()
    if not adapter:
        return _err("adapter is required")

    if "scrape" in adapter and adapter not in {"social_csv_export"}:
        from keprix.discovery.adapters.social import scrape_refusal_payload

        return _ok(scrape_refusal_payload(adapter))

    from keprix.discovery import bootstrap_discovery
    from keprix.discovery.runner import get_discovery_runner

    bootstrap_discovery()
    runner = get_discovery_runner()
    actor_type, actor_id = _actor(args)
    params = dict(args.get("params") or {})
    for key in ("rows", "csv_text", "user_schema", "schema", "location", "sic", "status", "keywords"):
        if key in args and key not in params:
            params[key] = args[key]
    icp_id = args.get("icp_id") or params.get("icp_id")
    icp_version = args.get("icp_version") if args.get("icp_version") is not None else params.get("icp_version")
    job = runner.create_job(
        ws,
        adapter,
        query=args.get("query") or args.get("q"),
        params=params,
        domain_pack=str(args.get("domain_pack") or "generic"),
        limits=dict(args.get("limits") or {}),
        list_name=args.get("list_name"),
        auto_materialize=bool(args.get("auto_materialize") or args.get("materialize") or False),
        actor_type=actor_type,
        actor_id=actor_id,
        icp_id=str(icp_id) if icp_id else None,
        icp_version=int(icp_version) if icp_version is not None else None,
    )
    run_now = args.get("run_now", True)
    if not run_now:
        return _ok(
            {
                "job": job,
                "deep_links": {"job": f"/crm/jobs/{job['id']}", "discover": "/crm/discover"},
            }
        )
    result = runner.run_job(
        ws,
        job["id"],
        materialize=bool(args.get("materialize") or args.get("auto_materialize") or False),
        approval_id=args.get("approval_id"),
        force=bool(args.get("force") or False),
    )
    # Never leave the operator with only tool JSON: always include GUI deep links.
    deep = result.get("deep_links") or {}
    deep.setdefault("job", f"/crm/jobs/{job['id']}")
    deep.setdefault("discover", "/crm/discover")
    if result.get("materialize") and (result["materialize"] or {}).get("list_id"):
        deep.setdefault("list", f"/crm/lists/{result['materialize']['list_id']}")
    result["deep_links"] = deep
    return _ok(result)


registry.register(
    name="discovery_run",
    toolset=TOOLSET,
    schema={
        "name": "discovery_run",
        "description": (
            "Run a CRM discovery adapter (companies_house, csv, web_directory, social_*, "
            "property_csv, health_csv, etc.). Creates a DiscoveryJob and returns deep links "
            "to /crm/jobs/{id} and draft List. Does not scrape social platforms; use API adapters "
            "or social_csv_export. Discovery candidates are not contactable until policy says so."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                adapter={"type": "string"},
                query={"type": "string"},
                q={"type": "string"},
                params={"type": "object"},
                domain_pack={"type": "string"},
                limits={"type": "object"},
                list_name={"type": "string"},
                auto_materialize={"type": "boolean"},
                materialize={"type": "boolean"},
                run_now={"type": "boolean"},
                rows={"type": "array"},
                csv_text={"type": "string"},
                location={"type": "string"},
                sic={"type": "string"},
                status={"type": "string"},
                keywords={"type": "string"},
                icp_id={"type": "string"},
                icp_version={"type": "integer"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id", "adapter"],
        },
    },
    handler=discovery_run,
    check_fn=check_crm_requirements,
)


def crm_icp_list(args: dict[str, Any], **kwargs: Any) -> str:
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    from keprix.crm import icp as icp_mod

    store = _store()
    items = icp_mod.list_icps(store, ws, name=args.get("name"))
    active = icp_mod.get_active_icp(store, ws)
    return _ok(
        {
            "items": items,
            "count": len(items),
            "active": active,
            "deep_links": {"ui": "/crm/icp"},
        }
    )


def crm_icp_use(args: dict[str, Any], **kwargs: Any) -> str:
    """Pin or Soft Wall-activate an ICP version for discovery defaults."""
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    icp_id = str(args.get("icp_id") or "").strip()
    if not icp_id:
        return _err("icp_id is required")
    from keprix.crm import icp as icp_mod

    store = _store()
    row = icp_mod.get_icp(store, ws, icp_id)
    if not row:
        return _err("icp_not_found")
    activate = bool(args.get("activate") or False)
    if activate:
        result = icp_mod.activate_icp(
            store,
            ws,
            icp_id,
            actor_id=_actor(args)[1],
            force=bool(args.get("force") or False),
            approval_id=args.get("approval_id"),
        )
        result["deep_links"] = {"ui": "/crm/icp", "approvals": "/crm"}
        return _ok(result)
    return _ok(
        {
            "ok": True,
            "pinned": {"icp_id": row["id"], "version": row.get("version"), "name": row.get("name")},
            "note": "Pass icp_id to discovery_run. Soft Wall activate with activate=true.",
            "deep_links": {"ui": "/crm/icp"},
        }
    )


registry.register(
    name="crm_icp_list",
    toolset=TOOLSET,
    schema={
        "name": "crm_icp_list",
        "description": "List saved ICP definition versions for a workspace. Active ICP is returned separately.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(name={"type": "string"}),
            "required": ["workspace_id"],
        },
    },
    handler=crm_icp_list,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_icp_use",
    toolset=TOOLSET,
    schema={
        "name": "crm_icp_use",
        "description": (
            "Select an ICP version for discovery (pin), or Soft Wall-activate it as the workspace default "
            "(activate=true). Activation deactivates sibling versions of the same name."
        ),
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                icp_id={"type": "string"},
                activate={"type": "boolean"},
                force={"type": "boolean"},
                approval_id={"type": "string"},
            ),
            "required": ["workspace_id", "icp_id"],
        },
    },
    handler=crm_icp_use,
    check_fn=check_crm_requirements,
)


def crm_score_icp(args: dict[str, Any], **kwargs: Any) -> str:
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    entity_type = str(args.get("entity_type") or "lead")
    entity_id = str(args.get("entity_id") or "").strip()
    if not entity_id:
        return _err("entity_id is required")
    from keprix.crm.icp_scoring import score_entity

    return _ok(
        score_entity(
            _store(),
            ws,
            entity_type=entity_type,
            entity_id=entity_id,
            icp_id=args.get("icp_id"),
        )
    )


def crm_account_brief(args: dict[str, Any], **kwargs: Any) -> str:
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    entity_type = str(args.get("entity_type") or "lead")
    entity_id = str(args.get("entity_id") or "").strip()
    if not entity_id:
        return _err("entity_id is required")
    from keprix.crm.icp_scoring import generate_account_brief

    return _ok(
        generate_account_brief(
            _store(),
            ws,
            entity_type=entity_type,
            entity_id=entity_id,
            icp_id=args.get("icp_id"),
        )
    )


def crm_data_quality_summary(args: dict[str, Any], **kwargs: Any) -> str:
    ws = _require_workspace(args)
    if not ws:
        return _err("workspace_id is required")
    from keprix.crm.data_quality import quality_summary

    return _ok(
        quality_summary(
            _store(),
            ws,
            pack=args.get("pack"),
            stage=args.get("stage"),
            owner=args.get("owner"),
        )
    )


registry.register(
    name="crm_score_icp",
    toolset=TOOLSET,
    schema={
        "name": "crm_score_icp",
        "description": "Score a lead/account/contact against the active (or pinned) ICP version.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity_type={"type": "string"},
                entity_id={"type": "string"},
                icp_id={"type": "string"},
            ),
            "required": ["workspace_id", "entity_id"],
        },
    },
    handler=crm_score_icp,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_account_brief",
    toolset=TOOLSET,
    schema={
        "name": "crm_account_brief",
        "description": "Generate an evidence-backed account brief and ICP score for a CRM entity.",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                entity_type={"type": "string"},
                entity_id={"type": "string"},
                icp_id={"type": "string"},
            ),
            "required": ["workspace_id", "entity_id"],
        },
    },
    handler=crm_account_brief,
    check_fn=check_crm_requirements,
)

registry.register(
    name="crm_data_quality_summary",
    toolset=TOOLSET,
    schema={
        "name": "crm_data_quality_summary",
        "description": "Summarise CRM data freshness/quality (incomplete, stale, conflicts, unverified).",
        "parameters": {
            "type": "object",
            "properties": _ws_props(
                pack={"type": "string"},
                stage={"type": "string"},
                owner={"type": "string"},
            ),
            "required": ["workspace_id"],
        },
    },
    handler=crm_data_quality_summary,
    check_fn=check_crm_requirements,
)
