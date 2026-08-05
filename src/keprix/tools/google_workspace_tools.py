"""Google Workspace tool registrations."""

from __future__ import annotations

import json
from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceError
from keprix.integrations.google_workspace.tools_calendar import gws_calendar_create, gws_calendar_list
from keprix.integrations.google_workspace.tools_drive import gws_drive_search
from keprix.integrations.google_workspace.tools_gmail import gws_gmail_list, gws_gmail_send
from keprix.integrations.google_workspace.tools_sheets import gws_sheets_read
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
