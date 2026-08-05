"""Tests for resilience/timeout_escalator.py."""

from __future__ import annotations

import pytest

from keprix.providers.resilience.timeout_escalator import TimeoutEscalator, TierTimeout


def test_default_ladder_first_tier_30s():
    esc = TimeoutEscalator()
    assert esc.for_tier(0) == 30.0


def test_default_ladder_second_tier_60s():
    esc = TimeoutEscalator()
    assert esc.for_tier(1) == 60.0


def test_clamps_to_last_for_out_of_range_index():
    esc = TimeoutEscalator(ladder=[30.0, 60.0, 120.0])
    assert esc.for_tier(10) == 120.0


def test_custom_ladder():
    esc = TimeoutEscalator(ladder=[10.0, 20.0, 40.0])
    assert esc.for_tier(0) == 10.0
    assert esc.for_tier(2) == 40.0


def test_for_tier_id_known():
    esc = TimeoutEscalator(
        ladder=[30.0, 60.0, 120.0],
        tier_ids=["premium", "subscription", "fallback"],
    )
    assert esc.for_tier_id("premium") == 30.0
    assert esc.for_tier_id("fallback") == 120.0


def test_for_tier_id_unknown_returns_last():
    esc = TimeoutEscalator(ladder=[30.0, 60.0], tier_ids=["a", "b"])
    assert esc.for_tier_id("unknown") == 60.0


def test_all_timeouts_returns_list():
    esc = TimeoutEscalator(
        ladder=[30.0, 60.0, 120.0],
        tier_ids=["t1", "t2", "t3"],
    )
    result = esc.all_timeouts()
    assert len(result) == 3
    assert all(isinstance(t, TierTimeout) for t in result)
    assert result[0].timeout_seconds == 30.0


def test_summary_returns_dict():
    esc = TimeoutEscalator(
        ladder=[30.0, 60.0],
        tier_ids=["fast", "slow"],
    )
    s = esc.summary()
    assert s == {"fast": 30.0, "slow": 60.0}
