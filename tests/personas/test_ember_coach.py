"""Tests for EMBER coach module."""

from __future__ import annotations

import pytest

from keprix.personas.ember.coach import (
    EmberCoach,
    detect_crisis_language,
    is_wellbeing_lane_owner,
)
from keprix.personas.nexus.project_tracker import Milestone, ProjectState


@pytest.fixture
def coach() -> EmberCoach:
    return EmberCoach(user_id="user-ember")


def test_detect_crisis_language() -> None:
    assert detect_crisis_language("I want to end my life")
    assert detect_crisis_language("Sometimes I think about self-harm")
    assert not detect_crisis_language("I am tired after a long week")


def test_crisis_response_signposts_resources(coach: EmberCoach) -> None:
    response = coach.coach("I want to kill myself")
    assert response.crisis.detected
    assert response.crisis.resources
    assert any("116 123" in resource for resource in response.crisis.resources)
    assert response.lane == "wellbeing"


def test_coaching_follows_ask_listen_reflect_suggest(coach: EmberCoach) -> None:
    response = coach.coach("Work has been overwhelming and I feel stuck.")
    assert response.ask
    assert response.listen
    assert response.reflect
    assert response.suggest
    assert not response.crisis.detected
    phases = response.to_dict()["phases"]
    assert phases["ask"] and phases["suggest"]


def test_persistent_negative_patterns_suggest_professional_help(coach: EmberCoach) -> None:
    response = coach.coach("Another hard day.", negative_checkin_streak=4)
    assert response.suggest_professional_help


@pytest.mark.asyncio
async def test_coaching_stored_in_wellbeing_vault(coach: EmberCoach) -> None:
    response = await coach.coach_and_store("I need help building a morning routine.")
    assert response.vault_item_id


def test_wellbeing_lane_excluded_from_status_report() -> None:
    state = ProjectState(
        workspace_id="ws",
        project_name="Demo",
        milestones=[
            Milestone(id="m1", title="Ship API", owner="FORGE"),
            Milestone(id="m2", title="Daily meditation", owner="EMBER"),
        ],
        agent_status={"FORGE": "active", "EMBER": "coaching"},
    )
    report = state.generate_status_report()
    assert "EMBER" not in report or "Agent Workstreams" in report
    assert "Ship API" in report
    assert "Daily meditation" not in report
    assert "| FORGE |" in report
    assert "| EMBER |" not in report


def test_is_wellbeing_lane_owner() -> None:
    assert is_wellbeing_lane_owner("EMBER")
    assert not is_wellbeing_lane_owner("FORGE")


def test_coach_does_not_share_with_work_agents(coach: EmberCoach) -> None:
    assert not coach.shares_with_work_agents()
