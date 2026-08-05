"""Sheets tool wrappers."""

from __future__ import annotations

from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge


def gws_sheets_read(spreadsheet_id: str, range_name: str) -> dict[str, Any]:
    return GoogleWorkspaceBridge().sheets_read(spreadsheet_id=spreadsheet_id, range_name=range_name)
