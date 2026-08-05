"""Subagent runtime helpers."""

from keprix.tui.runtime.events import SubagentRuntimeEvent


def active_subagents(items: dict[str, SubagentRuntimeEvent]) -> list[SubagentRuntimeEvent]:
    return [item for item in items.values() if item.status == "running"]


__all__ = ["active_subagents"]
