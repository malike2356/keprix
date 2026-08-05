"""Gmail tool wrappers."""

from __future__ import annotations

from typing import Any

from keprix.integrations.google_workspace.bridge import GoogleWorkspaceBridge


def gws_gmail_list(query: str = "", max_results: int = 10) -> dict[str, Any]:
    return GoogleWorkspaceBridge().gmail_list(query=query, max_results=max_results)


def gws_gmail_send(to: str, subject: str, body: str, confirm: bool = False) -> dict[str, Any]:
    return GoogleWorkspaceBridge().gmail_send(to=to, subject=subject, body=body, confirm=confirm)
