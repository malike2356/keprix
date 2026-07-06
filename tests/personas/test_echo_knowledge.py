"""Tests for ECHO knowledge module."""

from __future__ import annotations

import pytest

from keprix.personas.echo.knowledge import BusinessProfile, EchoKnowledge, UNKNOWN_ANSWER


@pytest.fixture
def knowledge() -> EchoKnowledge:
    profile = BusinessProfile(
        business_name="Acme Ltd",
        hours="Monday to Friday, 9am to 5pm",
        location="10 High Street, London",
        services="Consulting and support services",
        pricing_note="Packages start from GBP 500 per month.",
    )
    return EchoKnowledge(workspace_id="ws-echo", user_id="user-echo", profile=profile)


@pytest.mark.asyncio
async def test_answer_hours_from_profile(knowledge: EchoKnowledge) -> None:
    answer = await knowledge.answer_question("What are your opening hours?")
    assert "9am to 5pm" in answer.answer
    assert answer.source == "profile"


@pytest.mark.asyncio
async def test_answer_location_from_profile(knowledge: EchoKnowledge) -> None:
    answer = await knowledge.answer_question("Where are you located?")
    assert "High Street" in answer.answer


@pytest.mark.asyncio
async def test_unknown_question_does_not_guess(knowledge: EchoKnowledge) -> None:
    answer = await knowledge.answer_question("Do you support quantum fax machines?")
    assert answer.answer == UNKNOWN_ANSWER
    assert answer.confidence == 0.0


def test_detect_topic(knowledge: EchoKnowledge) -> None:
    assert knowledge.detect_topic("How much does it cost?") == "pricing"
    assert knowledge.detect_topic("What services do you offer?") == "services"
