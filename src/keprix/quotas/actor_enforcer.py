"""High-level actor quota enforcement with audit and HTTP 429 mapping."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from keprix.quotas.actor_limits import (
    ActorQuotaDecision,
    check_actor_limits,
    normalize_limits,
    record_actor_usage,
    resolve_limits,
    status_for_scope,
)
from keprix.quotas.actor_store import get_actor_quota_store
from keprix.quotas.policy import deployment_tier
from keprix.quotas.scope import QuotaScope, scopes_for_request

logger = logging.getLogger(__name__)


class ActorQuotaExceeded(RuntimeError):
    """Raised when an actor quota blocks an action (map to HTTP 429)."""

    def __init__(self, message: str, *, decision: ActorQuotaDecision, scope: QuotaScope) -> None:
        super().__init__(message)
        self.decision = decision
        self.scope = scope

    @property
    def status_code(self) -> int:
        return 429

    def to_http_detail(self) -> dict[str, Any]:
        payload = self.decision.to_dict()
        payload["scope"] = self.scope.to_dict()
        payload["error"] = "quota_exceeded"
        return payload


@dataclass
class MultiScopeCheckResult:
    allowed: bool
    decision: ActorQuotaDecision
    scope: QuotaScope | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision.to_dict(),
            "scope": self.scope.to_dict() if self.scope else None,
        }


async def _audit_denial(
    scope: QuotaScope,
    decision: ActorQuotaDecision,
    *,
    workspace_id: str | None,
    run_id: str | None,
    service: str | None,
) -> None:
    store = get_actor_quota_store()
    try:
        store.record_denial(
            scope,
            reason=decision.reason,
            metric=decision.metric,
            service=service,
            detail=decision.to_dict(),
            workspace_id=workspace_id,
            run_id=run_id,
        )
    except Exception:
        logger.debug("quota denial store write failed", exc_info=True)
    try:
        from keprix.security.audit import audit_log

        await audit_log(
            "quota_denied",
            user_id=scope.scope_id if scope.scope_type == "user" else None,
            event_data={
                "scope": scope.to_dict(),
                "reason": decision.reason,
                "metric": decision.metric,
                "service": service,
                "workspace_id": workspace_id,
                "run_id": run_id,
                "limit": decision.limit,
                "used": decision.used,
                "period": decision.period,
                "deployment_tier": deployment_tier(),
            },
            severity="warning",
        )
    except Exception:
        logger.debug("quota denial audit_log failed", exc_info=True)


async def check_scopes(
    *,
    service: str,
    workspace_id: str | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    api_token_id: str | None = None,
    product_id: str | None = None,
    tokens: int = 0,
    tool_runs: int = 0,
    mutation_runs: int = 0,
    calls: int = 1,
    run_id: str | None = None,
    raise_on_block: bool = False,
) -> MultiScopeCheckResult:
    """Check all applicable scopes. First denial wins."""
    scopes = scopes_for_request(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_id=agent_id,
        api_token_id=api_token_id,
        product_id=product_id,
    )
    last_ok = ActorQuotaDecision(allowed=True, reason="ok")
    last_scope: QuotaScope | None = scopes[0] if scopes else None

    for scope in scopes:
        decision = check_actor_limits(
            scope,
            service=service,
            tokens=tokens,
            tool_runs=tool_runs,
            mutation_runs=mutation_runs,
            calls=calls,
        )
        last_ok = decision
        last_scope = scope
        if not decision.allowed:
            await _audit_denial(
                scope,
                decision,
                workspace_id=workspace_id,
                run_id=run_id,
                service=service,
            )
            result = MultiScopeCheckResult(allowed=False, decision=decision, scope=scope)
            if raise_on_block:
                raise ActorQuotaExceeded(
                    f"Quota exceeded ({decision.reason}) for {scope.key()}",
                    decision=decision,
                    scope=scope,
                )
            return result

    return MultiScopeCheckResult(allowed=True, decision=last_ok, scope=last_scope)


def record_scopes(
    *,
    service: str,
    workspace_id: str | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    api_token_id: str | None = None,
    product_id: str | None = None,
    tokens: int = 0,
    tool_runs: int = 0,
    mutation_runs: int = 0,
    calls: int = 1,
) -> None:
    """Record usage against every applicable scope (isolated counters)."""
    for scope in scopes_for_request(
        workspace_id=workspace_id,
        user_id=user_id,
        agent_id=agent_id,
        api_token_id=api_token_id,
        product_id=product_id,
    ):
        record_actor_usage(
            scope,
            service=service,
            calls=calls,
            tokens=tokens,
            tool_runs=tool_runs,
            mutation_runs=mutation_runs,
        )


async def assert_actor_quota(**kwargs: Any) -> MultiScopeCheckResult:
    return await check_scopes(raise_on_block=True, **kwargs)


def remaining_headers(decision: ActorQuotaDecision) -> dict[str, str]:
    """Optional response headers exposing remaining allowance."""
    headers: dict[str, str] = {}
    remaining = decision.remaining or {}
    if remaining.get("calls") is not None:
        headers["X-Keprix-Quota-Remaining-Calls"] = str(remaining["calls"])
    if remaining.get("tokens") is not None:
        headers["X-Keprix-Quota-Remaining-Tokens"] = str(remaining["tokens"])
    if remaining.get("tool_runs") is not None:
        headers["X-Keprix-Quota-Remaining-Tool-Runs"] = str(remaining["tool_runs"])
    if remaining.get("mutation_runs") is not None:
        headers["X-Keprix-Quota-Remaining-Mutation-Runs"] = str(remaining["mutation_runs"])
    if decision.period:
        headers["X-Keprix-Quota-Period"] = decision.period
    return headers


__all__ = [
    "ActorQuotaExceeded",
    "MultiScopeCheckResult",
    "assert_actor_quota",
    "check_scopes",
    "normalize_limits",
    "record_scopes",
    "remaining_headers",
    "resolve_limits",
    "status_for_scope",
]
