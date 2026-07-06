"""Tests for responses input parsing."""

from __future__ import annotations

from keprix.public_api.agent_runtime import parse_responses_input


def test_parse_responses_input_with_instructions():
    parsed = parse_responses_input("hello", instructions="Be concise.")
    assert parsed.system_prompt == "Be concise."
    assert parsed.user_message == "hello"
