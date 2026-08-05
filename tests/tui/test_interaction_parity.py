from __future__ import annotations

import pytest

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient
from keprix.tui.transcript_store import TranscriptItem, TranscriptStore
from keprix.tui.widgets.model_picker import ModelInfo, ModelPicker
from keprix.tui.widgets.slash_input import SlashCompletionOption


class _Panel:
    text = ""
    classes: set[str] = set()

    def update(self, text: str) -> None:
        self.text = text

    def add_class(self, name: str) -> None:
        self.classes.add(name)

    def remove_class(self, name: str) -> None:
        self.classes.discard(name)


def test_slash_picker_window_shows_selected_command_beyond_first_page() -> None:
    panel = _Panel()
    app = object.__new__(KeprixTuiApp)
    app._slash_suggestions_panel = lambda: panel  # type: ignore[method-assign]
    candidates = [
        SlashCompletionOption(command=f"/cmd{idx}", description=f"Command {idx}")
        for idx in range(20)
    ]

    app._set_completion_candidates(candidates, selected_index=17)

    assert "> /cmd17 - Command 17" in panel.text
    assert "20 matches. Keep typing to filter." in panel.text


@pytest.mark.asyncio
async def test_search_command_reads_current_transcript() -> None:
    class Log:
        def __init__(self) -> None:
            self.store = TranscriptStore()
            self.store.append(TranscriptItem.create(role="user", plain_text="You: find invoice", body="find invoice"))
            self.store.append(TranscriptItem.create(role="agent", plain_text="keprix: invoice found", body="invoice found"))

    app = KeprixTuiApp(client=KeprixClient(), session_id="s1")
    log = Log()
    output: list[str] = []
    app._message_log = lambda: log  # type: ignore[method-assign]
    app._log_system = output.append  # type: ignore[method-assign]
    app._setup_required = False
    app.connected = True

    await app._submit_text("/search invoice")

    assert output
    assert "2 transcript matches for: invoice" in output[-1]


def test_model_picker_uses_stable_string_item_ids() -> None:
    picker = ModelPicker([ModelInfo(id="m1", provider="local", name="Mini")])
    items = picker._render_items()
    assert items[0].id == "model-0"
