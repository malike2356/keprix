"""Virtual message rendering for large histories."""

from __future__ import annotations

from keprix.tui.message_renderer import render_message
from keprix.tui.message_types import TuiMessage


def visible_slice(messages: list[TuiMessage], *, scroll_offset: int, viewport_height: int) -> tuple[int, list[TuiMessage]]:
    start = max(0, min(scroll_offset, len(messages)))
    end = max(start, min(len(messages), start + max(0, viewport_height)))
    return start, messages[start:end]


def render_visible(messages: list[TuiMessage], *, scroll_offset: int, viewport_height: int) -> list[str]:
    _, visible = visible_slice(messages, scroll_offset=scroll_offset, viewport_height=viewport_height)
    rendered: list[str] = []
    previous_role: str | None = None
    for message in visible:
        rendered.append(render_message(message, previous_role=previous_role))
        previous_role = message.role
    return rendered

