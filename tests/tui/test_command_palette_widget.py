from __future__ import annotations

from keprix.tui.command_center.palette import CommandPaletteModel
from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.widgets.command_palette import CommandPalette


def test_command_palette_widget_constructs_with_results() -> None:
    model = CommandPaletteModel(build_default_registry(), query="/he")
    widget = CommandPalette(model)
    items = widget._items()
    assert items
    assert model.state == "ready"


def test_command_palette_widget_empty_state_is_stable() -> None:
    model = CommandPaletteModel(build_default_registry(), query="no-match-for-this")
    widget = CommandPalette(model)
    items = widget._items()
    assert len(items) == 1
    assert model.state == "empty"


def test_command_palette_widget_navigation_changes_selected_index() -> None:
    model = CommandPaletteModel(build_default_registry())
    widget = CommandPalette(model)
    assert widget.model.selected_index == 0
    widget.model.move(1)
    assert widget.model.selected_index == 1
