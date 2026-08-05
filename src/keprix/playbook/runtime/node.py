"""Playbook node definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

NodeHandler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


class PlaybookNode:
    """A single step in a playbook graph."""

    def __init__(
        self,
        name: str,
        handler: NodeHandler,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.handler = handler
        self.metadata = metadata or {}

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        result = self.handler(state)
        if hasattr(result, "__await__"):
            result = await result
        if not isinstance(result, dict):
            raise TypeError(f"Node '{self.name}' must return a dict, got {type(result)!r}")
        return result
