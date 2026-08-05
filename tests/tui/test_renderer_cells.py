from __future__ import annotations

from keprix.tui.renderer.cells import Cell, cells_from_text


def test_cell_model_carries_terminal_metadata() -> None:
    cell = Cell.from_text("界", style="accent", link="https://example.com", selected=True, cursor=True, metadata_id="m1")
    assert cell.char == "界"
    assert cell.width == 2
    assert cell.style == "accent"
    assert cell.link == "https://example.com"
    assert cell.selected is True
    assert cell.cursor is True
    assert cell.metadata_id == "m1"


def test_cell_row_tracks_text_and_width() -> None:
    row = cells_from_text("a界", style="muted", metadata_id="row-1")
    assert row.text == "a界"
    assert row.width == 3
    assert {cell.style for cell in row.cells} == {"muted"}
    assert {cell.metadata_id for cell in row.cells} == {"row-1"}
