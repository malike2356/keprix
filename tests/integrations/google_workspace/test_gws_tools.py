"""Google Workspace registered tool tests."""

from __future__ import annotations

import json

import keprix.tools.google_workspace_tools  # noqa: F401
from keprix.tools.registry import registry


def test_gws_tools_registered_and_confirm_gate() -> None:
    entry = registry.get_entry("gws_gmail_send")

    assert entry is not None
    assert entry.toolset == "google-workspace"
    payload = json.loads(entry.handler({"to": "a@example.com", "subject": "Hi", "body": "Draft"}))
    assert payload["requires_confirmation"] is True


def test_sheets_tool_schema_uses_range_name() -> None:
    entry = registry.get_entry("gws_sheets_read")

    assert entry is not None
    props = entry.schema["parameters"]["properties"]
    assert "spreadsheet_id" in props
    assert "range_name" in props
