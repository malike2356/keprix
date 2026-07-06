"""Tests for feature gate enforcement."""

from __future__ import annotations

import pytest

from keprix.billing.feature_gates.enforcer import check_feature
from keprix.billing.feature_gates.matrix import build_feature_matrix
from keprix.billing.subscriptions.lifecycle import activate_subscription


def test_feature_matrix_from_config():
    matrix = build_feature_matrix()
    assert "pro" in matrix
    assert matrix["pro"].get("tools_all") is True


@pytest.mark.asyncio
async def test_check_feature_on_active_plan():
    await activate_subscription("user-fg", plan_id="team")
    assert await check_feature("user-fg", "api_access") is True
    assert await check_feature("user-fg", "sso") is False


@pytest.mark.asyncio
async def test_support_tier_comparison():
    await activate_subscription("user-gov", plan_id="pro")
    assert await check_feature("user-gov", "support", min_value="email") is True
    assert await check_feature("user-gov", "support", min_value="priority") is False
