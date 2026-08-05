"""Edition and deployment default quota policies.

Quotas are abuse/cost controls, separate from managed AI billing credits.
Self-hosted and Community stay generous; hosted trial and public accounts
get stricter defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

from keprix.licensing.edition import current_edition

Period = Literal["day", "month"]


@dataclass(frozen=True)
class ActorLimitPolicy:
    period: Period = "month"
    max_calls: int | None = None
    max_tokens: int | None = None
    max_tool_runs: int | None = None
    max_mutation_runs: int | None = None
    per_service: dict[str, dict[str, int]] = field(default_factory=dict)

    def has_limits(self) -> bool:
        return bool(
            self.max_calls
            or self.max_tokens
            or self.max_tool_runs
            or self.max_mutation_runs
            or self.per_service
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"period": self.period}
        if self.max_calls:
            out["max_calls"] = self.max_calls
        if self.max_tokens:
            out["max_tokens"] = self.max_tokens
        if self.max_tool_runs:
            out["max_tool_runs"] = self.max_tool_runs
        if self.max_mutation_runs:
            out["max_mutation_runs"] = self.max_mutation_runs
        if self.per_service:
            out["per_service"] = {k: dict(v) for k, v in self.per_service.items()}
        return out


def _is_hosted() -> bool:
    raw = (os.environ.get("KEPRIX_HOSTED") or os.environ.get("KEPRIX_DEPLOYMENT") or "").strip().lower()
    if raw in {"1", "true", "yes", "hosted", "saas", "cloud"}:
        return True
    if raw in {"0", "false", "no", "self_hosted", "self-hosted", "community"}:
        return False
    try:
        from keprix.billing.wallet.policy import is_hosted_deployment

        return is_hosted_deployment()
    except Exception:
        return False


def deployment_tier() -> str:
    """Return community | self_hosted | hosted_trial | hosted_pro."""
    if not _is_hosted():
        return "community" if current_edition() == "community" else "self_hosted"
    plan = (os.environ.get("KEPRIX_HOSTED_PLAN") or "").strip().lower()
    if plan in {"pro", "team", "starter", "paid"}:
        return "hosted_pro"
    # Default hosted accounts to trial-strict until a paid plan is known.
    return "hosted_trial"


# Stricter for public hosted; local self-host is effectively unlimited.
_DEFAULTS: dict[str, ActorLimitPolicy] = {
    "community": ActorLimitPolicy(
        period="month",
        max_calls=1_000_000,
        max_tokens=50_000_000,
        max_tool_runs=500_000,
        max_mutation_runs=50_000,
    ),
    "self_hosted": ActorLimitPolicy(
        period="month",
        max_calls=1_000_000,
        max_tokens=50_000_000,
        max_tool_runs=500_000,
        max_mutation_runs=50_000,
    ),
    "hosted_trial": ActorLimitPolicy(
        period="day",
        max_calls=200,
        max_tokens=200_000,
        max_tool_runs=100,
        max_mutation_runs=20,
        per_service={
            "llm": {"max_calls": 150, "max_tokens": 150_000},
            "mutation": {"max_calls": 20, "max_tokens": 50_000},
            "tools": {"max_calls": 100},
        },
    ),
    "hosted_pro": ActorLimitPolicy(
        period="month",
        max_calls=50_000,
        max_tokens=10_000_000,
        max_tool_runs=25_000,
        max_mutation_runs=2_000,
        per_service={
            "llm": {"max_calls": 40_000, "max_tokens": 8_000_000},
            "mutation": {"max_calls": 2_000, "max_tokens": 2_000_000},
        },
    ),
}


def default_policy_for_tier(tier: str | None = None) -> ActorLimitPolicy:
    key = tier or deployment_tier()
    return _DEFAULTS.get(key, _DEFAULTS["community"])


def default_policy() -> ActorLimitPolicy:
    return default_policy_for_tier()
