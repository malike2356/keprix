"""Slash command package boundaries for the Keprix TUI."""

from keprix.tui.commands.completion import complete_local_commands
from keprix.tui.commands.preview import command_preview
from keprix.tui.commands.schema import SlashCommandMetadata, SlashCompletionItem

__all__ = [
    "SlashCommandMetadata",
    "SlashCompletionItem",
    "command_preview",
    "complete_local_commands",
]
