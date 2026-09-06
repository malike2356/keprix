"""First-class worker tools for contacts, notes, and property capability status."""

from __future__ import annotations

import json
from typing import Any

from keprix.crm.store import get_crm_store
from keprix.document_vault.service import get_document_vault_service
from keprix.tools.registry import registry


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def _ws(args: dict[str, Any]) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        raise ValueError("workspace_id is required")
    return workspace_id


def _contact_tool(args: dict[str, Any]) -> str:
    try:
        ws = _ws(args)
        store = get_crm_store()
        action = str(args.get("action") or "list")
        if action == "list":
            return _json({"items": store.list_contacts(ws, limit=min(200, int(args.get("limit") or 50)))})
        contact_id = str(args.get("contact_id") or "")
        if action == "get":
            return _json({"item": store.get_contact(ws, contact_id)})
        if action == "create":
            return _json({"item": store.create_contact(ws, str(args.get("display_name") or "Untitled contact"), actor_type="worker", actor_id=str(args.get("actor_id") or "worker"), emails=args.get("emails") or [], phones=args.get("phones") or [])})
        if action == "update":
            return _json({"item": store.update_contact(ws, contact_id, actor_type="worker", actor_id=str(args.get("actor_id") or "worker"), **dict(args.get("fields") or {}))})
        if action == "delete":
            return _json({"item": store.delete_contact(ws, contact_id), "status": "deleted"})
        return _json({"error": "unsupported contact action"})
    except Exception as exc:
        return _json({"error": str(exc)})


def _note_tool(args: dict[str, Any]) -> str:
    try:
        ws = _ws(args)
        service = get_document_vault_service()
        action = str(args.get("action") or "list")
        if action == "list":
            return _json({"items": [item for item in service.store.list_items(ws, limit=200).get("items", []) if item.get("kind") in {"markdown", "plain_text"}]})
        item_id = str(args.get("item_id") or "")
        if action == "create":
            return _json({"item": service.create_text_item(ws, str(args.get("name") or "Note"), str(args.get("content") or ""), kind="markdown", actor_id=str(args.get("actor_id") or "worker"))})
        if action == "update":
            return _json({"item": service.write_content(ws, item_id, str(args.get("content") or "").encode(), actor_id=str(args.get("actor_id") or "worker"))})
        if action == "delete":
            return _json({"item": service.store.trash(ws, item_id, actor_id=str(args.get("actor_id") or "worker")), "status": "deleted"})
        return _json({"error": "unsupported note action"})
    except Exception as exc:
        return _json({"error": str(exc)})


def _property_tool(args: dict[str, Any]) -> str:
    return _json({"status": "not_configured", "capability": str(args.get("capability") or "property"), "message": "Property backend is not installed yet; no property action was performed."})


def _register(name: str, description: str, handler: Any, properties: dict[str, Any]) -> None:
    registry.register(name=name, toolset="worker", schema={"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": ["workspace_id"]}}, handler=handler)


_register("worker_contacts", "Workspace-scoped contact list/get/create/update/delete.", _contact_tool, {"workspace_id": {"type": "string"}, "action": {"type": "string"}, "contact_id": {"type": "string"}, "display_name": {"type": "string"}, "fields": {"type": "object"}, "emails": {"type": "array"}, "phones": {"type": "array"}})
_register("worker_notes", "Workspace-scoped Document Vault notes list/create/update/delete.", _note_tool, {"workspace_id": {"type": "string"}, "action": {"type": "string"}, "item_id": {"type": "string"}, "name": {"type": "string"}, "content": {"type": "string"}})
for _name in ("property_due_diligence", "property_floor_plan_analyze", "property_saved_search_run", "property_calculator_run"):
    _register(_name, "Property capability; returns not_configured until the canonical property backend is available.", _property_tool, {"workspace_id": {"type": "string"}, "capability": {"type": "string"}})
