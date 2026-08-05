"""Inline tool card widget."""

from __future__ import annotations

from textual.widgets import Static

from keprix.tui.renderer.tool_cards import ToolCard, render_tool_card


class ToolCardWidget(Static):
    """Compact expandable tool card."""

    DEFAULT_CSS = """
    ToolCardWidget {
        background: #001A00;
        color: #00CC33;
        border: solid #003B00;
        padding: 1 2;
        height: auto;
    }
    """

    def __init__(self, card: ToolCard, **kwargs) -> None:
        super().__init__(render_tool_card(card), **kwargs)
        self.card = card

    def toggle(self) -> None:
        self.card = self.card.toggle()
        self.update(render_tool_card(self.card))


__all__ = ["ToolCardWidget"]
