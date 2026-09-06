"""Google Workspace tool registrations."""

from __future__ import annotations

import json
from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceError
from keprix.integrations.google_workspace.tools_calendar import gws_calendar_create, gws_calendar_list
from keprix.integrations.google_workspace.tools_drive import gws_drive_search
from keprix.integrations.google_workspace.tools_gmail import gws_gmail_list, gws_gmail_send
from keprix.integrations.google_workspace.tools_sheets import gws_sheets_read
from keprix.integrations.google_workspace.tools_docs import gws_docs_create, gws_docs_update
from keprix.integrations.google_workspace.tools_slides import gws_slides_create
from keprix.integrations.google_workspace.tools_contacts import gws_contacts_enrich, gws_contacts_list
from keprix.integrations.google_workspace.vault_export import create_doc_from_vault, create_slides_from_vault
from keprix.tools.registry import registry

TOOLSET = "google-workspace"


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}


def _json_handler(fn):
    def _inner(args: dict[str, Any], **_kwargs: Any) -> str:
        try:
            return json.dumps(fn(**args))
        except GoogleWorkspaceError as exc:
            return json.dumps({"error": str(exc), "connected": False})

    return _inner


registry.register(
    name="gws_gmail_list",
    toolset=TOOLSET,
    schema=_schema("gws_gmail_list", "List or search Gmail messages through the Google Workspace connector.", {"query": {"type": "string", "default": ""}, "max_results": {"type": "number", "default": 10}}, []),
    handler=_json_handler(gws_gmail_list),
)

registry.register(
    name="gws_gmail_send",
    toolset=TOOLSET,
    schema=_schema("gws_gmail_send", "Send a Gmail message. Requires confirm=true.", {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "confirm": {"type": "boolean", "default": False}}, ["to", "subject", "body"]),
    handler=_json_handler(gws_gmail_send),
)

registry.register(
    name="gws_calendar_list",
    toolset=TOOLSET,
    schema=_schema("gws_calendar_list", "List upcoming Google Calendar events.", {"time_min": {"type": "string"}, "max_results": {"type": "number", "default": 10}}, []),
    handler=_json_handler(gws_calendar_list),
)

registry.register(
    name="gws_calendar_create",
    toolset=TOOLSET,
    schema=_schema("gws_calendar_create", "Create a Google Calendar event. Requires confirm=true.", {"summary": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}, "attendees": {"type": "array", "items": {"type": "string"}}, "confirm": {"type": "boolean", "default": False}}, ["summary", "start", "end"]),
    handler=_json_handler(gws_calendar_create),
)

registry.register(
    name="gws_drive_search",
    toolset=TOOLSET,
    schema=_schema("gws_drive_search", "Search Google Drive files.", {"query": {"type": "string"}, "max_results": {"type": "number", "default": 10}}, ["query"]),
    handler=_json_handler(gws_drive_search),
)

registry.register(
    name="gws_sheets_read",
    toolset=TOOLSET,
    schema=_schema("gws_sheets_read", "Read a range from a Google Sheet.", {"spreadsheet_id": {"type": "string"}, "range_name": {"type": "string", "default": "Sheet1!A1:Z100"}}, ["spreadsheet_id", "range_name"]),
    handler=_json_handler(gws_sheets_read),
)

registry.register(name="gws_docs_create", toolset=TOOLSET, schema=_schema("gws_docs_create", "Create a Google Doc. Requires confirm=true.", {"title": {"type": "string"}, "text": {"type": "string"}, "confirm": {"type": "boolean"}}, ["title"]), handler=_json_handler(gws_docs_create))
registry.register(name="gws_docs_update", toolset=TOOLSET, schema=_schema("gws_docs_update", "Replace or append Google Doc text. Requires confirm=true.", {"document_id": {"type": "string"}, "text": {"type": "string"}, "replace": {"type": "boolean"}, "confirm": {"type": "boolean"}}, ["document_id", "text"]), handler=_json_handler(gws_docs_update))
registry.register(name="gws_slides_create", toolset=TOOLSET, schema=_schema("gws_slides_create", "Create a Google Slides deck. Requires confirm=true.", {"title": {"type": "string"}, "slides": {"type": "array", "items": {"type": "string"}}, "confirm": {"type": "boolean"}}, ["title"]), handler=_json_handler(gws_slides_create))
registry.register(name="gws_contacts_list", toolset=TOOLSET, schema=_schema("gws_contacts_list", "List Google Contacts.", {"query": {"type": "string"}, "max_results": {"type": "number"}}, []), handler=_json_handler(gws_contacts_list))
registry.register(name="gws_contacts_enrich", toolset=TOOLSET, schema=_schema("gws_contacts_enrich", "Fill empty CRM lead fields from a matching Google Contact.", {"workspace_id": {"type": "string"}, "lead_id": {"type": "string"}, "query": {"type": "string"}, "actor_id": {"type": "string"}}, ["workspace_id", "lead_id", "query"]), handler=_json_handler(gws_contacts_enrich))
registry.register(name="gws_doc_from_vault", toolset=TOOLSET, schema=_schema("gws_doc_from_vault", "Create a Google Doc from a Document Vault item. Requires confirm=true.", {"workspace_id": {"type": "string"}, "item_id": {"type": "string"}, "actor_id": {"type": "string"}, "confirm": {"type": "boolean"}}, ["workspace_id", "item_id"]), handler=_json_handler(create_doc_from_vault))
registry.register(name="gws_slides_from_vault", toolset=TOOLSET, schema=_schema("gws_slides_from_vault", "Create Google Slides from a Document Vault item. Requires confirm=true.", {"workspace_id": {"type": "string"}, "item_id": {"type": "string"}, "actor_id": {"type": "string"}, "confirm": {"type": "boolean"}}, ["workspace_id", "item_id"]), handler=_json_handler(create_slides_from_vault))
