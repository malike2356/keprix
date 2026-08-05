from __future__ import annotations

from keprix.tui.hardening import assert_no_traceback
from keprix.tui.widgets.help_overlay import render_help_overlay
from keprix.tui.widgets.queued_messages import QueuedMessagesState


def test_help_is_always_renderable_without_backend() -> None:
    help_text = render_help_overlay()
    assert "/help" in help_text
    assert_no_traceback(help_text)


def test_queue_never_silently_loses_user_text() -> None:
    state = QueuedMessagesState()
    state.enqueue("  hello  ")
    state.enqueue("")
    state.enqueue("world")
    assert state.messages == ["hello", "world"]
    assert state.flush() == ["hello", "world"]
    assert state.messages == []


def test_normal_error_copy_avoids_traceback_language() -> None:
    assert_no_traceback("Backend error. Retry after the service recovers.")
