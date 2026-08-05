"""Calendar tool wrappers."""

from __future__ import annotations

from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge


def gws_calendar_list(time_min: str | None = None, max_results: int = 10) -> dict[str, Any]:
    return GoogleWorkspaceBridge().calendar_list(time_min=time_min, max_results=max_results)


def gws_calendar_create(summary: str, start: str, end: str, attendees: list[str] | None = None, confirm: bool = False) -> dict[str, Any]:
    return GoogleWorkspaceBridge().calendar_create(summary=summary, start=start, end=end, attendees=attendees, confirm=confirm)
