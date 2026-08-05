import pytest

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient
from keprix.tui.widgets.help_overlay import render_help_overlay


def _binding_map() -> dict[str, str]:
    return {binding.key: binding.action for binding in KeprixTuiApp.BINDINGS}


def test_required_keyboard_model_is_bound() -> None:
    bindings = _binding_map()

    assert bindings["ctrl+p"] == "command_palette"
    assert bindings["ctrl+space"] == "command_palette"
    assert bindings["ctrl+l"] == "search_transcript"
    assert bindings["ctrl+s"] == "focus_sessions"
    assert bindings["ctrl+m"] == "cycle_model"
    assert bindings["ctrl+r"] == "review_mode"
    assert bindings["ctrl+k"] == "flush_queue"
    assert bindings["?"] == "help"


def test_help_discovers_required_keys() -> None:
    help_text = render_help_overlay()

    for key in ("Ctrl+P", "Ctrl+Space", "Ctrl+L", "Ctrl+S", "Ctrl+M", "Ctrl+R", "Ctrl+K", "Esc", "?"):
        assert key in help_text


@pytest.mark.asyncio
async def test_help_action_is_reachable_offline(monkeypatch) -> None:
    output: list[str] = []
    app = KeprixTuiApp(client=KeprixClient())
    monkeypatch.setattr(app, "_log_system", output.append)

    await app.action_help()

    assert output
    assert "Keyboard" in output[0]


def test_search_action_primes_slash_search(monkeypatch) -> None:
    class FakeInput:
        value = ""
        cursor_position = 0

        def focus(self) -> None:
            self.focused = True

    fake = FakeInput()
    app = KeprixTuiApp(client=KeprixClient())
    monkeypatch.setattr(app, "_input_bar", lambda: fake)

    import asyncio

    asyncio.run(app.action_search_transcript())
    assert fake.value == "/search "
    assert fake.cursor_position == len(fake.value)
