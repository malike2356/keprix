"""Tests for COMPASS strategist module."""

from __future__ import annotations

import pytest

from keprix.personas.compass.strategist import (
    CompassStrategist,
    MIN_CLARIFYING_QUESTIONS,
    StrategyFramework,
    generate_clarifying_questions,
    has_sufficient_clarification,
)


@pytest.fixture
def strategist() -> CompassStrategist:
    return CompassStrategist(workspace_id="ws-compass", user_id="user-compass")


def test_generate_clarifying_questions_minimum_count() -> None:
    questions = generate_clarifying_questions("B2B SaaS expansion")
    assert len(questions) >= MIN_CLARIFYING_QUESTIONS


def test_insufficient_answers_blocks_recommendation(strategist: CompassStrategist) -> None:
    session = strategist.formulate_recommendation(
        "Launch new product line",
        framework=StrategyFramework.SWOT,
        answers={"q0": "only one answer"},
    )
    assert not session.ready_for_recommendation
    assert len(session.clarifying_questions) >= MIN_CLARIFYING_QUESTIONS


def test_recommendation_includes_alternatives_and_tradeoffs(strategist: CompassStrategist) -> None:
    answers = {f"q{index}": f"answer {index}" for index in range(MIN_CLARIFYING_QUESTIONS)}
    session = strategist.formulate_recommendation(
        "European market entry",
        framework=StrategyFramework.SWOT,
        answers=answers,
    )
    assert session.ready_for_recommendation
    assert len(session.options) >= 2
    assert session.recommendation
    assert session.trade_offs
    rejected = [option for option in session.options if option.rejected_reason]
    assert rejected


def test_framework_output_visible_for_swot(strategist: CompassStrategist) -> None:
    answers = {f"q{index}": f"answer {index}" for index in range(MIN_CLARIFYING_QUESTIONS)}
    session = strategist.formulate_recommendation(
        "Partner strategy",
        framework=StrategyFramework.SWOT,
        answers=answers,
    )
    assert "swot" in session.framework_output
    assert "strengths" in session.framework_output["swot"]
    assert "SWOT" in session.markdown or "swot" in session.markdown.lower()


def test_assumptions_flagged_explicitly(strategist: CompassStrategist) -> None:
    answers = {f"q{index}": f"answer {index}" for index in range(MIN_CLARIFYING_QUESTIONS)}
    session = strategist.formulate_recommendation(
        "Pricing strategy",
        framework=StrategyFramework.OKR,
        answers=answers,
    )
    assert session.assumptions
    assert "Assumptions" in session.markdown


def test_quantified_estimates_present(strategist: CompassStrategist) -> None:
    answers = {f"q{index}": f"answer {index}" for index in range(MIN_CLARIFYING_QUESTIONS)}
    session = strategist.formulate_recommendation(
        "Channel strategy",
        framework=StrategyFramework.PORTER,
        answers=answers,
    )
    assert session.quantified_estimates
    assert any("usd" in key.lower() or "pct" in key.lower() for key in session.quantified_estimates)


@pytest.mark.asyncio
async def test_strategy_playbook_stores_document_when_ready(strategist: CompassStrategist) -> None:
    answers = {f"q{index}": f"answer {index}" for index in range(MIN_CLARIFYING_QUESTIONS)}
    result = await strategist.run_strategy_session(
        "Workspace analytics GTM",
        framework=StrategyFramework.V2MOM,
        answers=answers,
        store=True,
    )
    assert result.get("ready_for_recommendation")
    assert result.get("document_id")
    assert result.get("markdown")


def test_has_sufficient_clarification_helper() -> None:
    assert not has_sufficient_clarification({"a": "one"})
    assert has_sufficient_clarification({"a": "1", "b": "2", "c": "3"})
