"""TUI setup handoff tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from keprix.tui.setup_handoff import run_setup_handoff


def test_run_setup_handoff_invokes_keprix_setup():
    with patch("keprix.tui.setup_handoff.subprocess.call", return_value=0) as call:
        code = run_setup_handoff("model")
    assert code == 0
    args, kwargs = call.call_args
    assert "setup" in args[0]
    assert "model" in args[0]
    assert kwargs["env"].get("KEPRIX_SETUP_REQUIRED") is None


def test_run_setup_handoff_without_section():
    with patch("keprix.tui.setup_handoff.subprocess.call", return_value=0) as call:
        code = run_setup_handoff()
    assert code == 0
    args, _kwargs = call.call_args
    assert args[0][-1] == "setup" or args[0][-2:] == ["setup"]
