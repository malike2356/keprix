"""Normalize, resolve, check, and record actor quota limits."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from keprix.quotas.actor_store import ActorQuotaStore, ActorUsage, get_actor_quota_store
from keprix.quotas.policy import ActorLimitPolicy, default_policy
from keprix.quotas.scope import QuotaScope

logger = logging.getLogger(__name__)

VALID_PERIODS = frozenset({"day", "month"})
MAX_LIMIT_VALUE = int(1e12)


def _positive_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return min(n, MAX_LIMIT_VALUE)


def normalize_limits(input_limits: Any) -> dict[str, Any] | None:
    """Validate and canonicalize a limits object. None means no effective limits."""
    if input_limits is None:
        return None
    if not isinstance(input_limits, dict):
        raise ValueError("limits must be an object")

    out: dict[str, Any] = {}
    period = input_limits.get("period", "month")
    period = "month" if period is None else str(period)
    if period not in VALID_PERIODS:
        raise ValueError("limits.period must be 'day' or 'month'")
    out["period"] = period

    for key in ("max_calls", "max_tokens", "max_tool_runs", "max_mutation_runs"):
        # Accept camelCase aliases from external configs.
        camel = {
            "max_calls": "maxCalls",
            "max_tokens": "maxTokens",
            "max_tool_runs": "maxToolRuns",
            "max_mutation_runs": "maxMutationRuns",
        }[key]
        val = _positive_int(input_limits.get(key, input_limits.get(camel)))
        if val:
            out[key] = val

    per_raw = input_limits.get("per_service", input_limits.get("perService"))
    if per_raw is not None:
        if not isinstance(per_raw, dict):
            raise ValueError("limits.per_service must be an object keyed by service name")
        per_service: dict[str, dict[str, int]] = {}
        for service, cfg in per_raw.items():
            name = str(service).lower()
            if not name.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"limits.per_service: invalid service name '{service}'")
            if not isinstance(cfg, dict):
                raise ValueError(f"limits.per_service.{service} must be an object")
            svc: dict[str, int] = {}
            for key, camel in (
                ("max_calls", "maxCalls"),
                ("max_tokens", "maxTokens"),
                ("max_tool_runs", "maxToolRuns"),
                ("max_mutation_runs", "maxMutationRuns"),
            ):
                val = _positive_int(cfg.get(key, cfg.get(camel)))
                if val:
                    svc[key] = val
            if svc:
                per_service[name] = svc
        if per_service:
            out["per_service"] = per_service

    has_any = any(k in out for k in ("max_calls", "max_tokens", "max_tool_runs", "max_mutation_runs", "per_service"))
    return out if has_any else None


def policy_from_dict(data: dict[str, Any] | None) -> ActorLimitPolicy | None:
    normalized = normalize_limits(data) if data else None
    if not normalized:
        return None
    return ActorLimitPolicy(
        period=normalized.get("period", "month"),  # type: ignore[arg-type]
        max_calls=normalized.get("max_calls"),
        max_tokens=normalized.get("max_tokens"),
        max_tool_runs=normalized.get("max_tool_runs"),
        max_mutation_runs=normalized.get("max_mutation_runs"),
        per_service=dict(normalized.get("per_service") or {}),
    )


def resolve_limits(
    scope: QuotaScope,
    *,
    store: ActorQuotaStore | None = None,
    fallback: ActorLimitPolicy | None = None,
) -> ActorLimitPolicy:
    credit_store = store or get_actor_quota_store()
    try:
        override = credit_store.get_override(scope)
        policy = policy_from_dict(override)
        if policy and policy.has_limits():
            return policy
    except Exception:
        logger.debug("actor quota override read failed", exc_info=True)
    return fallback or default_policy()


@dataclass
class ActorQuotaDecision:
    allowed: bool
    reason: str = "ok"
    metric: str | None = None
    scope: str | None = None
    limit: int | None = None
    used: int | None = None
    period: str = "month"
    remaining: dict[str, int | None] | None = None
    limits: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    status_code: int = 429

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "metric": self.metric,
            "scope": self.scope,
            "limit": self.limit,
            "used": self.used,
            "period": self.period,
            "remaining": self.remaining,
            "limits": self.limits,
            "usage": self.usage,
            "status_code": self.status_code,
        }


def _remaining(limit: int | None, used: int) -> int | None:
    if limit is None:
        return None
    return max(0, int(limit) - int(used))


def check_actor_limits(
    scope: QuotaScope,
    *,
    service: str | None = None,
    tokens: int = 0,
    tool_runs: int = 0,
    mutation_runs: int = 0,
    calls: int = 1,
    enforce_tokens: bool = True,
    store: ActorQuotaStore | None = None,
    policy: ActorLimitPolicy | None = None,
) -> ActorQuotaDecision:
    """Return whether one more action fits within the actor's limits.

    Fails open if the store cannot be read (broken quota must not take the gateway down).
    """
    credit_store = store or get_actor_quota_store()
    try:
        limits = policy or resolve_limits(scope, store=credit_store)
        if not limits.has_limits():
            return ActorQuotaDecision(allowed=True, reason="no_limits")
        usage = credit_store.get_usage(scope, period=limits.period)
    except Exception:
        logger.exception("actor quota check failed open for %s", scope.key())
        return ActorQuotaDecision(allowed=True, reason="quota_store_unavailable")

    remaining = {
        "calls": _remaining(limits.max_calls, usage.calls),
        "tokens": _remaining(limits.max_tokens, usage.tokens),
        "tool_runs": _remaining(limits.max_tool_runs, usage.tool_runs),
        "mutation_runs": _remaining(limits.max_mutation_runs, usage.mutation_runs),
    }

    def deny(metric: str, scope_label: str, limit: int, used: int) -> ActorQuotaDecision:
        return ActorQuotaDecision(
            allowed=False,
            reason=f"{metric}_limit_reached",
            metric=metric,
            scope=scope_label,
            limit=limit,
            used=used,
            period=limits.period,
            remaining=remaining,
            limits=limits.to_dict(),
            usage=usage.to_dict(),
        )

    if limits.max_calls and usage.calls + max(0, calls) > limits.max_calls:
        return deny("calls", "total", limits.max_calls, usage.calls)
    if enforce_tokens and limits.max_tokens and usage.tokens + max(0, tokens) > limits.max_tokens:
        return deny("tokens", "total", limits.max_tokens, usage.tokens)
    if limits.max_tool_runs and usage.tool_runs + max(0, tool_runs) > limits.max_tool_runs:
        return deny("tool_runs", "total", limits.max_tool_runs, usage.tool_runs)
    if limits.max_mutation_runs and usage.mutation_runs + max(0, mutation_runs) > limits.max_mutation_runs:
        return deny("mutation_runs", "total", limits.max_mutation_runs, usage.mutation_runs)

    svc = (service or "").lower()
    if svc and limits.per_service:
        svc_limits = limits.per_service.get(svc)
        if svc_limits:
            svc_usage = usage.per_service.get(svc) or {
                "calls": 0,
                "tokens": 0,
                "tool_runs": 0,
                "mutation_runs": 0,
            }
            if svc_limits.get("max_calls") and svc_usage["calls"] + max(0, calls) > svc_limits["max_calls"]:
                return deny("calls", svc, svc_limits["max_calls"], svc_usage["calls"])
            if (
                enforce_tokens
                and svc_limits.get("max_tokens")
                and svc_usage["tokens"] + max(0, tokens) > svc_limits["max_tokens"]
            ):
                return deny("tokens", svc, svc_limits["max_tokens"], svc_usage["tokens"])
            if svc_limits.get("max_tool_runs") and svc_usage.get("tool_runs", 0) + max(0, tool_runs) > svc_limits["max_tool_runs"]:
                return deny("tool_runs", svc, svc_limits["max_tool_runs"], svc_usage.get("tool_runs", 0))
            if (
                svc_limits.get("max_mutation_runs")
                and svc_usage.get("mutation_runs", 0) + max(0, mutation_runs) > svc_limits["max_mutation_runs"]
            ):
                return deny("mutation_runs", svc, svc_limits["max_mutation_runs"], svc_usage.get("mutation_runs", 0))

    return ActorQuotaDecision(
        allowed=True,
        reason="ok",
        period=limits.period,
        remaining=remaining,
        limits=limits.to_dict(),
        usage=usage.to_dict(),
    )


def record_actor_usage(
    scope: QuotaScope,
    *,
    service: str = "",
    calls: int = 0,
    tokens: int = 0,
    tool_runs: int = 0,
    mutation_runs: int = 0,
    store: ActorQuotaStore | None = None,
) -> None:
    credit_store = store or get_actor_quota_store()
    try:
        credit_store.record(
            scope,
            service=service,
            calls=calls,
            tokens=tokens,
            tool_runs=tool_runs,
            mutation_runs=mutation_runs,
        )
    except Exception:
        logger.debug("actor quota record failed", exc_info=True)


def status_for_scope(
    scope: QuotaScope,
    *,
    store: ActorQuotaStore | None = None,
) -> dict[str, Any]:
    credit_store = store or get_actor_quota_store()
    limits = resolve_limits(scope, store=credit_store)
    usage = credit_store.get_usage(scope, period=limits.period)
    return {
        "scope": scope.to_dict(),
        "period": limits.period,
        "limits": limits.to_dict(),
        "usage": usage.to_dict(),
        "remaining": {
            "calls": _remaining(limits.max_calls, usage.calls),
            "tokens": _remaining(limits.max_tokens, usage.tokens),
            "tool_runs": _remaining(limits.max_tool_runs, usage.tool_runs),
            "mutation_runs": _remaining(limits.max_mutation_runs, usage.mutation_runs),
        },
    }
