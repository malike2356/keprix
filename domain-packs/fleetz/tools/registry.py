"""Lightweight tool registry for the Fleetz domain pack sidecar."""

from __future__ import annotations

import json
from typing import Any, Callable

Handler = Callable[[dict[str, Any]], str]


class FleetzToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, name: str, handler: Handler) -> None:
        self._handlers[name] = handler

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        handler = self._handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown fleetz tool: {name}", "status": "error"})
        return handler(args)

    def tool_names(self) -> list[str]:
        return sorted(self._handlers)


registry = FleetzToolRegistry()
