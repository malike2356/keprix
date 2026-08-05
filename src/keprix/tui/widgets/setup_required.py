"""Minimal one-screen setup overlay for unconfigured TUI launches."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Select, Static

from keprix.tui.widgets.overlay_base import PromptOverlayBase

SaveHandler = Callable[[str, str, str, str], Awaitable[tuple[bool, str]]]
HandoffHandler = Callable[[], Awaitable[int]]


class SetupRequiredOverlay(PromptOverlayBase):
    """Block chat until provider credentials are saved."""

    DEFAULT_CSS = PromptOverlayBase.DEFAULT_CSS + """
    #setup-provider {
        margin-bottom: 1;
    }

    #setup-key, #setup-url, #setup-model {
        margin-bottom: 1;
    }

    #setup-actions {
        color: #008F11;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        *,
        providers: list[dict[str, str]],
        docs_url: str,
        on_save: SaveHandler,
        on_handoff: HandoffHandler,
    ) -> None:
        super().__init__()
        self._providers = providers
        self._docs_url = docs_url
        self._on_save = on_save
        self._on_handoff = on_handoff
        self._selected_provider = providers[0]["id"] if providers else "openrouter"

    def compose(self) -> ComposeResult:
        options = [(row["label"], row["id"]) for row in self._providers]
        with Vertical(id="prompt-frame"):
            yield Static("Setup required", id="prompt-title")
            yield Static(
                "Configure a provider to start chatting. This is a minimal unblock; "
                "run full setup later for TTS, gateway, and tools.",
                id="prompt-body",
            )
            yield Select(options, id="setup-provider", value=self._selected_provider)
            yield Input(placeholder="API key (optional for Ollama)", password=True, id="setup-key")
            yield Input(placeholder="Base URL (custom / Ollama)", id="setup-url")
            yield Input(placeholder="Default model (optional)", id="setup-model")
            yield Static(
                "Enter save | f full setup | d docs | Esc exit",
                id="setup-actions",
            )

    def on_mount(self) -> None:
        self.query_one("#setup-key", Input).focus()

    def _selected(self) -> str:
        select = self.query_one("#setup-provider", Select)
        value = select.value
        if isinstance(value, Select.BLANK):
            return self._selected_provider
        return str(value)

    async def _submit(self) -> None:
        provider = self._selected()
        api_key = self.query_one("#setup-key", Input).value.strip()
        base_url = self.query_one("#setup-url", Input).value.strip()
        model = self.query_one("#setup-model", Input).value.strip()
        ok, message = await self._on_save(provider, api_key, base_url, model)
        if ok:
            self.dismiss({"ok": True, "message": message})
        else:
            self.query_one("#prompt-body", Static).update(message)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self._submit()

    async def on_key(self, event) -> None:
        key = event.key.lower()
        if key == "escape":
            self.dismiss({"ok": False, "exit": True})
            event.stop()
            return
        if key == "ctrl+c":
            self.dismiss({"ok": False, "exit": True})
            event.stop()
            return
        if key == "f":
            code = await self._on_handoff()
            if code == 0:
                self.dismiss({"ok": True, "handoff": True})
            else:
                self.query_one("#prompt-body", Static).update(
                    f"Setup handoff exited with code {code}."
                )
            event.stop()
            return
        if key == "d":
            self.query_one("#prompt-body", Static).update(f"Docs: {self._docs_url}")
            event.stop()
            return

    async def action_cancel(self) -> None:
        self.dismiss({"ok": False, "exit": True})
