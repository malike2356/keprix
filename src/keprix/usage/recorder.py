"""Record LLM usage events at call sites."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.usage_pricing import CanonicalUsage

from keprix.usage.config import get_llm_usage_config
from keprix.usage.pricing_bridge import estimate_llm_cost
from keprix.usage.schemas import LlmUsageRecord
from keprix.usage.store import get_llm_usage_store

logger = logging.getLogger(__name__)

_CHANNEL_ALIASES = {
    "web": "web_ui",
    "webui": "web_ui",
    "web_ui": "web_ui",
    "telegram": "telegram",
    "discord": "discord",
    "cron": "cron",
    "cli": "cli",
    "gateway": "gateway",
    "api": "api",
    "eval": "eval",
    "compare": "compare",
    "mutation": "mutation",
    "plugin": "plugin",
    "agent": "agent",
}


def normalize_channel(value: str | None) -> str:
    key = str(value or "agent").strip().lower()
    return _CHANNEL_ALIASES.get(key, key or "agent")


class LlmUsageRecorder:
    async def record(
        self,
        *,
        usage: CanonicalUsage,
        provider: str,
        model: str,
        channel: str,
        user_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        workspace_id: str = "default",
        base_url: str | None = None,
        api_key: str | None = None,
        cost_result: Any | None = None,
    ) -> str:
        config = get_llm_usage_config()
        if not config.enabled:
            return ""

        try:
            cost = cost_result or estimate_llm_cost(
                usage=usage,
                model=model,
                provider=provider,
                base_url=base_url,
                api_key=api_key,
            )
            record = LlmUsageRecord(
                workspace_id=workspace_id,
                user_id=user_id,
                session_id=session_id,
                run_id=run_id,
                channel=normalize_channel(channel),
                provider=provider or "",
                model=model or "",
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_tokens,
                cache_write_tokens=usage.cache_write_tokens,
                reasoning_tokens=usage.reasoning_tokens,
                total_tokens=usage.total_tokens,
                cost_usd=cost.amount_usd if cost.amount_usd is not None else None,
                cost_status=str(cost.status),
                cost_source=str(cost.source),
                duration_ms=duration_ms,
                metadata=dict(metadata or {}),
            )
            event_id = await get_llm_usage_store().insert_async(record)
            self._mirror_prompt57_meters(record, run_id=run_id, workspace_id=workspace_id)
            return event_id
        except Exception as exc:
            logger.warning("LLM usage record failed: %s", exc)
            return ""

    def record_sync(self, **kwargs: Any) -> str:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.record(**kwargs))
        future = asyncio.run_coroutine_threadsafe(self.record(**kwargs), loop)
        try:
            return future.result(timeout=5)
        except Exception as exc:
            logger.warning("LLM usage record_sync failed: %s", exc)
            return ""

    def _mirror_prompt57_meters(
        self,
        record: LlmUsageRecord,
        *,
        run_id: str | None,
        workspace_id: str,
    ) -> None:
        from keprix.backend.observability.cost_meter import record_cost
        from keprix.backend.observability.token_meter import get_token_meter

        rid = run_id or record.id
        get_token_meter().record(
            rid,
            {
                "input": record.input_tokens,
                "output": record.output_tokens,
                "total": record.total_tokens,
            },
            workspace_id=workspace_id,
        )
        if record.cost_usd is not None:
            record_cost(rid, float(record.cost_usd), workspace_id=workspace_id)


_recorder: LlmUsageRecorder | None = None


def get_llm_usage_recorder() -> LlmUsageRecorder:
    global _recorder
    if _recorder is None:
        _recorder = LlmUsageRecorder()
    return _recorder
