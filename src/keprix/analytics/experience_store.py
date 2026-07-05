"""Analytics experience store."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Experience:
    request: str
    code: str
    outcome: str
    notes: list[str] = field(default_factory=list)


class ExperienceStore:
    def __init__(self) -> None:
        self._items: list[Experience] = []

    def add(self, experience: Experience) -> None:
        self._items.append(experience)

    def list(self) -> list[Experience]:
        return list(self._items)
