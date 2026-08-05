from __future__ import annotations

from keprix.tui.renderer.tool_cards import render_tool_card, tool_card_from_runtime
from keprix.tui.widgets.tool_card import ToolCardWidget


def test_tool_card_expand_collapse_state_is_stable() -> None:
    card = tool_card_from_runtime(name="large", result="x" * 300)
    collapsed = render_tool_card(card, max_preview=40)
    expanded = render_tool_card(card.toggle(), max_preview=40)
    assert "Show more" in collapsed
    assert "state: collapsed" in collapsed
    assert "Show more" not in expanded
    assert "state: expanded" in expanded


def test_tool_card_widget_toggle_updates_state() -> None:
    widget = ToolCardWidget(tool_card_from_runtime(name="large", result="x" * 300))
    assert widget.card.expanded is False
    widget.toggle()
    assert widget.card.expanded is True
