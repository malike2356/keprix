"""Tests for persona registry."""

from __future__ import annotations

from keprix.personas.forge.persona import FORGE_PERSONA
from keprix.personas.nexus.persona import NEXUS_PERSONA
from keprix.personas.beacon.persona import BEACON_PERSONA
from keprix.personas.prism.persona import PRISM_PERSONA
from keprix.personas.compass.persona import COMPASS_PERSONA
from keprix.personas.ember.persona import EMBER_PERSONA
from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.extensions.scout.persona.persona import SCOUT_PERSONA
from keprix.personas.echo.persona import ECHO_PERSONA
from keprix.personas.sage.persona import SAGE_PERSONA
from keprix.personas.warden.persona import WARDEN_PERSONA
from keprix.personas.registry import PersonaRegistry, get_persona_registry


def test_registry_registers_nexus_singleton() -> None:
    registry = get_persona_registry()
    persona = registry.get("NEXUS")
    assert persona is not None
    assert persona.name == "NEXUS"
    assert persona.agent_type == "orchestrator"


def test_registry_list_personas_includes_nexus() -> None:
    registry = get_persona_registry()
    names = [row["name"] for row in registry.list_personas()]
    assert "NEXUS" in names
    assert "FORGE" in names
    assert "WARDEN" in names
    assert "SAGE" in names
    assert "BEACON" in names
    assert "PRISM" in names
    assert "COMPASS" in names
    assert "EMBER" in names
    assert "CODEX" in names
    assert "ECHO" in names


def test_persona_loads_system_prompt() -> None:
    prompt = NEXUS_PERSONA.system_prompt()
    assert "NEXUS" in prompt
    assert "FORGE" in prompt


def test_registry_loads_skill_packs() -> None:
    registry = PersonaRegistry()
    registry.register(NEXUS_PERSONA)
    packs = registry.load_skill_pack_content("NEXUS")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-orchestrator" in pack_names
    assert "project-tracking" in pack_names
    assert "status-reporting" in pack_names


def test_persona_to_dict_shape() -> None:
    data = NEXUS_PERSONA.to_dict()
    assert data["colour"] == "#DC2626"
    assert "keprix-core-orchestrator" in data["skill_packs"]


def test_forge_persona_registered() -> None:
    registry = get_persona_registry()
    forge = registry.get("FORGE")
    assert forge is not None
    assert forge.colour == "#16A34A"
    assert forge.agent_type == "technical"


def test_forge_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(FORGE_PERSONA)
    packs = registry.load_skill_pack_content("FORGE")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-developer" in pack_names
    assert "architecture-decision-records" in pack_names
    assert "ci-cd-pipeline" in pack_names


def test_warden_persona_registered() -> None:
    registry = get_persona_registry()
    warden = registry.get("WARDEN")
    assert warden is not None
    assert warden.colour == "#2563EB"
    assert warden.agent_type == "security"


def test_warden_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(WARDEN_PERSONA)
    packs = registry.load_skill_pack_content("WARDEN")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-security" in pack_names
    assert "dependency-scanner" in pack_names
    assert "config-hardener" in pack_names
    assert "privacy-scanner" in pack_names


def test_sage_persona_registered() -> None:
    registry = get_persona_registry()
    sage = registry.get("SAGE")
    assert sage is not None
    assert sage.colour == "#7C3AED"
    assert sage.agent_type == "research"


def test_sage_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(SAGE_PERSONA)
    packs = registry.load_skill_pack_content("SAGE")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-research" in pack_names
    assert "source-credibility" in pack_names
    assert "briefing-templates" in pack_names
    assert "market-intel" in pack_names


def test_beacon_persona_registered() -> None:
    registry = get_persona_registry()
    beacon = registry.get("BEACON")
    assert beacon is not None
    assert beacon.colour == "#CA8A04"
    assert beacon.agent_type == "marketing"


def test_beacon_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(BEACON_PERSONA)
    packs = registry.load_skill_pack_content("BEACON")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-marketing" in pack_names
    assert "brand-voice-manager" in pack_names
    assert "campaign-builder" in pack_names
    assert "copy-templates" in pack_names


def test_prism_persona_registered() -> None:
    registry = get_persona_registry()
    prism = registry.get("PRISM")
    assert prism is not None
    assert prism.colour == "#0D9488"
    assert prism.agent_type == "growth"


def test_prism_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(PRISM_PERSONA)
    packs = registry.load_skill_pack_content("PRISM")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-seo" in pack_names
    assert "keyword-research" in pack_names
    assert "content-optimisation" in pack_names
    assert "social-media-strategy" in pack_names


def test_compass_persona_registered() -> None:
    registry = get_persona_registry()
    compass = registry.get("COMPASS")
    assert compass is not None
    assert compass.colour == "#7C3AED"
    assert compass.agent_type == "strategy"


def test_compass_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(COMPASS_PERSONA)
    packs = registry.load_skill_pack_content("COMPASS")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-strategy" in pack_names
    assert "strategy-frameworks" in pack_names
    assert "decision-frameworks" in pack_names
    assert "scenario-planning" in pack_names


def test_ember_persona_registered() -> None:
    registry = get_persona_registry()
    ember = registry.get("EMBER")
    assert ember is not None
    assert ember.colour == "#EA580C"
    assert ember.agent_type == "wellbeing"


def test_ember_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(EMBER_PERSONA)
    packs = registry.load_skill_pack_content("EMBER")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-wellbeing" in pack_names
    assert "habit-tracker" in pack_names
    assert "wellbeing-checkin" in pack_names
    assert "coaching-frameworks" in pack_names


def test_codex_persona_registered() -> None:
    registry = get_persona_registry()
    codex = registry.get("CODEX")
    assert codex is not None
    assert codex.colour == "#4F46E5"
    assert codex.agent_type == "legal"


def test_codex_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(CODEX_PERSONA)
    packs = registry.load_skill_pack_content("CODEX")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-legal" in pack_names
    assert "contract-review" in pack_names
    assert "document-templates" in pack_names
    assert "regulatory-tracker" in pack_names
    assert "legal-uk" in pack_names


def test_scout_persona_registered(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_ACTIVE_EXTENSIONS", "scout")
    import keprix.personas.registry as registry_module

    registry_module._registry = None
    registry = get_persona_registry()
    scout = registry.get("SCOUT")
    assert scout is not None
    assert scout.colour == "#6B7280"
    assert scout.agent_type == "governance"
    registry_module._registry = None


def test_scout_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(SCOUT_PERSONA)
    packs = registry.load_skill_pack_content("SCOUT")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-governance" in pack_names
    assert "policy-enforcement" in pack_names
    assert "kill-switch-control" in pack_names
    assert "audit-streaming" in pack_names


def test_echo_persona_registered() -> None:
    registry = get_persona_registry()
    echo = registry.get("ECHO")
    assert echo is not None
    assert echo.colour == "#E11D48"
    assert echo.agent_type == "receptionist"


def test_echo_skill_packs_load() -> None:
    registry = PersonaRegistry()
    registry.register(ECHO_PERSONA)
    packs = registry.load_skill_pack_content("ECHO")
    pack_names = {row["name"] for row in packs}
    assert "keprix-core-receptionist" in pack_names
    assert "calendar-booking" in pack_names
    assert "business-faq" in pack_names
    assert "voice-presets" in pack_names
