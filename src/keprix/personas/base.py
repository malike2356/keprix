"""Base persona class for Keprix specialist agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class KeprixPersona:
    name: str
    role: str
    tone: str
    colour: str
    agent_type: str
    skill_packs: list[str] = field(default_factory=list)
    prompts_dir: Path | None = None

    def prompt_path(self, filename: str) -> Path | None:
        if self.prompts_dir is None:
            return None
        candidate = self.prompts_dir / filename
        return candidate if candidate.exists() else None

    def load_prompt(self, filename: str, *, fallback: str = "") -> str:
        path = self.prompt_path(filename)
        if path is None:
            return fallback
        return path.read_text(encoding="utf-8")

    def system_prompt(self) -> str:
        return self.load_prompt("system.md")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "tone": self.tone,
            "colour": self.colour,
            "agent_type": self.agent_type,
            "skill_packs": list(self.skill_packs),
            "system_prompt": self.system_prompt(),
        }
