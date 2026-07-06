"""Tests for public API agent runtime helpers."""

from __future__ import annotations

import pytest

from keprix.public_api.agent_runtime import parse_openai_messages


def test_parse_openai_messages_extracts_user_and_history():
    parsed = parse_openai_messages(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "second"},
        ]
    )
    assert parsed.system_prompt == "You are helpful."
    assert parsed.user_message == "second"
    assert len(parsed.history) == 2
    assert parsed.session_id.startswith("api-")


def test_parse_openai_messages_requires_user_message():
    with pytest.raises(ValueError, match="No user message"):
        parse_openai_messages([{"role": "assistant", "content": "only assistant"}])
