"""Composer and slash command tests."""

from __future__ import annotations

import pytest

from keprix.tui.composer import InputHistory, MessageQueue
from keprix.tui.slash_commands import parse_slash


def test_message_queue_fifo() -> None:
    q = MessageQueue()
    q.enqueue("a")
    q.enqueue("b")
    assert q.pop() == "a"
    assert q.pop() == "b"


def test_input_history_navigation() -> None:
    history = InputHistory()
    history.push("first")
    history.push("second")
    history.begin_navigate("")
    assert history.previous() == "second"
    assert history.previous() == "first"
    assert history.next() == "second"
    assert history.next() == ""


def test_parse_slash() -> None:
    cmd, args = parse_slash("/queue show")
    assert cmd == "/queue"
    assert args == ["show"]
