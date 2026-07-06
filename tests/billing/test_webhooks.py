"""Tests for Stripe webhook dispatch and idempotency."""

from __future__ import annotations

import json

import pytest

from keprix.billing.webhooks.dispatcher import dispatch_webhook_event


@pytest.mark.asyncio
async def test_checkout_completed_creates_subscription():
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_unique_1",
                "subscription": "sub_test_unique_1",
                "metadata": {"user_id": "wh-user-1", "plan_id": "pro"},
            }
        },
    }
    result = await dispatch_webhook_event(event)
    assert result["ok"] is True
    assert result.get("duplicate") is not True


@pytest.mark.asyncio
async def test_webhook_idempotency():
    event = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_test_unique_1",
                "amount_paid": 5880,
                "currency": "gbp",
                "metadata": {"user_id": "wh-inv-1"},
            }
        },
    }
    first = await dispatch_webhook_event(event)
    second = await dispatch_webhook_event(event)
    assert first.get("duplicate") is not True
    assert second.get("duplicate") is True


@pytest.mark.asyncio
async def test_unknown_event_ignored():
    event = {"type": "unknown.event.kind", "id": "evt_unique_1", "data": {"object": {"id": "x-unique-1"}}}
    result = await dispatch_webhook_event(event)
    assert result.get("ignored") is True
