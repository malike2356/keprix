"""Colleague memory continuity tests (Prompt 295)."""

from __future__ import annotations

from types import SimpleNamespace

from agent.layered_assembly import LayeredStableInput, assemble_layered_stable
from agent.layered_prompt import PromptLayer
from agent.layers.memory_continuity import MEMORY_CONTINUITY_LAYER
from agent.memory_edit_gate import (
    detect_memory_edit_intent,
    evaluate_continuity_search_gate,
    evaluate_memory_edit_gate,
    has_continuity_reference,
    mark_memory_edited,
    reset_continuity_turn_flags,
)
from tools.conversation_search_tool import (
    _product_isolation_error,
    conversation_search_tool,
)
from tools.threat_patterns import first_threat_message


def test_memory_continuity_layer_in_layered_prompt() -> None:
    agent = SimpleNamespace(
        valid_tool_names=["memory", "session_search", "conversation_search"],
        model="gpt-4.1",
        provider="openai",
        session_id="s1",
        session_total_tokens=1000,
        platform="web",
        load_soul_identity=False,
        skip_context_files=True,
        _task_completion_guidance=False,
        _tool_use_enforcement=False,
        _environment_probe=False,
        _layered_prompt=True,
        _memory_store=None,
        _memory_manager=None,
        _memory_enabled=False,
        _user_profile_enabled=False,
        pass_session_id=True,
        _user_turn_count=1,
    )
    prompt = assemble_layered_stable(agent, LayeredStableInput())
    assert "<memory>" in prompt
    assert "Do not narrate memory retrieval" in prompt
    assert MEMORY_CONTINUITY_LAYER.split("\n")[0] in prompt
    assert prompt.index("<tone>") < prompt.index("<memory>")
    assert prompt.index("<memory>") < prompt.index("<execution>")
    assert PromptLayer.MEMORY.value == 6


def test_remember_intent_and_gate_blocks_false_confirm() -> None:
    agent = SimpleNamespace()
    reset_continuity_turn_flags(agent)
    assert detect_memory_edit_intent("Please remember that I prefer tabs") == "remember"
    assert detect_memory_edit_intent("Forget that preference") == "forget"

    nudge = evaluate_memory_edit_gate(
        "Remember that I prefer tabs",
        "Got it, I'll remember that.",
        agent,
    )
    assert nudge is not None
    assert "memory tool" in nudge.lower()

    mark_memory_edited(agent)
    assert (
        evaluate_memory_edit_gate(
            "Remember that I prefer tabs",
            "Got it, I'll remember that.",
            agent,
        )
        is None
    )


def test_continuity_search_gate_when_asking_user_to_repeat() -> None:
    agent = SimpleNamespace()
    reset_continuity_turn_flags(agent)
    assert has_continuity_reference("About the bug we discussed yesterday")
    nudge = evaluate_continuity_search_gate(
        "About the bug we discussed yesterday",
        "Can you remind me what that bug was?",
        agent,
    )
    assert nudge is not None
    assert "session_search" in nudge or "conversation_search" in nudge


def test_privacy_floors_block_ssn_and_payment() -> None:
    assert first_threat_message("ssn: 123-45-6789", scope="strict")
    assert first_threat_message("card number 4111111111111111", scope="strict")
    assert first_threat_message('password="supersecretvalue1234567890"', scope="strict")


def test_product_isolation_blocks_foreign_profile(monkeypatch) -> None:
    import keprix.security.product_context as pc

    ctx = SimpleNamespace(product_id="product-a", workspace_id="ws-a", tenant_id="t-a")
    monkeypatch.setattr(pc, "get_product_context_or_none", lambda: ctx)
    err = _product_isolation_error("product-b")
    assert err is not None
    assert "Cross-product" in err
    assert _product_isolation_error("product-a") is None


def test_conversation_search_requires_query() -> None:
    import json

    result = json.loads(conversation_search_tool(query=""))
    assert result.get("success") is False or "error" in result
