"""Unified persona prompt template (Prompt 290)."""

from __future__ import annotations

from dataclasses import dataclass, field


PERSONA_TEMPLATE = """\
## Identity
{identity_block}

## Capabilities
{capabilities_block}

## Tools
- Primary tools: {primary_tools}
- Support tools: {support_tools}
- Never use: {forbidden_tools}

## Execution Pattern
{execution_pattern}

## Output Expectations
{output_expectations}

## Domain Rules
{domain_rules}

## Constraints
{constraints}
"""


@dataclass(slots=True)
class PersonaPromptSections:
    """Structured persona prompt sections. Empty sections are omitted."""

    identity_block: str = ""
    capabilities_block: str = ""
    primary_tools: str = ""
    support_tools: str = ""
    forbidden_tools: str = ""
    execution_pattern: str = ""
    output_expectations: str = ""
    domain_rules: str = ""
    constraints: str = ""


_SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("identity_block", "## Identity"),
    ("capabilities_block", "## Capabilities"),
    ("execution_pattern", "## Execution Pattern"),
    ("output_expectations", "## Output Expectations"),
    ("domain_rules", "## Domain Rules"),
    ("constraints", "## Constraints"),
)


def _has_tools(sections: PersonaPromptSections) -> bool:
    return bool(
        sections.primary_tools.strip()
        or sections.support_tools.strip()
        or sections.forbidden_tools.strip()
    )


def build_persona_prompt(sections: PersonaPromptSections) -> str:
    """Render persona prompt, skipping empty sections."""
    parts: list[str] = []

    for field_name, heading in _SECTION_ORDER:
        value = getattr(sections, field_name, "").strip()
        if value:
            parts.append(f"{heading}\n{value}")

    if _has_tools(sections):
        tools_lines = ["## Tools"]
        if sections.primary_tools.strip():
            tools_lines.append(f"- Primary tools: {sections.primary_tools.strip()}")
        if sections.support_tools.strip():
            tools_lines.append(f"- Support tools: {sections.support_tools.strip()}")
        if sections.forbidden_tools.strip():
            tools_lines.append(f"- Never use: {sections.forbidden_tools.strip()}")
        insert_at = 2 if sections.capabilities_block.strip() else 1
        if sections.identity_block.strip():
            insert_at = min(insert_at, len(parts))
        parts.insert(insert_at, "\n".join(tools_lines))

    return "\n\n".join(parts).strip()
