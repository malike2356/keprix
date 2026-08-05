"""Tests for thinking block instructions."""

from __future__ import annotations

from types import SimpleNamespace

from agent.thinking_block import THINKING_BLOCK_INSTRUCTION, get_thinking_block_instruction


def test_thinking_block_contains_required_steps():
    for phrase in (
        "<thinking>",
        "ponytail-ladder",
        "Which tool can provide this",
        "Do not show the thinking block",
    ):
        assert phrase in THINKING_BLOCK_INSTRUCTION


def test_thinking_block_can_be_disabled_on_agent():
    agent = SimpleNamespace(_thinking_block=False)
    assert get_thinking_block_instruction(agent) == ""
