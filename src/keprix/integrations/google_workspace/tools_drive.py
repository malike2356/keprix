"""Drive tool wrappers."""

from __future__ import annotations

from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge


def gws_drive_search(query: str, max_results: int = 10) -> dict[str, Any]:
    return GoogleWorkspaceBridge().drive_search(query=query, max_results=max_results)
