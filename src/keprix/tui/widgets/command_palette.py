"""Command palette overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static

from keprix.tui.command_center.actions import CommandCenterAction
from keprix.tui.command_center.palette import CommandPaletteModel, palette_status_line


class CommandPalette(ModalScreen[CommandCenterAction | None]):
    """Keyboard-first command palette."""

    DEFAULT_CSS = """
    CommandPalette {
        align: center top;
    }

    CommandPalette > Vertical {
        margin-top: 2;
        width: 90%;
        max-width: 100;
        height: 18;
        background: #001A00;
        border: solid #003B00;
        padding: 1 2;
    }

    #command-palette-title {
        color: #00FF41;
        text-style: bold;
        margin-bottom: 1;
    }

    #command-palette-input {
        margin-bottom: 1;
    }

    #command-palette-list {
        height: 1fr;
    }

    #command-palette-status {
        color: #008F11;
        margin-top: 1;
    }
    """

    def __init__(self, model: CommandPaletteModel) -> None:
        super().__init__()
        self.model = model

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Command Center", id="command-palette-title")
            yield Input(placeholder="Search commands, sessions, models, skills, plugins, files...", id="command-palette-input")
            yield ListView(*self._items(), id="command-palette-list")
            yield Static(palette_status_line(self.model), id="command-palette-status")

    def on_mount(self) -> None:
        self.query_one("#command-palette-input", Input).focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        self.model.set_query(event.value)
        await self._refresh()

    async def on_key(self, event) -> None:
        key = event.key.lower()
        if key in {"escape", "ctrl+c"}:
            self.dismiss(None)
            event.stop()
            return
        if key in {"down", "tab"}:
            self.model.move(1)
            await self._refresh()
            event.stop()
            return
        if key in {"up", "shift+tab"}:
            self.model.move(-1)
            await self._refresh()
            event.stop()
            return
        if key == "enter":
            selected = self.model.selected()
            self.dismiss(selected)
            event.stop()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id:
            raw = str(event.item.id)
            if raw.startswith("command-palette-item-"):
                try:
                    index = int(raw[len("command-palette-item-") :])
                except ValueError:
                    return
                results = self.model.results()
                if 0 <= index < len(results):
                    self.dismiss(results[index])

    async def _refresh(self) -> None:
        list_view = self.query_one("#command-palette-list", ListView)
        await list_view.clear()
        await list_view.extend(self._items())
        status = self.query_one("#command-palette-status", Static)
        status.update(palette_status_line(self.model))

    def _items(self) -> list[ListItem]:
        results = self.model.results()
        if not results:
            return [ListItem(Static(palette_status_line(self.model)), id="command-palette-item-empty")]
        items: list[ListItem] = []
        for index, action in enumerate(results):
            marker = ">" if index == self.model.selected_index else " "
            disabled = " [dim](unavailable)[/]" if action.disabled else ""
            text = f"{marker} [bold]{action.title}[/] [dim]{action.category}[/]{disabled}\n  [dim]{action.description}[/]"
            items.append(ListItem(Static(text), id=f"command-palette-item-{index}"))
        return items


__all__ = ["CommandPalette"]
