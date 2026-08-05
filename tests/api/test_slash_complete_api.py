"""API tests for slash tab completion (Prompt 205)."""

from __future__ import annotations

from keprix.tui.slash_registry import local_completion_candidates


def test_local_completion_sorted() -> None:
    candidates = local_completion_candidates("/")
    assert candidates == sorted(candidates)
    assert "/help" in candidates
