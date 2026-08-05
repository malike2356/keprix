"""Review mode screen for the last agent turn."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Markdown

from keprix.tui.clipboard import copy_text
from keprix.tui.command_center.review import ReviewReport, render_review_report


class ReviewMode(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_summary", "Copy"),
    ]

    def __init__(self, report: ReviewReport) -> None:
        super().__init__()
        self.report = report
        self.summary_text = render_review_report(report)

    def compose(self) -> ComposeResult:
        yield Markdown(f"```\n{self.summary_text}\n```", id="review-mode")

    def copy_summary(self) -> bool:
        return copy_text(self.summary_text)

    async def action_copy_summary(self) -> None:
        if self.copy_summary():
            self.notify("Review copied.")
        else:
            self.notify("Copy failed.")

    async def action_close(self) -> None:
        self.dismiss(None)
