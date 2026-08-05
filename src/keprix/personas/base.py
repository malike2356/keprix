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
    guide_path: Path | None = None

    def resolve_guide_path(self) -> Path | None:
        if self.guide_path is not None:
            return self.guide_path if self.guide_path.exists() else None
        try:
            from keprix.agent.guide_enforcer import resolve_guide_path

            path = resolve_guide_path(self.name)
            return path if path.exists() else None
        except Exception:
            return None

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

    def guide_mandate(self) -> str:
        if self.resolve_guide_path() is None:
            return ""
        try:
            from keprix.agent.guide_enforcer import mandatory_guide_instruction

            return mandatory_guide_instruction(self.name)
        except Exception:
            rel = f"skills/personas/{self.name.lower()}/AGENT_GUIDE.md"
            return (
                f"**MANDATORY: Read {rel} before responding to ANY user message.** "
                "Do not act until you have read the routing guide."
            )

    def system_prompt(self) -> str:
        from keprix.personas.persona_prompts import get_engineered_prompt

        engineered = get_engineered_prompt(self.name)
        body = engineered if engineered else self.load_prompt("system.md")
        mandate = self.guide_mandate()
        if not mandate:
            return body
        stripped = body.lstrip()
        if stripped.startswith("**MANDATORY:"):
            return body
        return f"{mandate}\n\n{body}"

    def to_dict(self) -> dict[str, Any]:
        guide = self.resolve_guide_path()
        return {
            "name": self.name,
            "role": self.role,
            "tone": self.tone,
            "colour": self.colour,
            "agent_type": self.agent_type,
            "skill_packs": list(self.skill_packs),
            "guide_path": str(guide) if guide else None,
            "system_prompt": self.system_prompt(),
        }
