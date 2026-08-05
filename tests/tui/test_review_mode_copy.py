from keprix.tui.command_center.review import ReviewReport
from keprix.tui.widgets.review_mode import ReviewMode


def test_review_mode_copy_returns_rendered_summary(monkeypatch) -> None:
    copied: list[str] = []

    def fake_copy(text: str) -> bool:
        copied.append(text)
        return True

    monkeypatch.setattr("keprix.tui.widgets.review_mode.copy_text", fake_copy)
    screen = ReviewMode(ReviewReport(user_request_summary="Request", assistant_outcome_summary="Outcome"))

    assert screen.copy_summary() is True
    assert copied == [screen.summary_text]
    assert "Request" in copied[0]
