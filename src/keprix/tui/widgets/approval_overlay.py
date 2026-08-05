"""Exec approval overlay for the Textual TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from keprix.tui.widgets.overlay_base import PromptOverlayBase


class ApprovalOverlay(PromptOverlayBase):
    """Modal dangerous-command approval prompt."""

    def __init__(
        self,
        *,
        approval_id: str,
        command: str,
        description: str = "",
        allow_permanent: bool = True,
    ) -> None:
        super().__init__()
        self.approval_id = approval_id
        self.command = command
        self.description = description
        self.allow_permanent = allow_permanent

    def compose(self) -> ComposeResult:
        hint = "Y/Enter approve once | N/Esc deny"
        if self.allow_permanent:
            hint += " | A approve always"
        with Vertical(id="prompt-frame"):
            yield Static("Approval required", id="prompt-title")
            if self.description:
                yield Static(self.description, id="prompt-description")
            yield Static(self.command, id="prompt-command")
            yield Static(hint, id="prompt-hint")

    def on_mount(self) -> None:
        self.focus()

    def on_key(self, event) -> None:
        key = event.key.lower()
        if key == "ctrl+c":
            self.dismiss("deny")
            event.stop()
            return
        if key in {"y", "enter"}:
            self.dismiss("once")
            event.stop()
            return
        if key == "a" and self.allow_permanent:
            self.dismiss("always")
            event.stop()
            return
        if key in {"n", "escape"}:
            self.dismiss("deny")
            event.stop()
