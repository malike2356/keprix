"""Tests for failed payment dunning."""

from __future__ import annotations

import pytest

from keprix.billing.subscriptions.dunning import clear_dunning, record_payment_failure
from keprix.billing.subscriptions.lifecycle import activate_subscription


@pytest.mark.asyncio
async def test_record_payment_failure_marks_past_due():
    await activate_subscription("user-dun", plan_id="pro")
    result = await record_payment_failure("user-dun")
    assert result["subscription"]["status"] == "past_due"
    assert result["subscription"]["payment_failures"] == 1
    assert "dunning_action" in result


@pytest.mark.asyncio
async def test_clear_dunning_restores_active():
    await activate_subscription("user-clear", plan_id="pro")
    await record_payment_failure("user-clear")
    sub = await clear_dunning("user-clear")
    assert sub["status"] == "active"
    assert sub["payment_failures"] == 0
