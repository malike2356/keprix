"""Model picker overlay for keprix TUI.

Scrollable model list grouped by provider with fuzzy search.
Matches Hermes's modelPicker.tsx pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


@dataclass
class ModelInfo:
    id: str
    provider: str
    name: str
    description: str = ""
    pricing_input: float = 0.0
    pricing_output: float = 0.0
    context_window: int = 0


class ModelPicker(ModalScreen[ModelInfo | None]):
    """Modal screen for selecting a model."""

    DEFAULT_CSS = """
    ModelPicker {
        align: center middle;
    }
    ModelPicker > Vertical {
        width: 60;
        height: 20;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    ModelPicker Input {
        margin-bottom: 1;
    }
    ModelPicker ListView {
        height: 1fr;
    }
    """

    def __init__(self, models: list[ModelInfo], **kwargs) -> None:
        super().__init__(**kwargs)
        self._models = models
        self._filtered: list[ModelInfo] = list(models)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold]Select Model[/] [dim](Esc to cancel)[/]")
            yield Input(placeholder="Search models...", id="model-search")
            yield ListView(*self._render_items(), id="model-list")

    async def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        self._filtered = [
            m for m in self._models
            if not query or query in m.name.lower() or query in m.provider.lower()
        ]
        list_view = self.query_one("#model-list", ListView)
        await list_view.clear()
        await list_view.extend(self._render_items())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id:
            raw = str(event.item.id)
            if raw.startswith("model-"):
                raw = raw[len("model-") :]
            try:
                index = int(raw)
            except ValueError:
                return
            if 0 <= index < len(self._filtered):
                self.dismiss(self._filtered[index])

    def _render_items(self) -> list[ListItem]:
        items = []
        for i, m in enumerate(self._filtered):
            provider_badge = f"[dim]{m.provider}[/]"
            context = f"[dim]{_fmt_context(m.context_window)}[/]" if m.context_window else ""
            items.append(ListItem(
                Static(f"{m.name}  {provider_badge} {context}"),
                id=f"model-{i}",
            ))
        return items


def _fmt_context(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens // 1_000}K ctx"
    if tokens >= 1_000:
        return f"{tokens // 1_000}K ctx"
    return f"{tokens} ctx"
