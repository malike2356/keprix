"""TUI app helper tests."""

from __future__ import annotations

from keprix.tui.app import session_id_from_list_item, session_list_item_id
from keprix.tui.app import KeprixTuiApp
from keprix.tui.widgets.slash_input import SlashCompletionOption


def test_session_list_item_id_prefixes_uuid() -> None:
    session_id = "4e32d9ab-82ab-43b5-adab-c23b51777b0a"
    widget_id = session_list_item_id(session_id)
    assert widget_id.startswith("session-")
    assert widget_id[0].isalpha()
    assert session_id_from_list_item(widget_id) == session_id


def test_slash_suggestions_include_descriptions_and_more_hint() -> None:
    class Panel:
        text = ""
        classes: set[str] = set()

        def update(self, text: str) -> None:
            self.text = text

        def add_class(self, name: str) -> None:
            self.classes.add(name)

        def remove_class(self, name: str) -> None:
            self.classes.discard(name)

    panel = Panel()
    app = object.__new__(KeprixTuiApp)
    app._slash_suggestions_panel = lambda: panel  # type: ignore[method-assign]
    candidates = [
        SlashCompletionOption(f"/cmd{idx}", f"Description {idx}")
        for idx in range(14)
    ]

    app._set_completion_candidates(candidates, 13)

    assert "Slash commands" in panel.text
    assert "> /cmd13 - Description 13" in panel.text
    assert "14 matches. Keep typing to filter." in panel.text
    assert "visible" in panel.classes
