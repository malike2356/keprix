"""Local slash registry tests (Prompt 205)."""

from __future__ import annotations

from keprix.tui.slash_registry import is_local_slash_command, local_completion_candidates


def test_help_is_local() -> None:
    assert is_local_slash_command("/help") is True


def test_memory_is_not_local() -> None:
    assert is_local_slash_command("/memory") is False


def test_local_completion_prefix() -> None:
    matches = local_completion_candidates("/bu")
    assert "/busy" in matches
