"""Inline tool card renderer."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from typing import Any

from keprix.tui.runtime_events import redact_mapping

SECRET_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization|cookie)(['\"]?\s*[:=]\s*['\"]?)[^\s,'\"]+"
)


@dataclass(frozen=True)
class ToolCard:
    name: str
    status: str = "running"
    args: dict[str, Any] = field(default_factory=dict)
    result_preview: str = ""
    error_preview: str = ""
    duration_ms: int = 0
    expanded: bool = False
    metadata_id: str = ""

    def toggle(self) -> "ToolCard":
        return replace(self, expanded=not self.expanded)


def redacted_text(value: str) -> str:
    return SECRET_VALUE_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}[redacted]", value)


def tool_card_from_runtime(
    *,
    name: str,
    status: str = "running",
    args: dict[str, Any] | None = None,
    result: str = "",
    error: str = "",
    duration_ms: int = 0,
    expanded: bool = False,
    metadata_id: str = "",
) -> ToolCard:
    return ToolCard(
        name=name or "tool",
        status=status or "running",
        args=redact_mapping(dict(args or {})),
        result_preview=redacted_text(result),
        error_preview=redacted_text(error),
        duration_ms=max(0, duration_ms),
        expanded=expanded,
        metadata_id=metadata_id,
    )


def render_tool_card(card: ToolCard, *, max_preview: int = 160) -> str:
    status = card.status
    duration = f" {card.duration_ms} ms" if card.duration_ms else ""
    metadata = f" #{card.metadata_id}" if card.metadata_id else ""
    args = _format_args(card.args)
    inline_args = f" {args}" if args else ""
    header = f"[{status}] {card.name}{inline_args}{duration}{metadata}"
    preview = card.error_preview if card.status == "error" else card.result_preview
    preview = redacted_text(preview)
    if not card.expanded and len(preview) > max_preview:
        preview = preview[:max_preview].rstrip() + " ... Show more"
    lines = [header]
    if args:
        lines.append(f"args: {args}")
    if preview:
        label = "error" if card.status == "error" else "result"
        lines.append(f"{label}: {preview}")
    lines.append("state: expanded" if card.expanded else "state: collapsed")
    return "\n".join(lines)


def _format_args(args: dict[str, Any]) -> str:
    if not args:
        return ""
    return ", ".join(f"{key}={value!r}" for key, value in sorted(args.items()))


__all__ = ["ToolCard", "redacted_text", "render_tool_card", "tool_card_from_runtime"]
