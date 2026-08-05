"""Product command registry.

Product modules register commands at the CLI edge. Core command dispatch can
read this registry without importing product command implementations directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


CommandHandler = Callable[..., object]


@dataclass(frozen=True)
class RegisteredCommand:
    name: str
    handler: CommandHandler
    product: str


_COMMANDS: dict[str, RegisteredCommand] = {}


def register_command(name: str, handler: CommandHandler, *, product: str) -> None:
    _COMMANDS[name] = RegisteredCommand(name=name, handler=handler, product=product)


def iter_commands() -> list[RegisteredCommand]:
    return list(_COMMANDS.values())


def clear_commands_for_tests() -> None:
    _COMMANDS.clear()

