"""QuotaEnforcer: check and record resource usage at LLM call and tool boundaries.

Called from:
  - agent/conversation_loop.py: check_before_llm_call before request,
    record_llm_usage after response
  - agent/tool_executor.py: increment tool_calls after each tool dispatch
  - gateway session management: increment/decrement concurrent_sessions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .quota_config import ProductQuota, QuotaConfig, QuotaUsage, ResourceType, get_quota_config
from .quota_store import QuotaStore

QUOTA_WARNING_THRESHOLD = 0.90

QUOTA_WARNING_MESSAGE = (
    "[System: You are approaching your token limit for this billing period. "
    "Remaining: {remaining} tokens. Please wrap up this conversation efficiently. "
    "The user can upgrade their plan at /billing to increase the limit.]"
)

QUOTA_EXHAUSTED_MESSAGE = (
    "[System: Token quota exhausted for this billing period. "
    "You may not make further LLM calls. Tell the user clearly and suggest "
    "they upgrade at /billing or wait for the next billing period reset on {reset_date}.]"
)


@dataclass
class QuotaCheckResult:
    allowed: bool
    reason: str = ""
    remaining: int = 0
    action: str = "block"           # "block" | "graceful" | "alert_only"
    warning_message: str | None = None   # injected into conversation when graceful

    @property
    def is_hard_blocked(self) -> bool:
        return not self.allowed and self.action == "block"


class QuotaEnforcer:
    """Pre-flight checker and post-call usage recorder.

    Usage::

        enforcer = QuotaEnforcer(store, config)
        result = await enforcer.check_before_llm_call("aiva", estimated_tokens=1000)
        if result.is_hard_blocked:
            raise QuotaExhausted(result.reason)
        # ... make LLM call ...
        await enforcer.record_llm_usage("aiva", tokens_in=950, tokens_out=200, session_id=...)
    """

    def __init__(
        self,
        store: QuotaStore | None = None,
        config: QuotaConfig | None = None,
    ) -> None:
        self._store = store or QuotaStore()
        self._config = config or get_quota_config()

    async def check_before_llm_call(
        self,
        product_id: str,
        estimated_tokens: int = 0,
    ) -> QuotaCheckResult:
        usage = await self._store.get_usage(product_id)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.LLM_TOKENS_IN

        if usage.is_exhausted(resource):
            action = quota.get_action(resource)
            reset_date = usage.period_end.strftime("%Y-%m-%d")
            warning = None
            if action != "block":
                warning = QUOTA_EXHAUSTED_MESSAGE.format(reset_date=reset_date)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="llm_tokens_in_exhausted",
                remaining=0,
                action=action,
                warning_message=warning,
            )

        remaining = usage.remaining(resource)

        # Near-limit warning (graceful products only)
        warning = None
        action = quota.get_action(resource)
        if usage.is_near_limit(resource, QUOTA_WARNING_THRESHOLD):
            if action in ("graceful", "alert_only"):
                warning = QUOTA_WARNING_MESSAGE.format(remaining=remaining)

        return QuotaCheckResult(
            allowed=True,
            reason="ok",
            remaining=remaining,
            action=action,
            warning_message=warning,
        )

    async def record_llm_usage(
        self,
        product_id: str,
        tokens_in: int,
        tokens_out: int,
        session_id: str | None = None,
    ) -> None:
        await self._store.increment(product_id, ResourceType.LLM_TOKENS_IN, tokens_in, session_id)
        await self._store.increment(product_id, ResourceType.LLM_TOKENS_OUT, tokens_out, session_id)

    async def record_tool_call(
        self,
        product_id: str,
        session_id: str | None = None,
    ) -> QuotaCheckResult:
        """Record one tool call and return whether future calls are still allowed."""
        usage = await self._store.increment(product_id, ResourceType.TOOL_CALLS, 1, session_id)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.TOOL_CALLS

        if usage.is_exhausted(resource):
            action = quota.get_action(resource)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="tool_calls_exhausted",
                remaining=0,
                action=action,
            )
        return QuotaCheckResult(allowed=True, remaining=usage.remaining(resource))

    async def check_concurrent_sessions(self, product_id: str) -> QuotaCheckResult:
        usage = await self._store.get_usage(product_id)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.CONCURRENT_SESSIONS
        limit = quota.get_limit(resource)
        current = usage.used(resource)

        if current >= limit:
            return QuotaCheckResult(
                allowed=False,
                reason="concurrent_sessions_exhausted",
                remaining=0,
                action="block",
            )
        return QuotaCheckResult(allowed=True, remaining=limit - current)

    async def record_storage(
        self,
        product_id: str,
        bytes_delta: int,
    ) -> QuotaCheckResult:
        usage = await self._store.increment(product_id, ResourceType.STORAGE_BYTES, bytes_delta)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.STORAGE_BYTES

        if usage.is_exhausted(resource):
            action = quota.get_action(resource)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="storage_bytes_exhausted",
                remaining=0,
                action=action,
            )
        return QuotaCheckResult(allowed=True, remaining=usage.remaining(resource))

    async def check_before_mutation(
        self,
        product_id: str,
        *,
        estimated_tokens: int = 0,
    ) -> QuotaCheckResult:
        usage = await self._store.get_usage(product_id)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.MUTATION_RUNS
        if usage.is_exhausted(resource):
            action = quota.get_action(resource)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="mutation_runs_exhausted",
                remaining=0,
                action=action,
            )
        # Also respect estimated token headroom when configured.
        if estimated_tokens and usage.remaining(ResourceType.ESTIMATED_TOKENS) < estimated_tokens:
            action = quota.get_action(ResourceType.ESTIMATED_TOKENS)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="estimated_tokens_exhausted",
                remaining=usage.remaining(ResourceType.ESTIMATED_TOKENS),
                action=action,
            )
        return QuotaCheckResult(
            allowed=True,
            remaining=usage.remaining(resource),
            action=quota.get_action(resource),
        )

    async def record_mutation_run(
        self,
        product_id: str,
        *,
        tokens: int = 0,
        session_id: str | None = None,
    ) -> None:
        await self._store.increment(product_id, ResourceType.MUTATION_RUNS, 1, session_id)
        if tokens:
            await self._store.increment(product_id, ResourceType.ESTIMATED_TOKENS, tokens, session_id)

    async def check_before_tool_run(self, product_id: str) -> QuotaCheckResult:
        usage = await self._store.get_usage(product_id)
        quota = await self._config.get_quota(product_id)
        resource = ResourceType.TOOL_CALLS
        if usage.is_exhausted(resource):
            action = quota.get_action(resource)
            return QuotaCheckResult(
                allowed=(action != "block"),
                reason="tool_calls_exhausted",
                remaining=0,
                action=action,
            )
        return QuotaCheckResult(
            allowed=True,
            remaining=usage.remaining(resource),
            action=quota.get_action(resource),
        )
