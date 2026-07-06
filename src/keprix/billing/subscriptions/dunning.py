"""Failed payment retry schedule."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.subscriptions.lifecycle import cancel_subscription, expire_subscription, mark_past_due


async def record_payment_failure(user_id: str) -> dict[str, Any]:
    cfg = load_billing_config()
    sub = await get_billing_store().get_subscription(user_id) or {}
    failures = int(sub.get("payment_failures") or 0) + 1
    first_failure = sub.get("first_failure_at") or datetime.now(timezone.utc).isoformat()
    updated = await mark_past_due(user_id)
    updated = await get_billing_store().save_subscription(
        user_id,
        {"payment_failures": failures, "first_failure_at": first_failure},
    )

    action = {"action": "retry", "notify": False}
    if cfg and cfg.dunning.enabled:
        days_since = failures
        for step in sorted(cfg.dunning.retry_schedule, key=lambda item: item.days):
            if days_since >= step.days:
                action = step.model_dump()
        if action.get("action") == "cancel":
            await cancel_subscription(user_id, at_period_end=False)
            await expire_subscription(user_id)
        elif action.get("degrade_features"):
            community = cfg.community_plan()
            if community is not None:
                await get_billing_store().save_subscription(
                    user_id,
                    {"plan_id": community.id, "feature_flags": community.feature_flags},
                )

    return {"subscription": updated, "dunning_action": action}


async def clear_dunning(user_id: str) -> dict[str, Any]:
    return await get_billing_store().save_subscription(
        user_id,
        {"status": "active", "payment_failures": 0, "first_failure_at": None},
    )
