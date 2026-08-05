"""Clarify prompt overlay for the Textual TUI."""

from __future__ import annotations

import string

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Static

from keprix.tui.formatting import plain_text
from keprix.tui.widgets.overlay_base import PromptOverlayBase


def choice_labels(count: int) -> list[str]:
    labels: list[str] = []
    for index in range(count):
        if index < 9:
            labels.append(str(index + 1))
        else:
            labels.append(string.ascii_lowercase[index - 9])
    return labels


def format_choice_lines(choices: list[str]) -> str:
    lines: list[str] = []
    labels = choice_labels(len(choices))
    for label, choice in zip(labels, choices, strict=False):
        lines.append(f"[{label}] {choice}")
    if choices:
        lines.append("[0] Other (type your answer)")
    return "\n".join(lines)


class ClarifyOverlay(PromptOverlayBase):
    """Modal clarify question with numbered choices and freeform fallback."""

    def __init__(
        self,
        *,
        clarify_id: str,
        question: str,
        choices: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.clarify_id = clarify_id
        self.question = question
        self.choices = list(choices or [])
        self._selected = 0
        self._freeform = not self.choices

    def compose(self) -> ComposeResult:
        with Vertical(id="prompt-frame"):
            yield Static("Clarify", id="prompt-title")
            yield Static(plain_text(self.question), id="prompt-body")
            if self.choices:
                yield Static(format_choice_lines(self.choices), id="prompt-choices")
            yield Input(placeholder="Type answer or press 1-9", id="prompt-input")
            yield Static(
                "Keys: 1-9 or a-z select | Enter confirm | Esc dismiss",
                id="prompt-hint",
            )

    def on_mount(self) -> None:
        if self._freeform:
            self.query_one("#prompt-input", Input).focus()
        else:
            self.focus()

    def _answer_for_label(self, label: str) -> str:
        if label == "0" and self.choices:
            text = self.query_one("#prompt-input", Input).value.strip()
            return text
        labels = choice_labels(len(self.choices))
        if label in labels:
            return self.choices[labels.index(label)]
        return self.query_one("#prompt-input", Input).value.strip()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        answer = event.value.strip()
        if not answer and self.choices:
            answer = self.choices[self._selected] if self.choices else ""
        self.dismiss(answer)

    def on_key(self, event) -> None:
        key = event.key.lower()
        if key == "ctrl+c":
            self.dismiss("")
            event.stop()
            return
        if key == "escape":
            self.dismiss("")
            event.stop()
            return
        if key.isdigit() and key != "0":
            index = int(key) - 1
            if 0 <= index < len(self.choices):
                self._selected = index
                self.dismiss(self.choices[index])
                event.stop()
                return
        if len(key) == 1 and key in string.ascii_lowercase:
            labels = choice_labels(len(self.choices))
            if key in labels:
                self.dismiss(self.choices[labels.index(key)])
                event.stop()
                return
        if key == "0" and self.choices:
            self._freeform = True
            self.query_one("#prompt-input", Input).focus()
            event.stop()
