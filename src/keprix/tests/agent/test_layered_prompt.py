"""Tests for layered system prompt architecture."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.layered_assembly import LayeredStableInput, assemble_layered_stable
from agent.layered_prompt import LayeredPromptBuilder, PromptLayer, domain_layer_keys
from agent.layers.budget import render_budget_layer
from agent.layers.safety import SAFETY_LAYER
from agent.system_prompt import build_system_prompt_parts


class _Budget:
    remaining = 4
    max_total = 10


def _mock_agent(**overrides):
    base = {
        "valid_tool_names": ["memory", "web_search"],
        "model": "gpt-4.1",
        "provider": "openai",
        "session_id": "sess_test",
        "session_total_tokens": 12_000,
        "api_call_count": 3,
        "platform": "web",
        "load_soul_identity": False,
        "skip_context_files": True,
        "_task_completion_guidance": True,
        "_tool_use_enforcement": False,
        "_environment_probe": False,
        "_layered_prompt": True,
        "_memory_store": None,
        "_memory_manager": None,
        "_memory_enabled": False,
        "_user_profile_enabled": False,
        "pass_session_id": True,
        "iteration_budget": _Budget(),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_layers_are_ordered():
    builder = LayeredPromptBuilder()
    builder.add_layer(PromptLayer.TONE, "tone content")
    builder.add_layer(PromptLayer.IDENTITY, "identity content")
    prompt = builder.build()
    assert prompt.index("<identity>") < prompt.index("<tone>")
    assert "identity content" in prompt
    assert "tone content" in prompt


def test_missing_layers_are_omitted():
    builder = LayeredPromptBuilder()
    builder.add_layer(PromptLayer.SAFETY, "safety only")
    prompt = builder.build()
    assert "<safety>" in prompt
    assert "<identity>" not in prompt


def test_budget_layer_shows_remaining_turns():
    agent = _mock_agent(session_total_tokens=40_000, api_call_count=4)
    layer = render_budget_layer(agent)
    assert "Token budget" in layer
    assert "Estimated remaining turns" in layer


def test_safety_layer_covers_all_categories():
    required = (
        "Child safety",
        "Weapons",
        "Malicious code",
        "Medical",
        "Self-harm",
        "Creative content",
        "Refusal tone",
    )
    for label in required:
        assert label in SAFETY_LAYER


def test_domain_layers_injected_for_medical_context():
    keys = domain_layer_keys("Can you explain this medical symptom?")
    assert "medical" in keys
    report = assemble_layered_stable(
        _mock_agent(),
        LayeredStableInput(domain_context_text="medical symptom diagnosis"),
    )
    assert "<domain>" in report
    assert "health or medical topic" in report.lower()


def test_build_system_prompt_parts_uses_layer_markers():
    parts = build_system_prompt_parts(_mock_agent(), system_message="legal advice on contract")
    assert "<identity>" in parts["stable"]
    assert "<budget>" in parts["stable"]
    assert "<safety>" in parts["stable"]
    assert "<tools>" in parts["stable"]
    assert "<tone>" in parts["stable"]
    assert "<execution>" in parts["stable"]


def test_layered_prompt_can_be_disabled():
    parts = build_system_prompt_parts(_mock_agent(_layered_prompt=False))
    assert "<identity>" not in parts["stable"]
    assert "You are Keprix" in parts["stable"]
