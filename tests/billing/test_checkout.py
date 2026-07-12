"""Tests for Stripe checkout session creation."""

from __future__ import annotations

import pytest

from keprix.billing.stripe.checkout import (
    create_checkout_session,
    create_donation_checkout,
    donation_amount_to_pence,
)
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
async def test_donation_checkout_default_one_pound():
    result = await create_donation_checkout(donation_id="coffee")
    assert result["checkout_url"].startswith("https://checkout.stripe.test/")
    assert result["donation"]["amount"] == 100
    assert result["donation"]["amount_gbp"] == 1.0
    assert result["donation"]["pricing"] == "price_data"


@pytest.mark.asyncio
async def test_donation_checkout_custom_amount():
    result = await create_donation_checkout(donation_id="coffee", amount_gbp=7.5)
    assert result["donation"]["amount"] == 750
    assert result["donation"]["amount_gbp"] == 7.5
    assert result["donation"]["pricing"] == "price_data"


@pytest.mark.asyncio
async def test_donation_amount_validation():
    assert donation_amount_to_pence(1) == 100
    assert donation_amount_to_pence("3.50") == 350
    with pytest.raises(ValueError, match="Minimum"):
        donation_amount_to_pence(0.5)
    with pytest.raises(ValueError, match="Maximum"):
        donation_amount_to_pence(501)


@pytest.mark.asyncio
async def test_donation_checkout_rejects_below_minimum():
    with pytest.raises(ValueError, match="Minimum"):
        await create_donation_checkout(amount_gbp=0.99)


@pytest.mark.asyncio
async def test_checkout_unknown_plan():
    with pytest.raises(ValueError, match="Unknown plan"):
        await create_checkout_session(user_id="u", email="u@example.com", plan_id="nope")
