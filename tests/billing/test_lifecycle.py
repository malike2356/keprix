"""Tests for subscription lifecycle transitions."""

from __future__ import annotations

import pytest

from keprix.billing.store import get_billing_store
from keprix.billing.subscriptions.lifecycle import (
    activate_subscription,
    cancel_subscription,
    expire_subscription,
    start_trial,
)


@pytest.mark.asyncio
async def test_start_trial():
    sub = await start_trial("user-trial", "pro")
    assert sub["status"] == "trialing"
    assert sub["plan_id"] == "pro"
    assert sub.get("trial_ends_at")


@pytest.mark.asyncio
async def test_activate_subscription():
    sub = await activate_subscription("user-active", plan_id="team", stripe_subscription_id="sub_123")
    assert sub["status"] == "active"
    assert sub["stripe_subscription_id"] == "sub_123"
    flags = sub.get("feature_flags") or {}
    assert flags.get("api_access") is True


@pytest.mark.asyncio
async def test_cancel_at_period_end():
    await activate_subscription("user-cancel", plan_id="pro")
    sub = await cancel_subscription("user-cancel", at_period_end=True)
    assert sub["cancel_at_period_end"] is True
    assert sub["status"] == "active"


@pytest.mark.asyncio
async def test_expire_falls_back_to_community():
    await activate_subscription("user-expire", plan_id="team")
    sub = await expire_subscription("user-expire")
    assert sub["status"] == "expired"
    assert sub["plan_id"] == "community"
    stored = await get_billing_store().get_subscription("user-expire")
    assert stored is not None
    assert stored["plan_id"] == "community"
