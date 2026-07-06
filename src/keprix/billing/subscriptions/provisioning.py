"""Apply plan feature flags to a subscription record."""

from __future__ import annotations

from keprix.billing.schema import PlanConfig
from keprix.billing.store import get_billing_store


async def provision_plan_features(user_id: str, plan: PlanConfig) -> dict[str, object]:
    sub = await get_billing_store().save_subscription(
        user_id,
        {
            "plan_id": plan.id,
            "feature_flags": plan.feature_flags,
            "seats": plan.seats,
        },
    )
    return {"user_id": user_id, "plan_id": plan.id, "feature_flags": sub.get("feature_flags")}
