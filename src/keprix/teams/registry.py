"""Registry for reusable teams."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.teams.crew import Crew
from keprix.teams.flow import TeamFlow


@dataclass(slots=True)
class RegisteredTeam:
    crew: Crew
    flow: TeamFlow


class TeamRegistry:
    def __init__(self) -> None:
        self._items: dict[str, RegisteredTeam] = {}

    def register(self, crew: Crew, flow: TeamFlow) -> None:
        self._items[crew.name] = RegisteredTeam(crew=crew, flow=flow)

    def get(self, name: str) -> RegisteredTeam | None:
        return self._items.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._items)


team_registry = TeamRegistry()
