"""Verify all 10 personas have required engineered prompt sections."""

from __future__ import annotations

from keprix.personas.persona_prompts import ENGINEERED_PERSONA_PROMPTS

CORE_PERSONAS = (
    "NEXUS",
    "FORGE",
    "WARDEN",
    "SAGE",
    "BEACON",
    "PRISM",
    "COMPASS",
    "EMBER",
    "CODEX",
    "ECHO",
)

OPTIONAL_SECTIONS = (
    "## Domain Rules",
    "## Constraints",
)


def test_all_ten_personas_have_engineered_prompts() -> None:
    assert set(ENGINEERED_PERSONA_PROMPTS) == set(CORE_PERSONAS)


def test_each_persona_has_domain_or_constraints() -> None:
    for name in CORE_PERSONAS:
        prompt = ENGINEERED_PERSONA_PROMPTS[name]
        assert any(section in prompt for section in OPTIONAL_SECTIONS), (
            f"{name} should include domain rules or constraints"
        )


def test_nexus_roster_lists_specialists() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["NEXUS"]
    for specialist in ("FORGE", "WARDEN", "SAGE", "CODEX", "ECHO"):
        assert specialist in prompt
