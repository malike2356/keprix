"""Skills hub state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkillItem:
    name: str
    description: str = ""
    installed: bool = False
    enabled: bool = False
    source: str = ""


class SkillsHubState:
    def __init__(self, skills: list[SkillItem] | None = None) -> None:
        self.skills = list(skills or [])

    def search(self, query: str) -> list[SkillItem]:
        needle = query.lower().strip()
        return [skill for skill in self.skills if not needle or needle in skill.name.lower() or needle in skill.description.lower()]

    def set_enabled(self, name: str, enabled: bool) -> None:
        for skill in self.skills:
            if skill.name == name:
                skill.enabled = enabled
                return
        raise KeyError(name)

