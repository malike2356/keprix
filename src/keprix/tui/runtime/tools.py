"""Tool runtime helpers."""

from keprix.tui.runtime.events import ToolRuntimeEvent


def running_tools(tools: list[ToolRuntimeEvent]) -> list[ToolRuntimeEvent]:
    return [tool for tool in tools if tool.status == "running"]


__all__ = ["running_tools"]
