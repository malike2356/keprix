"""Transcript selection tests (Prompt 204)."""

from __future__ import annotations

from keprix.tui.clipboard import copy_text
from keprix.tui.selection import TranscriptLineMap, TranscriptSelection
from keprix.tui.transcript_store import TranscriptItem, TranscriptStore


def _store_with_messages() -> TranscriptStore:
    store = TranscriptStore()
    store.append(TranscriptItem.create(role="user", plain_text="You: hello", body="hello"))
    store.append(TranscriptItem.create(role="agent", plain_text="keprix: world", body="world"))
    return store


def test_selected_text_spans_user_and_agent() -> None:
    store = _store_with_messages()
    line_map = TranscriptLineMap.from_store(store)
    selection = TranscriptSelection()
    selection.start_at(2, 0)
    selection.extend_to(line_map.line_count - 2, 5)
    text = selection.selected_text(line_map)
    assert "hello" in text
    assert "world" in text
    assert "[" not in text


def test_empty_selection_copy_returns_false() -> None:
    assert copy_text("") is False


def test_collapsed_selection_is_not_active() -> None:
    selection = TranscriptSelection()
    selection.start_at(1, 1)
    assert selection.is_active is False


def test_cell_at_respects_scroll_offset() -> None:
    store = TranscriptStore()
    for index in range(10):
        store.append(
            TranscriptItem.create(role="system", plain_text=f"line-{index}", body=f"line-{index}")
        )
    line_map = TranscriptLineMap.from_store(store)
    selection = TranscriptSelection()
    row, col = selection.cell_at(
        local_y=2,
        local_x=3,
        scroll_y=5,
        line_map=line_map,
        padding_top=1,
        padding_left=2,
    )
    assert row == 6
    assert col == 1


def test_selection_survives_line_map_rebuild() -> None:
    store = _store_with_messages()
    line_map = TranscriptLineMap.from_store(store)
    selection = TranscriptSelection()
    selection.start_at(1, 0)
    selection.extend_to(3, 4)
    store.append(TranscriptItem.create(role="system", plain_text="later", body="later"))
    rebuilt = TranscriptLineMap.from_store(store)
    assert selection.selected_text(rebuilt)
