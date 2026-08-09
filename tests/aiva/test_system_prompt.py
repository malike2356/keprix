from __future__ import annotations

from keprix.aiva.system_prompt import build_aiva_system_prompt, estimate_tokens, should_use_lean_aiva_prompt


def test_lean_prompt_under_3k_tokens() -> None:
    prompt = build_aiva_system_prompt(
        aiva_name="Aiva",
        user_name="Malike",
        tools=[{"name": "email.search"}, {"name": "calendar.list"}, "web.search"],
        memory_injection="Prefers short answers.",
        calendar_today="10:00 standup",
        recent_emails_summary="2 unread from clients",
        domain_knowledge="UK property investor",
    )
    assert "You are Aiva" in prompt
    assert "email.search" in prompt
    assert "Never invent information" in prompt
    assert "verlox monorepo" not in prompt.lower()
    assert "scout architecture" not in prompt.lower()
    assert estimate_tokens(prompt) < 3000


def test_workspace_overrides_and_property_domain() -> None:
    prompt = build_aiva_system_prompt(
        workspace_overrides={
            "aiva_name": "Portfolio Aiva",
            "tone": "Direct and practical.",
            "domain": "property",
            "domain_knowledge": "Focus on HMO compliance.",
        }
    )
    assert "Portfolio Aiva" in prompt
    assert "Direct and practical." in prompt
    assert "UK property operations" in prompt or "HMO compliance" in prompt
    assert "Confirm the active Propreneur tenant" in prompt


def test_engineering_markers_stripped_from_dynamic_blocks() -> None:
    prompt = build_aiva_system_prompt(
        memory_injection="Remember the Verlox monorepo structure and Scout architecture.",
        domain_knowledge="Keep build prompt formats handy.",
    )
    assert "verlox monorepo" not in prompt.lower()
    assert "scout architecture" not in prompt.lower()
    assert "build prompt" not in prompt.lower()


def test_should_use_lean_only_for_aiva() -> None:
    assert should_use_lean_aiva_prompt("aiva") is True
    assert should_use_lean_aiva_prompt("carina") is False
    assert should_use_lean_aiva_prompt(None) is False
