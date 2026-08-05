"""Help overlay content helpers."""

from __future__ import annotations

from keprix.tui.slash_registry import LOCAL_SLASH_COMMANDS


def render_help_overlay() -> str:
    rows = [
        "Keyboard",
        "Ctrl+P command palette",
        "Ctrl+Space command palette",
        "Ctrl+L transcript search",
        "Ctrl+S sessions",
        "Ctrl+M model picker",
        "Ctrl+R review mode",
        "Ctrl+Shift+R reconnect",
        "Ctrl+K send queued message",
        "Ctrl+C stop current reply",
        "Ctrl+G open editor",
        "? help",
        "Esc close overlays",
        "",
        "Slash commands",
    ]
    for command in LOCAL_SLASH_COMMANDS:
        rows.append(f"{command.names[0]} - {command.description}")
    return "\n".join(rows)
