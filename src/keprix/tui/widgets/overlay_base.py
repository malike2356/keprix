"""Shared helpers for TUI modal prompt overlays."""

from __future__ import annotations

from textual.screen import ModalScreen


class PromptOverlayBase(ModalScreen[str]):
    """Base modal screen for clarify and approval overlays."""

    DEFAULT_CSS = """
    PromptOverlayBase {
        align: center middle;
    }

    #prompt-frame {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: #001A00;
        border: solid #003B00;
        padding: 1 2;
        color: #00FF41;
    }

    #prompt-title {
        text-style: bold;
        color: #00FF41;
        margin-bottom: 1;
    }

    #prompt-body {
        color: #00CC33;
        margin-bottom: 1;
    }

    #prompt-hint {
        color: #008F11;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+c", "cancel", "Cancel"),
    ]

    def action_cancel(self) -> None:
        self.dismiss("")
