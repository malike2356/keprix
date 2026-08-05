"""Command registry exports."""

from keprix.tui.slash_registry import (
    COMMAND_OVERRIDES,
    LOCAL_SLASH_COMMANDS,
    canonical_local_command,
    is_local_slash_command,
    local_command_metadata,
    local_command_names,
    local_completion_candidates,
    local_completion_items,
    slash_command_description,
    slash_command_metadata,
)

__all__ = [
    "COMMAND_OVERRIDES",
    "LOCAL_SLASH_COMMANDS",
    "canonical_local_command",
    "is_local_slash_command",
    "local_command_metadata",
    "local_command_names",
    "local_completion_candidates",
    "local_completion_items",
    "slash_command_description",
    "slash_command_metadata",
]
