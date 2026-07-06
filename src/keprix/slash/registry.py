"""Shared slash command registry."""

from __future__ import annotations

from keprix.slash.schemas import SlashCommand, SlashContext, SlashResult


class SlashRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}

    def register(self, command: SlashCommand) -> None:
        key = command.name.lower()
        self._commands[key] = command
        for alias in command.aliases:
            self._commands[alias.lower()] = command

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name.lower())

    def names(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for command in self._commands.values():
            if command.name in seen:
                continue
            seen.add(command.name)
            out.append(command.name)
        return sorted(out)

    def list_for_role(self, role: str) -> list[SlashCommand]:
        from keprix.slash.permissions import role_allows

        seen: set[str] = set()
        allowed: list[SlashCommand] = []
        for command in self._commands.values():
            if command.name in seen:
                continue
            if role_allows(role, command.min_role):
                seen.add(command.name)
                allowed.append(command)
        return sorted(allowed, key=lambda item: item.name)


_registry: SlashRegistry | None = None


def get_slash_registry() -> SlashRegistry:
    global _registry
    if _registry is None:
        from keprix.slash.builtins import register_builtin_commands

        _registry = SlashRegistry()
        register_builtin_commands(_registry)
    return _registry
