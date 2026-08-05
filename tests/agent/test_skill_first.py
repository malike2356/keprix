"""Tests for skill-first execution gate (Prompt 292)."""

from __future__ import annotations

import json
from types import SimpleNamespace

from keprix.agent.skill_first import (
    SkillFirstAction,
    SkillFirstGate,
    apply_skill_first_gate,
    record_after_skill_view,
)
from keprix.agent.layers.execution import EXECUTION_LAYER


_CATALOG = [
    {
        "name": "pptx",
        "description": "Create PowerPoint presentations and slides",
        "category": "documents",
        "triggers": ["pptx", "powerpoint", "slides"],
    },
    {
        "name": "docx",
        "description": "Create Word documents",
        "category": "documents",
        "triggers": ["docx", "word"],
    },
    {
        "name": "pdf",
        "description": "Create and edit PDF files",
        "category": "documents",
        "triggers": ["pdf"],
    },
]


def test_execution_layer_includes_skill_first_clause() -> None:
    assert "Skill-first contract" in EXECUTION_LAYER
    assert "skill_view" in EXECUTION_LAYER
    assert "defect, not an optimization" in EXECUTION_LAYER


def test_soft_tools_are_never_gated() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    for tool in ("web_search", "memory", "clarify", "todo", "skill_view"):
        decision = gate.before_tool(tool, {"query": "pptx slides"})
        assert decision.allows_execution
        assert decision.action in (SkillFirstAction.ALLOW, SkillFirstAction.BYPASS)


def test_write_pptx_blocked_until_skill_viewed() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    decision = gate.before_tool("write_file", {"path": "deck.pptx"})
    assert decision.action == SkillFirstAction.REQUIRE_SKILL_READ
    assert "pptx" in decision.required_skills
    assert "skill_view" in decision.message

    gate.record_skill_view("pptx")
    allowed = gate.before_tool("write_file", {"path": "deck.pptx"})
    assert allowed.allows_execution
    assert allowed.action == SkillFirstAction.ALLOW


def test_docx_and_pdf_paths_match() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    docx = gate.before_tool("write_file", {"path": "report.docx"})
    assert docx.action == SkillFirstAction.REQUIRE_SKILL_READ
    assert "docx" in docx.required_skills

    pdf = gate.before_tool("patch", {"path": "/tmp/out.pdf"})
    assert pdf.action == SkillFirstAction.REQUIRE_SKILL_READ
    assert "pdf" in pdf.required_skills


def test_execute_code_and_computer_use_gated_when_matched() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    code = gate.before_tool("execute_code", {"code": "build a pptx deck"})
    assert code.action == SkillFirstAction.REQUIRE_SKILL_READ

    computer = gate.before_tool("computer_use", {"prompt": "export slides to pptx"})
    assert computer.action == SkillFirstAction.REQUIRE_SKILL_READ


def test_no_match_allows_gated_tool() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    decision = gate.before_tool("terminal", {"command": "ls -la"})
    assert decision.allows_execution


def test_permissive_warn_once_then_allows() -> None:
    gate = SkillFirstGate(profile="permissive", skill_catalog=_CATALOG)
    first = gate.before_tool("write_file", {"path": "deck.pptx"})
    assert first.action == SkillFirstAction.BYPASS
    assert first.reason == "permissive_warn_once"

    second = gate.before_tool("write_file", {"path": "deck.pptx"})
    assert second.action == SkillFirstAction.BYPASS
    assert second.reason == "permissive_already_warned"


def test_multiple_matched_skills_all_required() -> None:
    catalog = _CATALOG + [
        {
            "name": "slides-brand",
            "description": "Brand rules for powerpoint slides and pptx decks",
            "category": "documents",
            "triggers": ["pptx", "slides", "brand"],
        }
    ]
    gate = SkillFirstGate(profile="standard", skill_catalog=catalog)
    decision = gate.before_tool("write_file", {"path": "branded-deck.pptx"})
    assert decision.action == SkillFirstAction.REQUIRE_SKILL_READ
    assert "pptx" in decision.required_skills
    assert "slides-brand" in decision.required_skills

    gate.record_skill_view("pptx")
    still = gate.before_tool("write_file", {"path": "branded-deck.pptx"})
    assert still.action == SkillFirstAction.REQUIRE_SKILL_READ
    assert still.required_skills == ("slides-brand",)

    gate.record_skill_view("slides-brand")
    assert gate.before_tool("write_file", {"path": "branded-deck.pptx"}).allows_execution


def test_apply_skill_first_gate_on_agent() -> None:
    agent = SimpleNamespace(
        _skill_first=True,
        _skill_first_profile="standard",
        _skill_first_config={},
        _skill_first_gate=SkillFirstGate(profile="standard", skill_catalog=_CATALOG),
    )
    blocked = apply_skill_first_gate(agent, "write_file", {"path": "x.pptx"})
    assert blocked is not None
    payload = json.loads(blocked)
    assert payload["skill_first"] is True
    assert "pptx" in payload["required_skills"]

    record_after_skill_view(
        agent,
        "skill_view",
        {"name": "pptx"},
        json.dumps({"success": True, "name": "pptx"}),
    )
    assert apply_skill_first_gate(agent, "write_file", {"path": "x.pptx"}) is None


def test_disabled_flag_bypasses() -> None:
    agent = SimpleNamespace(_skill_first=False)
    assert apply_skill_first_gate(agent, "write_file", {"path": "x.pptx"}) is None


def test_failed_skill_view_does_not_record() -> None:
    gate = SkillFirstGate(profile="standard", skill_catalog=_CATALOG)
    agent = SimpleNamespace(
        _skill_first=True,
        _skill_first_profile="standard",
        _skill_first_config={},
        _skill_first_gate=gate,
    )
    record_after_skill_view(
        agent,
        "skill_view",
        {"name": "pptx"},
        json.dumps({"success": False, "error": "missing"}),
    )
    decision = gate.before_tool("write_file", {"path": "deck.pptx"})
    assert decision.action == SkillFirstAction.REQUIRE_SKILL_READ
