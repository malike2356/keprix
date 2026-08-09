from __future__ import annotations

import pytest

from keprix.agent.carina_bridge import _default_complete
from keprix.aiva.model_routing import model_supports_tools, resolve_aiva_model


def test_starter_uses_configurable_fast_default() -> None:
    route = resolve_aiva_model(
        workspace_id="ws-1",
        env={"AIVA_PROVIDER": "openai", "AIVA_MODEL": "gpt-4o-mini"},
    )
    assert route.model_id == "openai:gpt-4o-mini"
    assert route.source == "environment_default"
    assert route.latency_target_ms == 2000


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        ("growth", "anthropic:claude-haiku-4-5"),
        ("business", "anthropic:claude-sonnet-4-6"),
        ("premium", "anthropic:claude-sonnet-4-6"),
    ],
)
def test_paid_tiers_select_their_models(tier: str, expected: str) -> None:
    route = resolve_aiva_model(workspace_id="ws-1", tier=tier, env={})
    assert route.model_id == expected


def test_workspace_override_wins_over_tier() -> None:
    route = resolve_aiva_model(
        workspace_id="ws-premium",
        tier="growth",
        env={"AIVA_WORKSPACE_MODELS": '{"ws-premium":"openai:gpt-4o-mini"}'},
    )
    assert route.model_id == "openai:gpt-4o-mini"
    assert route.source == "configured_workspace_override"


def test_request_workspace_override_has_highest_priority() -> None:
    route = resolve_aiva_model(
        workspace_id="ws-1",
        tier="business",
        workspace_provider="google",
        workspace_model="gemini-3.5-flash",
        env={"AIVA_WORKSPACE_MODELS": '{"ws-1":"openai:gpt-4o-mini"}'},
    )
    assert route.model_id == "google:gemini-3.5-flash"
    assert route.source == "request_workspace_override"


def test_rejects_known_non_tool_model() -> None:
    assert model_supports_tools("deepseek", "deepseek-r1") is False
    with pytest.raises(ValueError, match="does not support required tools"):
        resolve_aiva_model(
            workspace_id="ws-1",
            workspace_model="deepseek-r1",
            workspace_provider="deepseek",
            env={},
        )


@pytest.mark.asyncio
async def test_flash_disables_deepseek_thinking_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    class Completions:
        async def create(self, **kwargs):
            observed.update(kwargs)
            message = type("Message", (), {"content": "ok", "tool_calls": None})()
            choice = type("Choice", (), {"message": message, "finish_reason": "stop"})()
            return type("Response", (), {"choices": [choice], "usage": None})()

    client = type("Client", (), {"chat": type("Chat", (), {"completions": Completions()})()})()
    monkeypatch.delenv("AIVA_DEEPSEEK_THINKING", raising=False)
    monkeypatch.setattr(
        "agent.auxiliary_client.resolve_provider_client",
        lambda *_args, **_kwargs: (client, "deepseek-v4-flash"),
    )

    await _default_complete(
        provider="deepseek",
        model="deepseek-v4-flash",
        temperature=0.7,
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
    )

    assert observed["extra_body"] == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_engineering_model_keeps_default_thinking(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    class Completions:
        async def create(self, **kwargs):
            observed.update(kwargs)
            message = type("Message", (), {"content": "ok", "tool_calls": None})()
            choice = type("Choice", (), {"message": message, "finish_reason": "stop"})()
            return type("Response", (), {"choices": [choice], "usage": None})()

    client = type("Client", (), {"chat": type("Chat", (), {"completions": Completions()})()})()
    monkeypatch.setattr(
        "agent.auxiliary_client.resolve_provider_client",
        lambda *_args, **_kwargs: (client, "deepseek-v4-pro"),
    )

    await _default_complete(
        provider="deepseek",
        model="deepseek-v4-pro",
        temperature=0.7,
        messages=[{"role": "user", "content": "build"}],
        tools=[],
    )

    assert "extra_body" not in observed
