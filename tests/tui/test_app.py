"""TUI app helper tests."""

from __future__ import annotations

from keprix.tui.app import session_id_from_list_item, session_list_item_id


def test_session_list_item_id_prefixes_uuid() -> None:
    session_id = "4e32d9ab-82ab-43b5-adab-c23b51777b0a"
    widget_id = session_list_item_id(session_id)
    assert widget_id.startswith("session-")
    assert widget_id[0].isalpha()
    assert session_id_from_list_item(widget_id) == session_id
