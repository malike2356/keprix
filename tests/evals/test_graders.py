"""Grader tests (Prompt 57)."""

from __future__ import annotations

import pytest

from keprix.backend.evals.graders import (
    GraderType,
    GradingContext,
    all_passed,
    grade_exact_match,
    grade_json_schema,
    grade_llm_judge,
    grade_safety_violation,
    run_graders,
)
from keprix.backend.evals.trace import redact_dict, redact_value


def test_exact_match_grader():
    ctx = GradingContext(output="hello world")
    passed, reason = grade_exact_match(ctx, {"expected": "hello world"})
    assert passed is True
    assert reason is None


def test_json_schema_grader():
    ctx = GradingContext(output='{"name": "keprix", "version": 1}')
    passed, reason = grade_json_schema(ctx, {"schema": {"required": ["name", "version"]}})
    assert passed is True
    assert reason is None


def test_safety_violation_grader_blocks_unsafe():
    ctx = GradingContext(blocked=False)
    passed, reason = grade_safety_violation(ctx, {"expect_blocked": True})
    assert passed is False
    assert "not blocked" in (reason or "")


def test_llm_judge_rejected_as_sole_safety_grader():
    ctx = GradingContext(output="ok response here", safety_critical=True)
    results = run_graders(ctx, [{"type": GraderType.LLM_JUDGE, "criteria": "quality", "sole_grader": True}])
    assert results[0].passed is False
    assert "cannot be the only grader" in (results[0].reason or "")


def test_redaction_strips_secrets():
    payload = {
        "api_key": "sk-testsecretvalue1234567890",
        "message": "Bearer abc.def.ghi",
        "nested": {"token": "secret-token"},
    }
    redacted = redact_dict(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert "[REDACTED]" in redact_value("Authorization: Bearer abc123")


def test_all_passed_aggregates_grader_results():
    ctx = GradingContext(output="includes keyword", blocked=True)
    results = run_graders(
        ctx,
        [
            {"type": GraderType.SAFETY_VIOLATION, "expect_blocked": True},
            {"type": GraderType.HUMAN_RUBRIC, "items": ["keyword"]},
        ],
    )
    passed, reason = all_passed(results)
    assert passed is True
    assert reason is None
