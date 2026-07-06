"""Shared action names for command palette, slash commands, and TUI."""

from __future__ import annotations

from typing import Any

ACTIONS: list[dict[str, Any]] = [
    {"id": "nav.launcher", "label": "Open launcher", "href": "/launcher", "surface": ["web", "mobile", "tui"]},
    {"id": "nav.chat", "label": "Open chat", "href": "/chat", "surface": ["web", "mobile", "tui"]},
    {"id": "nav.research", "label": "Start research", "href": "/research", "surface": ["web", "mobile"]},
    {"id": "nav.settings", "label": "Open settings", "href": "/settings", "surface": ["web", "mobile", "desktop"]},
    {"id": "job.retry", "label": "Retry job", "action": "retry", "surface": ["web", "mobile", "tui", "cli"]},
    {"id": "approval.approve", "label": "Approve", "action": "approve", "surface": ["web", "mobile", "tui", "cli", "chat"]},
    {"id": "approval.reject", "label": "Reject", "action": "reject", "surface": ["web", "mobile", "tui", "cli", "chat"]},
    {"id": "vault.unlock", "label": "Unlock vault", "href": "/vault", "surface": ["web", "mobile"]},
    {"id": "backup.create", "label": "Create backup", "href": "/admin/backup", "surface": ["web", "admin"]},
]


def actions_for_surface(surface: str) -> list[dict[str, Any]]:
    return [action for action in ACTIONS if surface in action.get("surface", [])]
