from __future__ import annotations

from keprix.agent.model_policy import ResolvedModelPolicy, enforce_model, model_allowed
from keprix.billing.schema import PlanConfig


def test_empty_policy_allows_global_models() -> None:
    policy = ResolvedModelPolicy("community", frozenset(), frozenset(), None)
    assert model_allowed("openai:gpt-4.1-mini", policy)


def test_policy_enforces_provider_and_model(monkeypatch) -> None:
    policy = ResolvedModelPolicy(
        "team", frozenset({"openai"}), frozenset({"gpt-4.1-mini"}), "openai:gpt-4.1-mini"
    )
    assert model_allowed("openai:gpt-4.1-mini", policy)
    assert not model_allowed("anthropic:claude-sonnet-4-6", policy)
    monkeypatch.setattr("keprix.agent.model_policy.resolve_model_policy", lambda _tier: policy)
    try:
        enforce_model("anthropic:claude-sonnet-4-6", "team")
    except ValueError as exc:
        assert "not allowed" in str(exc)
    else:
        raise AssertionError("disallowed model was accepted")


def test_plan_config_accepts_model_policy() -> None:
    plan = PlanConfig(
        id="team",
        name="Team",
        plan_model_policy={
            "allowed_providers": ["openai"],
            "allowed_models": ["gpt-4.1-mini"],
            "default_model": "openai:gpt-4.1-mini",
        },
    )
    assert plan.plan_model_policy.default_model == "openai:gpt-4.1-mini"
