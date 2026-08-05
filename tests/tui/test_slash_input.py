"""Slash input widget tests."""

from __future__ import annotations

import pytest

from keprix.tui.widgets.slash_input import SlashCompletionOption, SlashInput


@pytest.mark.asyncio
async def test_printable_key_delegates_to_textual_input() -> None:
    from textual.app import App, ComposeResult

    class Host(App):
        def compose(self) -> ComposeResult:
            yield SlashInput(id="input-bar")

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("h")
        widget = app.query_one("#input-bar", SlashInput)
        assert widget.value == "h"


@pytest.mark.asyncio
async def test_typing_slash_loads_visible_candidates() -> None:
    from textual.app import App, ComposeResult

    seen: list[tuple[list[SlashCompletionOption], int]] = []

    async def complete(prefix: str) -> list[str]:
        assert prefix == "/"
        return ["/help", "/clear"]

    class Host(App):
        def compose(self) -> ComposeResult:
            yield SlashInput(
                id="input-bar",
                complete_slash=complete,
                on_completion_candidates=lambda candidates, index: seen.append((candidates, index)),
            )

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("/")
        await pilot.pause(0.25)
        assert seen[-1] == (
            [SlashCompletionOption("/help"), SlashCompletionOption("/clear")],
            0,
        )


@pytest.mark.asyncio
async def test_cycle_completion_moves_selection_without_rewriting_input() -> None:
    from textual.app import App, ComposeResult

    async def complete(prefix: str) -> list[str]:
        return ["/clear", "/model"]

    class Host(App):
        def compose(self) -> ComposeResult:
            yield SlashInput(id="input-bar", complete_slash=complete)

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        widget = app.query_one("#input-bar", SlashInput)
        widget.value = "/clr"
        assert await widget.cycle_completion() is True
        assert widget.value == "/clr"
        assert widget.apply_selected_completion() is True
        assert widget.value == "/clear "


@pytest.mark.asyncio
async def test_down_and_enter_select_slash_candidate() -> None:
    from textual.app import App, ComposeResult

    seen: list[tuple[list[SlashCompletionOption], int]] = []

    async def complete(prefix: str) -> list[str]:
        return ["/clear", "/model"]

    class Host(App):
        def compose(self) -> ComposeResult:
            yield SlashInput(
                id="input-bar",
                complete_slash=complete,
                on_completion_candidates=lambda candidates, index: seen.append((candidates, index)),
            )

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        widget = app.query_one("#input-bar", SlashInput)
        widget.value = "/"
        await pilot.press("down")
        assert seen[-1] == (
            [SlashCompletionOption("/clear"), SlashCompletionOption("/model")],
            0,
        )
        await pilot.press("down")
        assert seen[-1] == (
            [SlashCompletionOption("/clear"), SlashCompletionOption("/model")],
            1,
        )
        await pilot.press("enter")
        assert widget.value == "/model "


@pytest.mark.asyncio
async def test_completion_accepts_descriptions() -> None:
    from textual.app import App, ComposeResult

    seen: list[tuple[list[SlashCompletionOption], int]] = []

    async def complete(prefix: str) -> list[SlashCompletionOption]:
        return [SlashCompletionOption("/clear", "Clear the transcript")]

    class Host(App):
        def compose(self) -> ComposeResult:
            yield SlashInput(
                id="input-bar",
                complete_slash=complete,
                on_completion_candidates=lambda candidates, index: seen.append((candidates, index)),
            )

    app = Host()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("/")
        await pilot.pause(0.25)
        assert seen[-1][0][0].description == "Clear the transcript"
