"""Subscription lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.subscriptions.provisioning import provision_plan_features


async def start_trial(user_id: str, plan_id: str) -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None:
        raise RuntimeError("Billing not configured")
    plan = cfg.plan_by_id(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")

    trial_days = cfg.product.trial_days
    trial_ends = None
    status = "active" if trial_days <= 0 else "trialing"
    if trial_days > 0:
        trial_ends = (datetime.now(timezone.utc) + timedelta(days=trial_days)).isoformat()

    sub = await get_billing_store().save_subscription(
        user_id,
        {
            "product_id": cfg.product.id,
            "plan_id": plan.id,
            "status": status,
            "seats": plan.seats,
            "feature_flags": plan.feature_flags,
            "trial_ends_at": trial_ends,
            "cancel_at_period_end": False,
        },
    )
    await provision_plan_features(user_id, plan)
    return sub


async def activate_subscription(user_id: str, *, plan_id: str, stripe_subscription_id: str | None = None) -> dict[str, Any]:
    cfg = load_billing_config()
    plan = cfg.plan_by_id(plan_id) if cfg else None
    payload: dict[str, Any] = {
        "status": "active",
        "plan_id": plan_id,
        "stripe_subscription_id": stripe_subscription_id,
        "cancel_at_period_end": False,
    }
    if plan is not None:
        payload["feature_flags"] = plan.feature_flags
        payload["seats"] = plan.seats
    sub = await get_billing_store().save_subscription(user_id, payload)
    if plan is not None:
        await provision_plan_features(user_id, plan)
    return sub


async def mark_past_due(user_id: str) -> dict[str, Any]:
    return await get_billing_store().save_subscription(user_id, {"status": "past_due"})


async def cancel_subscription(user_id: str, *, at_period_end: bool = True) -> dict[str, Any]:
    status = "active" if at_period_end else "cancelled"
    payload: dict[str, Any] = {"cancel_at_period_end": at_period_end}
    if not at_period_end:
        payload["status"] = "cancelled"
    return await get_billing_store().save_subscription(user_id, payload)


async def expire_subscription(user_id: str) -> dict[str, Any]:
    cfg = load_billing_config()
    community = cfg.community_plan() if cfg else None
    payload: dict[str, Any] = {"status": "expired", "cancel_at_period_end": False}
    if community is not None:
        payload["plan_id"] = community.id
        payload["feature_flags"] = community.feature_flags
        payload["seats"] = community.seats
    return await get_billing_store().save_subscription(user_id, payload)
