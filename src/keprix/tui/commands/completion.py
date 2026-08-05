"""Command completion logic independent from rendering."""

from keprix.tui.slash_registry import SlashCompletionItem, local_completion_items


def complete_local_commands(prefix: str, *, limit: int | None = None) -> list[SlashCompletionItem]:
    items = local_completion_items(prefix)
    return items if limit is None else items[:limit]


def complete_local_command_actions(prefix: str, *, limit: int | None = None) -> list[str]:
    return [item.command for item in complete_local_commands(prefix, limit=limit)]


__all__ = ["complete_local_command_actions", "complete_local_commands"]
