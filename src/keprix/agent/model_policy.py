"""Tier-aware model selection and enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.billing.config_loader import load_billing_config


@dataclass(frozen=True)
class ResolvedModelPolicy:
    tier: str
    allowed_providers: frozenset[str]
    allowed_models: frozenset[str]
    default_model: str | None


def resolve_model_policy(tier: str) -> ResolvedModelPolicy:
    config = load_billing_config()
    plan = config.plan_by_id(tier) if config else None
    policy = plan.plan_model_policy if plan else None
    if policy is None:
        return ResolvedModelPolicy(tier, frozenset(), frozenset(), None)
    return ResolvedModelPolicy(
        tier=tier,
        allowed_providers=frozenset(
            item.strip().lower() for item in policy.allowed_providers if item.strip()
        ),
        allowed_models=frozenset(item.strip() for item in policy.allowed_models if item.strip()),
        default_model=policy.default_model.strip() if policy.default_model else None,
    )


def model_allowed(model_id: str, policy: ResolvedModelPolicy) -> bool:
    provider, _, model = model_id.partition(":")
    if policy.allowed_providers and provider.lower() not in policy.allowed_providers:
        return False
    return (
        not policy.allowed_models
        or model in policy.allowed_models
        or model_id in policy.allowed_models
    )


def resolve_default_model(tier: str, global_default: str | None = None) -> str | None:
    policy = resolve_model_policy(tier)
    if policy.default_model and model_allowed(policy.default_model, policy):
        return policy.default_model
    return global_default


def enforce_model(model_id: str, tier: str) -> str:
    policy = resolve_model_policy(tier)
    if policy.allowed_providers or policy.allowed_models:
        if not model_allowed(model_id, policy):
            raise ValueError(f"Model {model_id!r} is not allowed on plan tier {tier!r}")
    return model_id
