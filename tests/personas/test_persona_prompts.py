"""Tests for engineered persona prompts (Prompt 290)."""

from __future__ import annotations

import pytest

from keprix.personas.persona_prompts import ENGINEERED_PERSONA_PROMPTS, get_engineered_prompt
from keprix.personas.persona_prompts.codex import CODEX_SECTIONS
from keprix.personas.persona_prompts.forge import FORGE_SECTIONS
from keprix.personas.persona_prompts.sage import SAGE_SECTIONS
from keprix.personas.persona_prompts.echo import ECHO_SECTIONS
from keprix.personas.persona_prompts.warden import WARDEN_SECTIONS
from keprix.personas.prompt_template import PersonaPromptSections, build_persona_prompt
from keprix.personas.registry import get_persona_registry


REQUIRED_SECTIONS = (
    "## Identity",
    "## Capabilities",
    "## Tools",
    "## Execution Pattern",
    "## Output Expectations",
)


@pytest.mark.parametrize("name", sorted(ENGINEERED_PERSONA_PROMPTS))
def test_engineered_prompt_has_core_sections(name: str) -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS[name]
    for section in REQUIRED_SECTIONS:
        assert section in prompt, f"{name} missing {section}"


def test_registry_uses_engineered_prompts() -> None:
    registry = get_persona_registry()
    for name in ENGINEERED_PERSONA_PROMPTS:
        persona = registry.get(name)
        assert persona is not None
        assert persona.system_prompt() == get_engineered_prompt(name)


def test_forge_adopts_cursor_coding_pattern() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["FORGE"]
    assert "ponytail ladder" in prompt.lower()
    assert "file_tools.read_file" in prompt
    assert "Do not guess" in prompt


def test_codex_adopts_task_first_legal_pattern() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["CODEX"]
    assert "task-focused" in prompt.lower()
    assert "file_tools.read_file" in prompt
    assert "jurisdiction" in prompt.lower()


def test_sage_adopts_claude_code_research_pattern() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["SAGE"]
    assert "plan before acting" in prompt.lower()
    assert "UNDERSTAND" in prompt
    assert "executive summary" in prompt.lower()


def test_echo_adopts_notion_workspace_pattern() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["ECHO"]
    assert "workspace" in prompt.lower()
    assert "calendar" in prompt.lower()
    assert "quietly efficient" in prompt.lower()


def test_warden_adopts_fable_safety_pattern() -> None:
    prompt = ENGINEERED_PERSONA_PROMPTS["WARDEN"]
    assert "Never generate exploit code" in prompt
    assert "severity" in prompt.lower()
    assert "sceptical" in prompt.lower()


def test_empty_sections_are_omitted() -> None:
    minimal = PersonaPromptSections(identity_block="You are TEST.")
    prompt = build_persona_prompt(minimal)
    assert prompt == "## Identity\nYou are TEST."
    assert "## Capabilities" not in prompt
    assert "## Tools" not in prompt


def test_partial_tools_section_only_lists_present_fields() -> None:
    sections = PersonaPromptSections(
        identity_block="You are TEST.",
        primary_tools="alpha",
    )
    prompt = build_persona_prompt(sections)
    assert "- Primary tools: alpha" in prompt
    assert "Support tools" not in prompt
    assert "Never use" not in prompt


def test_section_objects_are_non_empty_for_flagship_personas() -> None:
    for sections in (FORGE_SECTIONS, SAGE_SECTIONS, ECHO_SECTIONS, WARDEN_SECTIONS, CODEX_SECTIONS):
        assert sections.identity_block.strip()
        assert sections.execution_pattern.strip()
        assert sections.output_expectations.strip()
