"""Keprix TUI Command Center foundation."""

from keprix.tui.command_center.actions import CommandCenterAction
from keprix.tui.command_center.registry import CommandCenterRegistry, build_default_registry
from keprix.tui.command_center.state import CommandCenterState

__all__ = [
    "CommandCenterAction",
    "CommandCenterRegistry",
    "CommandCenterState",
    "build_default_registry",
]
