"""Playbook edge definitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

EdgeCondition = Callable[[dict[str, Any]], bool | str]


class PlaybookEdge:
    """Directed edge between nodes, optionally gated by a condition."""

    def __init__(
        self,
        source: str,
        target: str,
        *,
        condition: EdgeCondition | None = None,
    ) -> None:
        self.source = source
        self.target = target
        self.condition = condition

    def resolve(self, state: dict[str, Any]) -> str | None:
        if self.condition is None:
            return self.target
        result = self.condition(state)
        if result is False or result is None:
            return None
        if result is True:
            return self.target
        return str(result)
