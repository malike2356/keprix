"""Tests for team seat limits."""

from __future__ import annotations

import pytest

from keprix.billing.subscriptions.lifecycle import activate_subscription
from keprix.billing.subscriptions.seats import invite_seat, remove_seat, seat_limit_for_user


@pytest.mark.asyncio
async def test_seat_limit_from_plan():
    await activate_subscription("owner-1", plan_id="team")
    limit = await seat_limit_for_user("owner-1")
    assert limit == 10


@pytest.mark.asyncio
async def test_invite_and_remove_seat():
    await activate_subscription("owner-2", plan_id="team")
    seat = await invite_seat("owner-2", email="member@example.com", role="member")
    assert seat["status"] == "invited"
    removed = await remove_seat("owner-2", seat["id"])
    assert removed is True


@pytest.mark.asyncio
async def test_seat_limit_enforced():
    owner = "owner-seat-limit"
    await activate_subscription(owner, plan_id="community")
    await invite_seat(owner, email="one@example.com")
    with pytest.raises(ValueError, match="Seat limit"):
        await invite_seat(owner, email="two@example.com")
