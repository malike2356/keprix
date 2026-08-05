"""Clarify overlay helper tests (Prompt 202)."""

from __future__ import annotations

import pytest

from keprix.tui.widgets.clarify_overlay import choice_labels, format_choice_lines


def test_choice_labels_first_nine_are_digits() -> None:
    assert choice_labels(3) == ["1", "2", "3"]


def test_choice_labels_tenth_is_alpha() -> None:
    labels = choice_labels(10)
    assert labels[9] == "a"


def test_format_choice_lines_includes_other_option() -> None:
    text = format_choice_lines(["Alpha", "Beta"])
    assert "[1] Alpha" in text
    assert "[2] Beta" in text
    assert "[0] Other" in text


class _KeyEvent:
    def __init__(self, key: str) -> None:
        self.key = key
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def test_clarify_overlay_number_key_selects_choice() -> None:
    from keprix.tui.widgets.clarify_overlay import ClarifyOverlay

    overlay = ClarifyOverlay(
        clarify_id="abc",
        question="Pick one",
        choices=["Alpha", "Beta"],
    )
    captured: list[str] = []
    overlay.dismiss = captured.append  # type: ignore[method-assign]

    event = _KeyEvent("2")
    overlay.on_key(event)
    assert captured == ["Beta"]
    assert event.stopped is True


def test_clarify_overlay_ctrl_c_cancels() -> None:
    from keprix.tui.widgets.clarify_overlay import ClarifyOverlay

    overlay = ClarifyOverlay(
        clarify_id="abc",
        question="Pick one",
        choices=["Alpha", "Beta"],
    )
    captured: list[str] = []
    overlay.dismiss = captured.append  # type: ignore[method-assign]

    event = _KeyEvent("ctrl+c")
    overlay.on_key(event)
    assert captured == [""]
    assert event.stopped is True
