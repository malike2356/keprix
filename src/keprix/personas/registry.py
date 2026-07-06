"""Persona registry and skill-pack loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.personas.base import KeprixPersona
from keprix.personas.forge.persona import FORGE_PERSONA
from keprix.personas.nexus.persona import NEXUS_PERSONA
from keprix.personas.warden.persona import WARDEN_PERSONA
from keprix.personas.sage.persona import SAGE_PERSONA
from keprix.personas.beacon.persona import BEACON_PERSONA
from keprix.personas.prism.persona import PRISM_PERSONA
from keprix.personas.compass.persona import COMPASS_PERSONA
from keprix.personas.ember.persona import EMBER_PERSONA
from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.personas.echo.persona import ECHO_PERSONA


def _active_extension_names() -> list[str]:
    import os

    raw = os.environ.get("KEPRIX_ACTIVE_EXTENSIONS", "").strip()
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def _register_extension_personas(registry: PersonaRegistry) -> None:
    if "scout" not in _active_extension_names():
        return
    from keprix.extensions.scout.persona.persona import SCOUT_PERSONA

    registry.register(SCOUT_PERSONA)


class PersonaRegistry:
    def __init__(self) -> None:
        self._personas: dict[str, KeprixPersona] = {}

    def register(self, persona: KeprixPersona) -> None:
        self._personas[persona.name.upper()] = persona

    def get(self, name: str) -> KeprixPersona | None:
        return self._personas.get(name.upper())

    def list_personas(self) -> list[dict[str, Any]]:
        return [persona.to_dict() for persona in sorted(self._personas.values(), key=lambda p: p.name)]

    def list_names(self) -> list[str]:
        return sorted(self._personas)

    def load_skill_pack_paths(self, persona_name: str) -> list[Path]:
        persona = self.get(persona_name)
        if persona is None:
            return []
        skills_root = Path(__file__).resolve().parents[1] / "skills"
        paths: list[Path] = []
        for pack_name in persona.skill_packs:
            for match in skills_root.rglob("SKILL.md"):
                if match.parent.name == pack_name:
                    paths.append(match)
                    break
        return paths

    def load_skill_pack_content(self, persona_name: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for path in self.load_skill_pack_paths(persona_name):
            rows.append(
                {
                    "name": path.parent.name,
                    "path": str(path),
                    "content": path.read_text(encoding="utf-8"),
                }
            )
        return rows


_registry: PersonaRegistry | None = None


def get_persona_registry() -> PersonaRegistry:
    global _registry
    if _registry is None:
        _registry = PersonaRegistry()
        _registry.register(NEXUS_PERSONA)
        _registry.register(FORGE_PERSONA)
        _registry.register(WARDEN_PERSONA)
        _registry.register(SAGE_PERSONA)
        _registry.register(BEACON_PERSONA)
        _registry.register(PRISM_PERSONA)
        _registry.register(COMPASS_PERSONA)
        _registry.register(EMBER_PERSONA)
        _registry.register(CODEX_PERSONA)
        _register_extension_personas(_registry)
        _registry.register(ECHO_PERSONA)
    return _registry
