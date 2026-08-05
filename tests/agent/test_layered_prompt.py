"""Layered system prompt integration tests (prompt 289)."""

from __future__ import annotations

from types import SimpleNamespace

from agent.layered_assembly import LayeredStableInput, assemble_layered_stable
from agent.layered_prompt import domain_layer_keys
from agent.layers.budget import render_budget_layer
from agent.system_prompt import build_system_prompt_parts


def _mock_agent(**overrides):
    base = {
        "valid_tool_names": ["memory", "web_search"],
        "model": "gpt-4.1",
        "provider": "openai",
        "session_id": "sess_test",
        "session_total_tokens": 12_000,
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
        "_user_turn_count": 3,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_budget_layer_shows_remaining_turns():
    agent = _mock_agent(session_total_tokens=40_000)
    layer = render_budget_layer(agent)
    assert "Token budget" in layer
    assert "Estimated remaining turns" in layer


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
    stable = parts["stable"]
    for tag in ("identity", "budget", "safety", "tools", "tone", "execution"):
        assert f"<{tag}>" in stable


def test_layered_prompt_can_be_disabled():
    parts = build_system_prompt_parts(_mock_agent(_layered_prompt=False))
    assert "<identity>" not in parts["stable"]
    assert "You are Keprix" in parts["stable"]
