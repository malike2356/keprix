"""Tests for persona leak-pattern audit registry."""

from __future__ import annotations

from keprix.personas.persona_audit import PERSONA_AUDIT, get_persona_audit, list_audited_personas

CORE_PERSONAS = (
    "nexus",
    "forge",
    "warden",
    "sage",
    "beacon",
    "prism",
    "compass",
    "ember",
    "codex",
    "echo",
)


def test_all_personas_have_audit_entries() -> None:
    assert set(list_audited_personas()) == set(CORE_PERSONAS)


def test_audit_entry_shape() -> None:
    for name in CORE_PERSONAS:
        entry = get_persona_audit(name)
        assert entry is not None
        assert entry["patterns_adopted"]
        assert isinstance(entry["missing"], list)
        assert entry["confidence"] in {"high", "medium", "low"}


def test_flagship_personas_have_high_confidence_patterns() -> None:
    for name in ("forge", "sage", "codex"):
        entry = get_persona_audit(name)
        assert entry is not None
        assert entry["confidence"] == "high"
        assert entry["patterns_adopted"]


def test_persona_audit_lookup_is_case_insensitive() -> None:
    assert get_persona_audit("FORGE") == get_persona_audit("forge")
