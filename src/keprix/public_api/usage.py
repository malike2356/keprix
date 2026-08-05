"""Usage metering for developer API keys."""

from __future__ import annotations

from typing import Any

from keprix.observability.metrics import get_metrics_store
from keprix.public_api.keys import ApiKeyContext, get_api_key_store
from keprix.usage.pricing_bridge import usage_from_counts
from keprix.usage.recorder import get_llm_usage_recorder


async def record_api_usage(
    ctx: ApiKeyContext,
    *,
    endpoint: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
) -> None:
    store = get_metrics_store()
    total = prompt_tokens + completion_tokens
    await store.record(
        metric_type="provider_request",
        metric_name=model,
        metric_value=total,
        user_id=ctx.workspace_id,
        tags={
            "api_key_id": ctx.key_id,
            "endpoint": endpoint,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    )
    get_api_key_store().increment_usage(ctx.key_id, amount=1)
    await get_llm_usage_recorder().record(
        usage=usage_from_counts(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        ),
        provider=provider or "api",
        model=model,
        channel="api",
        user_id=ctx.workspace_id,
        session_id=session_id,
        run_id=run_id,
        workspace_id=ctx.workspace_id,
        metadata={"api_key_id": ctx.key_id, "endpoint": endpoint},
    )


async def usage_summary(workspace_id: str = "default", days: int = 30) -> dict[str, Any]:
    store = get_metrics_store()
    try:
        breakdown = await store.breakdown(
            metric_type="provider_request",
            days=days,
            user_id=workspace_id,
        )
        rate_limits = await store.rate_limit_events(days=days)
    except Exception:
        breakdown = []
        rate_limits = []
    keys = get_api_key_store().list_keys(workspace_id=workspace_id)
    return {
        "workspace_id": workspace_id,
        "days": days,
        "by_model": breakdown,
        "rate_limit_events": rate_limits,
        "keys": [key.model_dump() for key in keys],
    }
