"""First-class Document Vault agent tools (Prompt 650).

Backed only by the canonical Document Vault service. Trusted session context
supplies workspace/actor; model-supplied tenants and host paths fail closed.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Callable

from tools.registry import registry

from keprix.document_vault.agent_context import resolve_vault_context
from keprix.document_vault.flags import load_flags
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import get_document_vault_service
from keprix.document_vault.soft_wall import gate_vault_action, redact_audit_payload
from keprix.document_vault.store import get_document_vault_store

TOOLSET = "document_vault"


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"ok": False, "error": message, **extra}, ensure_ascii=False)


def document_vault_configured() -> bool:
    return bool(load_flags().enabled)


def _svc():
    return get_document_vault_service()


def _store():
    return get_document_vault_store()


def _ctx(args: dict[str, Any], kwargs: dict[str, Any]):
    return resolve_vault_context(args, **kwargs)


def _fail(exc: Exception) -> str:
    if isinstance(exc, VaultError):
        return _ok({"ok": False, "error_code": exc.code, "error": exc.message, **exc.extra})
    return _err(str(exc))


def _compact_item(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": item.get("kind"),
        "parent_id": item.get("parent_id"),
        "current_revision": item.get("current_revision"),
        "content_authority": item.get("content_authority"),
        "byte_size": item.get("byte_size"),
        "trashed": bool(item.get("trashed") or item.get("trashed_at")),
        "updated_at": item.get("updated_at"),
    }


def _audit(workspace_id: str, *, action: str, actor_id: str, item_id: str | None, payload: dict[str, Any]) -> None:
    store = _store()
    store._audit(
        workspace_id,
        item_id=item_id,
        action=f"agent:{action}",
        actor_id=actor_id,
        payload=redact_audit_payload(payload),
    )
    store._commit()


def _soft_wall(
    ctx,
    *,
    kind: str,
    subject: str,
    payload: dict[str, Any],
    object_id: str | None = None,
    approval_id: str | None = None,
) -> dict[str, Any] | None:
    gate = gate_vault_action(
        ctx.workspace_id,
        kind=kind,
        subject=subject,
        payload=payload,
        object_id=object_id,
        actor_id=ctx.actor_id,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {
            "ok": False,
            "blocked": True,
            "error_code": gate.get("error_code") or "soft_wall_required",
            "approval": gate.get("approval"),
        }
    return None


def document_vault_list(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        parent_id = args.get("parent_id")
        limit = int(args.get("limit") or 50)
        offset = int(args.get("offset") or 0)
        include_trashed = bool(args.get("include_trashed"))
        result = _store().list_items(
            ctx.workspace_id,
            parent_id=parent_id,
            include_trashed=include_trashed,
            limit=limit,
            offset=offset,
        )
        items = [_compact_item(row) for row in result.get("items") or []]
        return _ok(
            {
                "ok": True,
                "workspace_id": ctx.workspace_id,
                "parent_id": parent_id,
                "items": items,
                "count": len(items),
                "total": result.get("total"),
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as exc:
        return _fail(exc)


def document_vault_search(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        q = str(args.get("q") or args.get("query") or "").strip()
        if not q:
            return _err("q is required")
        mode = str(args.get("mode") or "metadata").strip().lower()
        if mode in {"content", "rag"}:
            from keprix.document_vault.search.retriever import content_search

            result = content_search(
                _store(),
                ctx.workspace_id,
                q,
                limit=int(args.get("limit") or 20),
                grants=ctx.grants or None,
            )
            return _ok(result)
        result = _store().search(ctx.workspace_id, q, limit=int(args.get("limit") or 50))
        items = [_compact_item(row) for row in result.get("items") or []]
        return _ok({"ok": True, "q": q, "items": items, "count": len(items), "mode": "metadata"})
    except Exception as exc:
        return _fail(exc)


def document_vault_inspect(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        item = _store().get_item(ctx.workspace_id, item_id, include_trashed=True)
        if not item:
            return _ok({"ok": False, "error_code": "not_found"})
        mapping = _store().get_provider_mapping_for_item(ctx.workspace_id, item_id, "google_drive")
        return _ok(
            {
                "ok": True,
                "item": _compact_item(item),
                "mime_type": item.get("mime_type"),
                "checksum": item.get("checksum"),
                "classification": item.get("classification"),
                "provider_mapping": (
                    {
                        "provider_item_id": mapping.get("provider_item_id"),
                        "provider_revision": mapping.get("provider_revision"),
                        "conflict_state": mapping.get("conflict_state"),
                    }
                    if mapping
                    else None
                ),
            }
        )
    except Exception as exc:
        return _fail(exc)


def document_vault_read(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        text = svc.read_text(ctx.workspace_id, item_id)
        offset = int(args.get("offset") or 0)
        limit = args.get("limit")
        total = len(text)
        sliced = text[offset:]
        if limit is not None:
            sliced = sliced[: int(limit)]
        return _ok(
            {
                "ok": True,
                "item_id": item_id,
                "content": sliced,
                "offset": offset,
                "length": len(sliced),
                "total_length": total,
                "truncated": offset + len(sliced) < total,
            }
        )
    except Exception as exc:
        return _fail(exc)


def document_vault_create_folder(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        name = str(args.get("name") or "").strip()
        if not name:
            return _err("name is required")
        item = svc.create_folder(
            ctx.workspace_id,
            name,
            parent_id=args.get("parent_id"),
            actor_id=ctx.actor_id,
        )
        _audit(ctx.workspace_id, action="create_folder", actor_id=ctx.actor_id, item_id=item["id"], payload={"name": name})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_create_file(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        name = str(args.get("name") or "").strip()
        if not name:
            return _err("name is required")
        content = str(args.get("content") or "")
        kind = str(args.get("kind") or "markdown")
        item = svc.create_text_item(
            ctx.workspace_id,
            name,
            content,
            kind=kind,
            parent_id=args.get("parent_id"),
            actor_id=ctx.actor_id,
            item_id=args.get("idempotency_key"),
        )
        _audit(
            ctx.workspace_id,
            action="create_file",
            actor_id=ctx.actor_id,
            item_id=item["id"],
            payload={"name": name, "kind": kind, "revision": item.get("current_revision")},
        )
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_update(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        if "content" not in args:
            return _err("content is required")
        expected = args.get("expected_revision")
        item = svc.write_content(
            ctx.workspace_id,
            item_id,
            str(args.get("content") or "").encode("utf-8"),
            expected_revision=int(expected) if expected is not None else None,
            actor_id=ctx.actor_id,
            change_summary=str(args.get("change_summary") or "agent update"),
        )
        _audit(
            ctx.workspace_id,
            action="update",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"expected_revision": expected, "revision": item.get("current_revision")},
        )
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_append(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        text = str(args.get("text") or args.get("content") or "")
        if not item_id or not text:
            return _err("item_id and text are required")
        expected = args.get("expected_revision")
        item = svc.append_text(
            ctx.workspace_id,
            item_id,
            text,
            expected_revision=int(expected) if expected is not None else None,
            actor_id=ctx.actor_id,
        )
        _audit(ctx.workspace_id, action="append", actor_id=ctx.actor_id, item_id=item_id, payload={"chars": len(text)})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_rename(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        name = str(args.get("name") or "").strip()
        if not item_id or not name:
            return _err("item_id and name are required")
        item = _store().rename(ctx.workspace_id, item_id, name, actor_id=ctx.actor_id)
        _audit(ctx.workspace_id, action="rename", actor_id=ctx.actor_id, item_id=item_id, payload={"name": name})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_move(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        item = _store().move(
            ctx.workspace_id,
            item_id,
            parent_id=args.get("parent_id"),
            actor_id=ctx.actor_id,
        )
        _audit(
            ctx.workspace_id,
            action="move",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"parent_id": args.get("parent_id")},
        )
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_copy(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        item = _store().copy(
            ctx.workspace_id,
            item_id,
            parent_id=args.get("parent_id"),
            name=args.get("name"),
            actor_id=ctx.actor_id,
        )
        _audit(ctx.workspace_id, action="copy", actor_id=ctx.actor_id, item_id=item["id"], payload={"source": item_id})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_trash(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        item = _store().trash(ctx.workspace_id, item_id, actor_id=ctx.actor_id)
        _audit(ctx.workspace_id, action="trash", actor_id=ctx.actor_id, item_id=item_id, payload={})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_restore(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        item = _store().restore(ctx.workspace_id, item_id, actor_id=ctx.actor_id)
        _audit(ctx.workspace_id, action="restore", actor_id=ctx.actor_id, item_id=item_id, payload={})
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_permanent_delete(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        blocked = _soft_wall(
            ctx,
            kind="document_vault.permanent_delete",
            subject=f"Permanently delete vault item {item_id}",
            payload={"item_id": item_id, "intent": "permanent_delete"},
            object_id=item_id,
            approval_id=args.get("approval_id"),
        )
        if blocked:
            return _ok(blocked)
        result = _store().permanent_delete(ctx.workspace_id, item_id, actor_id=ctx.actor_id)
        _audit(
            ctx.workspace_id,
            action="permanent_delete",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"approval_id": args.get("approval_id")},
        )
        return _ok({"ok": True, **result})
    except Exception as exc:
        return _fail(exc)


def document_vault_revisions(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        if not item_id:
            return _err("item_id is required")
        rows = _store().list_revisions(ctx.workspace_id, item_id)
        compact = [
            {
                "revision": row.get("revision"),
                "checksum": row.get("checksum"),
                "byte_size": row.get("byte_size"),
                "change_summary": row.get("change_summary"),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]
        return _ok({"ok": True, "item_id": item_id, "revisions": compact})
    except Exception as exc:
        return _fail(exc)


def document_vault_restore_revision(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        revision = args.get("revision")
        if not item_id or revision is None:
            return _err("item_id and revision are required")
        item = svc.restore_revision(ctx.workspace_id, item_id, int(revision), actor_id=ctx.actor_id)
        _audit(
            ctx.workspace_id,
            action="restore_revision",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"revision": revision},
        )
        return _ok({"ok": True, "item": _compact_item(item)})
    except Exception as exc:
        return _fail(exc)


def document_vault_import(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        name = str(args.get("name") or "upload.bin").strip()
        content_b64 = args.get("content_base64")
        content = args.get("content")
        if content_b64:
            data = base64.b64decode(str(content_b64))
        elif content is not None:
            data = str(content).encode("utf-8")
        else:
            return _err("content or content_base64 is required")
        result = svc.import_bytes(
            ctx.workspace_id,
            data,
            filename=name,
            parent_id=args.get("parent_id"),
            actor_id=ctx.actor_id,
            declared_mime=str(args.get("mime_type") or ""),
        )
        item = result.get("item") if isinstance(result, dict) else result
        item_id = (item or {}).get("id") if isinstance(item, dict) else None
        _audit(ctx.workspace_id, action="import", actor_id=ctx.actor_id, item_id=item_id, payload={"name": name})
        return _ok({"ok": True, "result": result if not isinstance(item, dict) else {"item": _compact_item(item)}})
    except Exception as exc:
        return _fail(exc)


def document_vault_export(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        svc = _svc()
        svc.require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        fmt = str(args.get("format") or "markdown")
        if not item_id:
            return _err("item_id is required")
        item = _store().get_item(ctx.workspace_id, item_id, include_trashed=True)
        classification = str((item or {}).get("classification") or "internal")
        if classification in {"secret", "restricted", "confidential"}:
            blocked = _soft_wall(
                ctx,
                kind="document_vault.classified_export",
                subject=f"Export classified item {item_id} as {fmt}",
                payload={"item_id": item_id, "format": fmt, "classification": classification},
                object_id=item_id,
                approval_id=args.get("approval_id"),
            )
            if blocked:
                return _ok(blocked)
        result = svc.export_item(ctx.workspace_id, item_id, target_format=fmt, actor_id=ctx.actor_id)
        export = result.get("export") or {}
        data = export.get("data") or b""
        if isinstance(data, str):
            data_b64 = base64.b64encode(data.encode("utf-8")).decode("ascii")
            nbytes = len(data.encode("utf-8"))
        else:
            data_b64 = base64.b64encode(bytes(data)).decode("ascii")
            nbytes = len(bytes(data))
        _audit(
            ctx.workspace_id,
            action="export",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"format": fmt, "bytes": nbytes, "classification": classification},
        )
        return _ok(
            {
                "ok": True,
                "item_id": item_id,
                "format": fmt,
                "mime": export.get("mime"),
                "byte_size": nbytes,
                "content_base64": data_b64,
                "fidelity": export.get("fidelity"),
            }
        )
    except Exception as exc:
        return _fail(exc)


def document_vault_sync_status(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        from keprix.document_vault.google.service import GoogleDriveVaultService

        status = GoogleDriveVaultService().status(ctx.workspace_id)
        return _ok({"ok": True, "status": status})
    except Exception as exc:
        return _fail(exc)


def document_vault_sync_request(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        from keprix.document_vault.google.service import GoogleDriveVaultService

        direction = str(args.get("direction") or "inbound")
        result = GoogleDriveVaultService().sync_now(
            ctx.workspace_id,
            source=str(args.get("source") or "manual"),
            actor_id=ctx.actor_id,
            direction=direction,
            item_id=args.get("item_id"),
        )
        _audit(
            ctx.workspace_id,
            action="sync_request",
            actor_id=ctx.actor_id,
            item_id=args.get("item_id"),
            payload={"direction": direction},
        )
        return _ok({"ok": True, "result": result})
    except Exception as exc:
        return _fail(exc)


def document_vault_conflict_resolve(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        ctx = _ctx(args, kwargs)
        from keprix.document_vault.google.service import GoogleDriveVaultService

        item_id = str(args.get("item_id") or "").strip()
        choice = str(args.get("choice") or "").strip()
        if not item_id or choice not in {"keep_local", "keep_remote", "keep_both"}:
            return _err("item_id and choice (keep_local|keep_remote|keep_both) required")
        if choice in {"keep_local", "keep_remote"}:
            blocked = _soft_wall(
                ctx,
                kind="document_vault.conflict_overwrite",
                subject=f"Resolve conflict {item_id} with {choice}",
                payload={"item_id": item_id, "choice": choice},
                object_id=item_id,
                approval_id=args.get("approval_id"),
            )
            if blocked:
                return _ok(blocked)
        result = GoogleDriveVaultService().resolve_conflict(
            ctx.workspace_id,
            item_id,
            choice=choice,
            actor_id=ctx.actor_id,
        )
        _audit(
            ctx.workspace_id,
            action="conflict_resolve",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"choice": choice, "approval_id": args.get("approval_id")},
        )
        return _ok({"ok": True, **result})
    except Exception as exc:
        return _fail(exc)


def document_vault_bulk(args: dict[str, Any], **kwargs: Any) -> str:
    """Destructive bulk trash requires Soft Wall."""
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_ids = args.get("item_ids") or []
        action = str(args.get("action") or "trash")
        if not isinstance(item_ids, list) or not item_ids:
            return _err("item_ids list is required")
        if action not in {"trash", "permanent_delete"}:
            return _err("action must be trash or permanent_delete")
        blocked = _soft_wall(
            ctx,
            kind="document_vault.bulk_destructive",
            subject=f"Bulk {action} {len(item_ids)} vault items",
            payload={"action": action, "item_ids": item_ids[:100], "count": len(item_ids)},
            approval_id=args.get("approval_id"),
        )
        if blocked:
            return _ok(blocked)
        results = []
        for item_id in item_ids:
            iid = str(item_id)
            if action == "trash":
                results.append(_compact_item(_store().trash(ctx.workspace_id, iid, actor_id=ctx.actor_id)))
            else:
                # permanent delete still needs per-item gate unless approval covers bulk
                results.append(_store().permanent_delete(ctx.workspace_id, iid, actor_id=ctx.actor_id))
        _audit(
            ctx.workspace_id,
            action=f"bulk_{action}",
            actor_id=ctx.actor_id,
            item_id=None,
            payload={"count": len(item_ids), "approval_id": args.get("approval_id")},
        )
        return _ok({"ok": True, "results": results, "count": len(results)})
    except Exception as exc:
        return _fail(exc)


def document_vault_share(args: dict[str, Any], **kwargs: Any) -> str:
    """External sharing is Soft Wall gated (policy stub until share service)."""
    try:
        ctx = _ctx(args, kwargs)
        _svc().require_enabled()
        item_id = str(args.get("item_id") or "").strip()
        audience = str(args.get("share_audience") or "external")
        if not item_id:
            return _err("item_id is required")
        blocked = _soft_wall(
            ctx,
            kind="document_vault.external_share",
            subject=f"Share vault item {item_id} to {audience}",
            payload={"item_id": item_id, "share_audience": audience, "permission": args.get("permission")},
            object_id=item_id,
            approval_id=args.get("approval_id"),
        )
        if blocked:
            return _ok(blocked)
        _audit(
            ctx.workspace_id,
            action="external_share",
            actor_id=ctx.actor_id,
            item_id=item_id,
            payload={"share_audience": audience, "approval_id": args.get("approval_id")},
        )
        return _ok(
            {
                "ok": True,
                "item_id": item_id,
                "shared": True,
                "share_audience": audience,
                "note": "Share grant recorded; channel delivery is owned by Prompt 651",
            }
        )
    except Exception as exc:
        return _fail(exc)


def _register(
    name: str,
    description: str,
    handler: Callable[..., str],
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> None:
    registry.register(
        name=name,
        toolset=TOOLSET,
        description=description,
        emoji="📁",
        requires_env=False,
        check_fn=document_vault_configured,
        schema={
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required or [],
                },
            },
        },
        handler=handler,
    )


_ITEM = {"item_id": {"type": "string"}}
_PARENT = {"parent_id": {"type": "string"}}
_APPROVAL = {"approval_id": {"type": "string", "description": "Approved Soft Wall id to resume"}}

_register(
    "document_vault_list",
    "List Document Vault items under a parent (paginated). Tenant vault only.",
    document_vault_list,
    {**_PARENT, "limit": {"type": "integer"}, "offset": {"type": "integer"}, "include_trashed": {"type": "boolean"}},
)
_register(
    "document_vault_search",
    "Search Document Vault by metadata or content (mode=metadata|content) with revision citations.",
    document_vault_search,
    {"q": {"type": "string"}, "limit": {"type": "integer"}, "mode": {"type": "string"}},
    ["q"],
)
_register(
    "document_vault_inspect",
    "Inspect Document Vault item metadata and sync mapping.",
    document_vault_inspect,
    _ITEM,
    ["item_id"],
)
_register(
    "document_vault_read",
    "Read Document Vault text content with optional offset/limit range.",
    document_vault_read,
    {**_ITEM, "offset": {"type": "integer"}, "limit": {"type": "integer"}},
    ["item_id"],
)
_register(
    "document_vault_create_folder",
    "Create a folder in the Document Vault.",
    document_vault_create_folder,
    {"name": {"type": "string"}, **_PARENT},
    ["name"],
)
_register(
    "document_vault_create_file",
    "Create a text/markdown file in the Document Vault.",
    document_vault_create_file,
    {
        "name": {"type": "string"},
        "content": {"type": "string"},
        "kind": {"type": "string"},
        "idempotency_key": {"type": "string"},
        **_PARENT,
    },
    ["name"],
)
_register(
    "document_vault_update",
    "Replace Document Vault file content with expected_revision optimistic check.",
    document_vault_update,
    {**_ITEM, "content": {"type": "string"}, "expected_revision": {"type": "integer"}, "change_summary": {"type": "string"}},
    ["item_id", "content"],
)
_register(
    "document_vault_append",
    "Append text to a Document Vault file with expected_revision.",
    document_vault_append,
    {**_ITEM, "text": {"type": "string"}, "expected_revision": {"type": "integer"}},
    ["item_id", "text"],
)
_register("document_vault_rename", "Rename a Document Vault item.", document_vault_rename, {**_ITEM, "name": {"type": "string"}}, ["item_id", "name"])
_register("document_vault_move", "Move a Document Vault item to a new parent folder.", document_vault_move, {**_ITEM, **_PARENT}, ["item_id"])
_register("document_vault_copy", "Copy a Document Vault item.", document_vault_copy, {**_ITEM, **_PARENT, "name": {"type": "string"}}, ["item_id"])
_register("document_vault_trash", "Move a Document Vault item to trash.", document_vault_trash, _ITEM, ["item_id"])
_register("document_vault_restore", "Restore a trashed Document Vault item.", document_vault_restore, _ITEM, ["item_id"])
_register(
    "document_vault_permanent_delete",
    "Permanently delete a trashed Document Vault item (Soft Wall / Rule of Two).",
    document_vault_permanent_delete,
    {**_ITEM, **_APPROVAL},
    ["item_id"],
)
_register("document_vault_revisions", "List Document Vault revisions for an item.", document_vault_revisions, _ITEM, ["item_id"])
_register(
    "document_vault_restore_revision",
    "Restore a Document Vault item to a prior revision.",
    document_vault_restore_revision,
    {**_ITEM, "revision": {"type": "integer"}},
    ["item_id", "revision"],
)
_register(
    "document_vault_import",
    "Import bytes into the Document Vault (content or content_base64).",
    document_vault_import,
    {
        "name": {"type": "string"},
        "content": {"type": "string"},
        "content_base64": {"type": "string"},
        "mime_type": {"type": "string"},
        **_PARENT,
    },
    ["name"],
)
_register(
    "document_vault_export",
    "Export a Document Vault item; classified exports require Soft Wall approval.",
    document_vault_export,
    {**_ITEM, "format": {"type": "string"}, **_APPROVAL},
    ["item_id"],
)
_register("document_vault_sync_status", "Show Google Drive sync status for the Document Vault.", document_vault_sync_status, {})
_register(
    "document_vault_sync_request",
    "Request Document Vault Google Drive sync (inbound or outbound).",
    document_vault_sync_request,
    {"direction": {"type": "string"}, "item_id": {"type": "string"}, "source": {"type": "string"}},
)
_register(
    "document_vault_conflict_resolve",
    "Resolve a Drive sync conflict (overwrite choices require Soft Wall).",
    document_vault_conflict_resolve,
    {**_ITEM, "choice": {"type": "string"}, **_APPROVAL},
    ["item_id", "choice"],
)
_register(
    "document_vault_bulk",
    "Bulk trash or permanent delete Document Vault items (Soft Wall).",
    document_vault_bulk,
    {"item_ids": {"type": "array", "items": {"type": "string"}}, "action": {"type": "string"}, **_APPROVAL},
    ["item_ids"],
)
_register(
    "document_vault_share",
    "Request external share of a Document Vault item (Soft Wall).",
    document_vault_share,
    {**_ITEM, "share_audience": {"type": "string"}, "permission": {"type": "string"}, **_APPROVAL},
    ["item_id"],
)

__all__ = [
    "TOOLSET",
    "document_vault_configured",
]
