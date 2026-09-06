"""Agent-facing contact tools."""

from __future__ import annotations

from typing import Any

from keprix.tools.registry import registry

from keprix.contacts.search import (
    contact_get,
    contact_get_primary_email,
    contact_get_primary_phone,
    contact_search,
)

__all__ = [
    "contact_search",
    "contact_get",
    "contact_get_primary_email",
    "contact_get_primary_phone",
]


def _run(coro):
    from keprix.model_tools import _run_async
    return _run_async(coro)


async def contact_search_tool(query: str, limit: int = 5) -> list[dict[str, Any]]:
    return await contact_search(query, limit=limit)


def _user(args: dict[str, Any]) -> str:
    return str(args.get("user_id") or args.get("workspace_id") or "local")


def contact_list_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    rows = _run(get_contact_store().list_contacts(user_id=_user(args), query=args.get("query"), limit=max(1, min(int(args.get("limit") or 100), 500))))
    return json.dumps([row.to_dict() for row in rows], default=str)


def contact_get_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    row = _run(get_contact_store().get(str(args.get("contact_id") or ""), user_id=_user(args)))
    return json.dumps(row.to_dict() if row else {"status": "not_found"}, default=str)


def contact_create_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    data = {key: args[key] for key in ("display_name", "given_name", "family_name", "emails", "phones", "addresses", "organisation", "job_title", "notes") if key in args}
    if not str(data.get("display_name") or "").strip():
        return json.dumps({"status": "invalid", "reason": "display_name is required"})
    row = _run(get_contact_store().create(data, user_id=_user(args)))
    return json.dumps(row.to_dict(), default=str)


def contact_update_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    updates = {key: args[key] for key in ("display_name", "given_name", "family_name", "emails", "phones", "addresses", "organisation", "job_title", "notes") if key in args}
    row = _run(get_contact_store().update(str(args.get("contact_id") or ""), updates, user_id=_user(args)))
    return json.dumps(row.to_dict() if row else {"status": "not_found_or_read_only"}, default=str)


def contact_delete_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    ok = _run(get_contact_store().delete(str(args.get("contact_id") or ""), user_id=_user(args)))
    return json.dumps({"ok": bool(ok), "status": "deleted" if ok else "not_found_or_read_only"})


def contact_enrich_tool(args: dict[str, Any]) -> str:
    import json
    from keprix.contacts.store import get_contact_store
    store = get_contact_store()
    contact_id = str(args.get("contact_id") or "")
    current = _run(store.get(contact_id, user_id=_user(args)))
    if current is None:
        return json.dumps({"status": "not_found"})
    allowed = ("organisation", "job_title", "notes", "photo_url")
    updates = {key: args[key] for key in allowed if args.get(key) and not getattr(current, key)}
    row = _run(store.update(contact_id, updates, user_id=_user(args))) if updates else current
    return json.dumps({"updated_fields": sorted(updates), "contact": row.to_dict() if row else None}, default=str)


_CONTACT_SCHEMA = {"type": "object", "properties": {"user_id": {"type": "string"}, "workspace_id": {"type": "string"}}}
registry.register(name="contact_list", toolset="contacts", schema={"name": "contact_list", "description": "List workspace-scoped contacts.", "parameters": _CONTACT_SCHEMA}, handler=contact_list_tool)
registry.register(name="contact_get", toolset="contacts", schema={"name": "contact_get", "description": "Get one workspace-scoped contact.", "parameters": {"type": "object", "properties": {**_CONTACT_SCHEMA["properties"], "contact_id": {"type": "string"}}, "required": ["contact_id"]}}, handler=contact_get_tool)
registry.register(name="contact_create", toolset="contacts", schema={"name": "contact_create", "description": "Create a manual workspace contact.", "parameters": {"type": "object", "properties": {**_CONTACT_SCHEMA["properties"], "display_name": {"type": "string"}, "emails": {"type": "array"}, "phones": {"type": "array"}, "organisation": {"type": "string"}}, "required": ["display_name"]}}, handler=contact_create_tool)
registry.register(name="contact_update", toolset="contacts", schema={"name": "contact_update", "description": "Update a manual workspace contact.", "parameters": {"type": "object", "properties": {**_CONTACT_SCHEMA["properties"], "contact_id": {"type": "string"}, "display_name": {"type": "string"}, "notes": {"type": "string"}}, "required": ["contact_id"]}}, handler=contact_update_tool)
registry.register(name="contact_delete", toolset="contacts", schema={"name": "contact_delete", "description": "Delete a manual workspace contact.", "parameters": {"type": "object", "properties": {**_CONTACT_SCHEMA["properties"], "contact_id": {"type": "string"}}, "required": ["contact_id"]}}, handler=contact_delete_tool)
registry.register(name="contact_enrich", toolset="contacts", schema={"name": "contact_enrich", "description": "Fill empty contact fields without overwriting existing data.", "parameters": {"type": "object", "properties": {**_CONTACT_SCHEMA["properties"], "contact_id": {"type": "string"}, "organisation": {"type": "string"}, "job_title": {"type": "string"}, "notes": {"type": "string"}}, "required": ["contact_id"]}}, handler=contact_enrich_tool)
