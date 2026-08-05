"""Approval overlay tests (Prompt 202)."""

from __future__ import annotations

from keprix.api.web_ui_prompt_bridge import normalize_approval_decision


def test_normalize_approval_decision_once() -> None:
    assert normalize_approval_decision("Y") == "once"
    assert normalize_approval_decision("approve") == "once"


def test_normalize_approval_decision_always() -> None:
    assert normalize_approval_decision("A") == "always"


def test_normalize_approval_decision_deny() -> None:
    assert normalize_approval_decision("n") == "deny"
    assert normalize_approval_decision("") == "deny"


class _KeyEvent:
    def __init__(self, key: str) -> None:
        self.key = key
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def test_approval_overlay_yes_once() -> None:
    from keprix.tui.widgets.approval_overlay import ApprovalOverlay

    overlay = ApprovalOverlay(
        approval_id="ap1",
        command="rm -rf /tmp/demo",
        description="dangerous command",
    )
    captured: list[str] = []
    overlay.dismiss = captured.append  # type: ignore[method-assign]

    event = _KeyEvent("y")
    overlay.on_key(event)
    assert captured == ["once"]
    assert event.stopped is True


def test_approval_overlay_ctrl_c_denies() -> None:
    from keprix.tui.widgets.approval_overlay import ApprovalOverlay

    overlay = ApprovalOverlay(
        approval_id="ap1",
        command="rm -rf /tmp/demo",
    )
    captured: list[str] = []
    overlay.dismiss = captured.append  # type: ignore[method-assign]

    event = _KeyEvent("ctrl+c")
    overlay.on_key(event)
    assert captured == ["deny"]
    assert event.stopped is True
