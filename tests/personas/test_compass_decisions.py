"""Tests for COMPASS decisions module."""

from __future__ import annotations

import pytest

from keprix.personas.compass.decisions import (
    CompassDecisions,
    DecisionCriterion,
    DecisionOptionScore,
    MIN_CLARIFYING_QUESTIONS,
    generate_decision_questions,
)


@pytest.fixture
def decisions() -> CompassDecisions:
    return CompassDecisions(workspace_id="ws-compass", user_id="user-compass")


def test_generate_decision_questions_minimum() -> None:
    questions = generate_decision_questions("Build vs buy")
    assert len(questions) >= MIN_CLARIFYING_QUESTIONS


def test_evaluate_decision_produces_weighted_totals(decisions: CompassDecisions) -> None:
    result = decisions.evaluate_decision(
        "Expand to US market",
        clarifying_answers={f"q{index}": "answer" for index in range(MIN_CLARIFYING_QUESTIONS)},
        store=False,
    )
    assert result.weighted_totals
    assert len(result.options) >= 2
    assert result.recommendation
    assert result.alternatives


def test_decision_includes_quantified_cost_benefit(decisions: CompassDecisions) -> None:
    result = decisions.evaluate_decision(
        "Acquire smaller competitor",
        clarifying_answers={f"q{index}": "answer" for index in range(MIN_CLARIFYING_QUESTIONS)},
        base_impact_usd=200_000,
        store=False,
    )
    assert result.cost_benefit["estimated_cost_usd"] > 0
    assert result.cost_benefit["estimated_benefit_usd"] == 200_000
    assert "roi_pct" in result.cost_benefit


def test_scenarios_include_probabilities_and_impacts(decisions: CompassDecisions) -> None:
    plan = decisions.plan_scenarios("Launch premium tier", base_impact_usd=150_000)
    assert len(plan.scenarios) == 3
    total_probability = sum(scenario.probability_pct for scenario in plan.scenarios)
    assert abs(total_probability - 100.0) < 0.01
    assert plan.expected_value_usd > 0
    assert plan.assumptions


def test_workspace_payload_includes_matrix_table(decisions: CompassDecisions) -> None:
    result = decisions.evaluate_decision(
        "Platform rebuild",
        clarifying_answers={f"q{index}": "answer" for index in range(MIN_CLARIFYING_QUESTIONS)},
        store=False,
    )
    payload = result.to_workspace_payload()
    assert payload["tables"]
    assert payload["charts"]


def test_custom_criteria_and_options(decisions: CompassDecisions) -> None:
    criteria = [
        DecisionCriterion("Speed", 0.5),
        DecisionCriterion("Cost", 0.5),
    ]
    options = [
        DecisionOptionScore("Fast", {"Speed": 9.0, "Cost": 4.0}),
        DecisionOptionScore("Cheap", {"Speed": 5.0, "Cost": 9.0}),
    ]
    result = decisions.evaluate_decision(
        "Vendor selection",
        criteria=criteria,
        options=options,
        clarifying_answers={f"q{index}": "answer" for index in range(MIN_CLARIFYING_QUESTIONS)},
        store=False,
    )
    assert "Fast" in result.weighted_totals
    assert "Cheap" in result.weighted_totals


def test_premortem_risks_generated(decisions: CompassDecisions) -> None:
    result = decisions.evaluate_decision(
        "Hire sales team",
        clarifying_answers={f"q{index}": "answer" for index in range(MIN_CLARIFYING_QUESTIONS)},
        store=False,
    )
    assert result.premortem_risks
