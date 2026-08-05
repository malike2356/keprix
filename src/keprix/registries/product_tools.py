"""Product tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ToolFactory = Callable[[], object]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    factory: ToolFactory
    product: str


_TOOLS: dict[str, RegisteredTool] = {}


def register_tool(name: str, factory: ToolFactory, *, product: str) -> None:
    _TOOLS[name] = RegisteredTool(name=name, factory=factory, product=product)


def iter_tools() -> list[RegisteredTool]:
    return list(_TOOLS.values())


def clear_tools_for_tests() -> None:
    _TOOLS.clear()

