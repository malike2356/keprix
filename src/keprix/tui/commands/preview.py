"""Command preview rendering independent from dispatch."""

from keprix.tui.slash_registry import SlashCommandMetadata, slash_command_metadata


def command_preview(command_name: str) -> str:
    metadata = slash_command_metadata(command_name)
    if metadata is None:
        return ""
    return format_command_preview(metadata)


def format_command_preview(metadata: SlashCommandMetadata) -> str:
    usage = metadata.name
    if metadata.args:
        usage = f"{usage} {metadata.args}"
    aliases = f" aliases: {', '.join(metadata.aliases)}" if metadata.aliases else ""
    return f"{usage}: {metadata.description}{aliases}"


__all__ = ["command_preview", "format_command_preview"]
