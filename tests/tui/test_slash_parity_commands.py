from __future__ import annotations

from keprix.tui.slash_registry import local_completion_candidates


def test_hermes_style_commands_complete_without_prefix_only_matching() -> None:
    assert "/clear" in local_completion_candidates("/clr")
    assert "/model" in local_completion_candidates("/mdl")
    assert "/plugins" in local_completion_candidates("/plug")
    assert "/billing" in local_completion_candidates("/bill")
