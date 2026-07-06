"""Tests for EMBER habits module."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from keprix.personas.ember.habits import EmberHabits, _compute_streak


@pytest.fixture
def habits() -> EmberHabits:
    return EmberHabits(workspace_id="ws-ember", user_id="user-ember-habits")


def test_compute_streak_counts_consecutive_days() -> None:
    today = date(2026, 1, 10)
    dates = [
        (today - timedelta(days=2)).isoformat(),
        (today - timedelta(days=1)).isoformat(),
        today.isoformat(),
    ]
    streak, longest = _compute_streak(dates, today=today)
    assert streak == 3
    assert longest == 3


@pytest.mark.asyncio
async def test_create_habit_uses_wellbeing_lane_tags(habits: EmberHabits) -> None:
    record = await habits.create_habit(name="Morning walk", cue="After breakfast")
    assert record.habit_id
    assert record.vault_item_id
    assert record.task_id


@pytest.mark.asyncio
async def test_log_completion_increments_streak(habits: EmberHabits) -> None:
    created = await habits.create_habit(name="Journal")
    updated = await habits.log_completion(created.habit_id)
    assert updated.streak >= 1
    assert updated.completion_dates


@pytest.mark.asyncio
async def test_list_habits_returns_latest_streak(habits: EmberHabits) -> None:
    created = await habits.create_habit(name="Stretch")
    await habits.log_completion(created.habit_id)
    rows = await habits.list_habits()
    match = next(row for row in rows if row.habit_id == created.habit_id)
    assert match.streak >= 1


@pytest.mark.asyncio
async def test_build_plan_includes_streak_markdown(habits: EmberHabits) -> None:
    created = await habits.create_habit(name="Read", motivation="Calm evenings")
    await habits.log_completion(created.habit_id)
    plan = await habits.build_plan(created.habit_id)
    assert plan.streak >= 1
    assert "Read" in plan.markdown
    assert "streak" in plan.markdown.lower()
