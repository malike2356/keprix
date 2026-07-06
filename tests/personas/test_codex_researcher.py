"""Tests for CODEX researcher module."""

from __future__ import annotations

import pytest

from keprix.personas.codex.researcher import (
    CodexResearcher,
    is_advice_request,
    is_out_of_depth,
)
from keprix.personas.codex.reviewer import LEGAL_INFORMATION_DISCLAIMER


@pytest.fixture
def researcher() -> CodexResearcher:
    return CodexResearcher(workspace_id="ws-codex", user_id="user-codex")


def test_refuses_direct_legal_advice_requests(researcher: CodexResearcher) -> None:
    assert is_advice_request("Should I sign this contract tomorrow?")
    answer = researcher.answer_question("Should I sign this contract tomorrow?", jurisdiction="England and Wales (UK)")
    assert answer.refused_advice
    assert answer.disclaimer == LEGAL_INFORMATION_DISCLAIMER
    assert "cannot tell you what you should do" in answer.information.lower()


def test_out_of_depth_refers_to_specialist(researcher: CodexResearcher) -> None:
    assert is_out_of_depth("What litigation strategy should we use in court filing?")
    answer = researcher.answer_question(
        "What litigation strategy should we use in court filing?",
        jurisdiction="England and Wales (UK)",
    )
    assert answer.out_of_depth
    assert answer.specialist_referral


def test_answer_states_jurisdiction(researcher: CodexResearcher) -> None:
    answer = researcher.answer_question(
        "What is a limitation of liability clause?",
        jurisdiction="England and Wales (UK)",
    )
    assert answer.jurisdiction == "England and Wales (UK)"
    assert "England and Wales (UK)" in answer.information


def test_generate_checklist_data_protection(researcher: CodexResearcher) -> None:
    checklist = researcher.generate_checklist("data_protection", jurisdiction="England and Wales (UK)")
    assert checklist["jurisdiction"] == "England and Wales (UK)"
    assert len(checklist["items"]) >= 4
    assert checklist["disclaimer"] == LEGAL_INFORMATION_DISCLAIMER


@pytest.mark.asyncio
async def test_track_regulatory_changes(researcher: CodexResearcher) -> None:
    update = await researcher.track_regulatory_changes(
        "UK GDPR enforcement",
        jurisdiction="United Kingdom",
        use_research=False,
        store=False,
    )
    assert update.topic == "UK GDPR enforcement"
    assert update.implications
    assert update.checked_at
