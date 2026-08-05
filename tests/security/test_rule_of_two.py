"""Tests for Rule of Two scoring."""

from __future__ import annotations

from keprix.security.rule_of_two import record_leg, reset_state, should_require_human_approval


def test_rule_of_two_requires_approval_after_two_legs():
    reset_state("session-1")
    record_leg("session-1", private_data=True, tool_name="memory:search")
    assert not should_require_human_approval("session-1", tool_name="search:web")
    record_leg("session-1", untrusted_content=True, tool_name="web:fetch")
    assert should_require_human_approval("session-1", tool_name="terminal:run")

