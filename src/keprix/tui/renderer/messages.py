"""Message renderer exports."""

from dataclasses import dataclass

from keprix.tui.message_renderer import collapse_duplicates, render_message
from keprix.tui.message_types import TuiMessage
from keprix.tui.renderer.theme import KEPRIX_THEME_TOKENS


def render_tui_message(message: TuiMessage) -> str:
    return render_message(message)


@dataclass(frozen=True)
class RenderedMessageGroup:
    role: str
    body: str
    count: int


def group_messages(messages: list[TuiMessage]) -> list[RenderedMessageGroup]:
    groups: list[RenderedMessageGroup] = []
    current_role = ""
    current: list[str] = []
    for message in messages:
        if current and message.role != current_role:
            groups.append(RenderedMessageGroup(role=current_role, body="\n".join(current), count=len(current)))
            current = []
        current_role = message.role
        current.append(render_message(message, previous_role=current_role))
    if current:
        groups.append(RenderedMessageGroup(role=current_role, body="\n".join(current), count=len(current)))
    return groups


def render_message_with_theme(message: TuiMessage) -> str:
    style = {
        "error": KEPRIX_THEME_TOKENS["error"],
        "tool_call": KEPRIX_THEME_TOKENS["accent"],
        "tool_result": KEPRIX_THEME_TOKENS["muted"],
    }.get(message.role, KEPRIX_THEME_TOKENS["accent"])
    return f"[{style}]\n{render_message(message)}"


__all__ = [
    "RenderedMessageGroup",
    "collapse_duplicates",
    "group_messages",
    "render_message",
    "render_message_with_theme",
    "render_tui_message",
]
