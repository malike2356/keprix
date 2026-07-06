"""Tests for EMBER checkin module."""

from __future__ import annotations

import pytest

from keprix.personas.ember.checkin import (
    EmberCheckin,
    count_negative_checkin_streak,
    detect_burnout_signals,
)


@pytest.fixture
def checkin() -> EmberCheckin:
    return EmberCheckin(user_id="user-ember-checkin")


@pytest.mark.asyncio
async def test_submit_checkin_stores_in_vault(checkin: EmberCheckin) -> None:
    record = await checkin.submit_checkin(energy=3, stress=3, focus=3, sleep=3, mood=3)
    assert record.vault_item_id
    assert record.checkin_id


@pytest.mark.asyncio
async def test_checkin_history_lists_records(checkin: EmberCheckin) -> None:
    await checkin.submit_checkin(energy=4, stress=2, focus=4, sleep=4, mood=4)
    rows = await checkin.list_checkins()
    assert rows


def test_negative_checkin_streak_detection() -> None:
    records = [
        {"energy": 2, "mood": 2, "stress": 4},
        {"energy": 1, "mood": 2, "stress": 5},
    ]
    assert count_negative_checkin_streak(records) == 2


def test_burnout_signals_from_patterns() -> None:
    records = [
        {"energy": 2, "mood": 2, "stress": 4},
        {"energy": 1, "mood": 2, "stress": 5},
        {"energy": 2, "mood": 1, "stress": 4},
    ]
    signals = detect_burnout_signals(records)
    assert "declining_energy" in signals
    assert "increasing_stress" in signals


@pytest.mark.asyncio
async def test_low_scores_trigger_supportive_suggestion(checkin: EmberCheckin) -> None:
    record = await checkin.submit_checkin(energy=1, stress=5, focus=2, sleep=2, mood=1, notes="Rough week")
    assert "gentle" in record.reflection.lower() or "low" in record.reflection.lower()
    assert record.suggestion


def test_schedule_checkins_creates_cron_job(checkin: EmberCheckin, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_create_job(**kwargs):
        captured.update(kwargs)
        return {"id": "job-123", "enabled": True}

    monkeypatch.setattr("keprix.personas.ember.checkin.create_job", fake_create_job)
    schedule = checkin.schedule_checkins(frequency="daily", topics=["energy", "mood"])
    assert schedule.job_id == "job-123"
    assert schedule.frequency == "daily"
    assert "energy" in captured.get("prompt", "")


@pytest.mark.asyncio
async def test_run_scheduled_checkin_persists_record(checkin: EmberCheckin) -> None:
    record = await checkin.run_scheduled_checkin()
    assert record.vault_item_id
    assert "Scheduled" in record.notes


@pytest.mark.asyncio
async def test_burnout_assessment_returns_boundary_suggestions(checkin: EmberCheckin) -> None:
    await checkin.submit_checkin(energy=1, stress=5, focus=2, sleep=2, mood=1)
    await checkin.submit_checkin(energy=1, stress=5, focus=2, sleep=1, mood=1)
    assessment = await checkin.burnout_assessment()
    assert "signals" in assessment
    assert "negative_checkin_streak" in assessment
