"""Tests for Stripe checkout session creation."""

from __future__ import annotations

import pytest

from keprix.billing.stripe.checkout import create_checkout_session
from keprix.billing.stripe.products import sync_products_and_prices


@pytest.mark.asyncio
async def test_checkout_session_mock_mode():
    await sync_products_and_prices()
    result = await create_checkout_session(
        user_id="user-1",
        email="user@example.com",
        plan_id="pro",
        interval="month",
    )
    assert "checkout_url" in result
    assert result["checkout_url"].startswith("https://checkout.stripe.test/")


@pytest.mark.asyncio
async def test_checkout_unknown_plan():
    with pytest.raises(ValueError, match="Unknown plan"):
        await create_checkout_session(user_id="u", email="u@example.com", plan_id="nope")
