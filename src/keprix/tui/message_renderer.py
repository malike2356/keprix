"""Message rendering helpers for the Keprix terminal UI."""

from __future__ import annotations

import re
from pathlib import Path

from keprix.tui.message_types import TuiMessage
from keprix.tui.renderer.tool_cards import render_tool_card, tool_card_from_runtime

URL_RE = re.compile(r"https?://[^\s)]+")
PATH_RE = re.compile(r"(?<![:/\w])(?:~|/|\.\.?/)[^\s:]+")


def render_message(message: TuiMessage, *, previous_role: str | None = None, max_tool_result: int = 500) -> str:
    """Render a message with role indicator, timestamp, metadata, and links."""
    parts: list[str] = []
    if previous_role and previous_role != message.role:
        parts.append("")
    prefix = _role_prefix(message)
    stamp = message.timestamp.strftime("%H:%M:%S")
    header = f"{prefix} [{stamp}]"
    meta = _metadata(message)
    if meta:
        header = f"{header} {meta}"
    parts.append(header)
    if message.tool is not None:
        parts.append(_render_tool(message, max_tool_result=max_tool_result))
    if message.content:
        parts.append(_linkify(message.content))
    return "\n".join(parts).strip()


def collapse_duplicates(rendered_messages: list[str]) -> list[str]:
    collapsed: list[str] = []
    last = None
    count = 0
    for message in rendered_messages:
        if message == last:
            count += 1
            continue
        if last is not None:
            collapsed.append(_duplicate_suffix(last, count))
        last = message
        count = 1
    if last is not None:
        collapsed.append(_duplicate_suffix(last, count))
    return collapsed


def _duplicate_suffix(message: str, count: int) -> str:
    if count <= 1:
        return message
    return f"{message}\n[{count} duplicates]"


def _role_prefix(message: TuiMessage) -> str:
    return {
        "user": "> user",
        "assistant": "keprix",
        "tool_call": "tool",
        "tool_result": "tool result",
        "error": "error",
        "system": "system",
    }.get(message.role, message.role)


def _metadata(message: TuiMessage) -> str:
    bits: list[str] = []
    if message.model:
        bits.append(message.model)
    if message.token_count is not None:
        bits.append(f"{message.token_count} tok")
    if message.latency_ms is not None:
        bits.append(f"{message.latency_ms} ms")
    return f"({' | '.join(bits)})" if bits else ""


def _render_tool(message: TuiMessage, *, max_tool_result: int) -> str:
    assert message.tool is not None
    card = tool_card_from_runtime(
        name=message.tool.name,
        status=message.tool.status,
        args=message.tool.args,
        result=message.tool.result,
        error=message.tool.result if message.tool.status == "error" else "",
        duration_ms=message.latency_ms or 0,
        expanded=bool(message.metadata.get("expanded_tool")),
        metadata_id=str(message.metadata.get("id") or ""),
    )
    return render_tool_card(card, max_preview=max_tool_result)


def _linkify(text: str) -> str:
    text = URL_RE.sub(lambda match: f"<{match.group(0)}>", text)
    return PATH_RE.sub(lambda match: _format_path(match.group(0)), text)


def _format_path(value: str) -> str:
    expanded = Path(value).expanduser()
    return f"[file:{expanded}]"
