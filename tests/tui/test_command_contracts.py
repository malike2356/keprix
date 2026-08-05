from __future__ import annotations

from keprix.tui.commands.args import parse_slash_args
from keprix.tui.commands.completion import complete_local_commands
from keprix.tui.commands.history import CommandHistory
from keprix.tui.commands.preview import command_preview
from keprix.tui.commands.registry import local_command_metadata, slash_command_metadata


def test_all_local_commands_have_schema_metadata() -> None:
    metadata = local_command_metadata()
    assert len(metadata) >= 40
    assert all(item.name.startswith("/") for item in metadata)
    assert all(item.description for item in metadata)
    assert slash_command_metadata("/open") is not None


def test_completion_is_independent_from_rendering() -> None:
    items = complete_local_commands("/se")
    commands = [item.command for item in items]
    assert "/sessions" in commands
    assert "/setup" in commands
    assert all(item.description for item in items)


def test_preview_is_independent_from_dispatch() -> None:
    preview = command_preview("/open")
    assert "/open <url>" in preview
    assert "Open a URL" in preview


def test_args_and_history_are_stable() -> None:
    parsed = parse_slash_args('/tools --limit 5 "search term"')
    assert parsed.command == "/tools"
    assert parsed.flags["limit"] == "5"
    assert parsed.positional == ["search term"]
    history = CommandHistory(max_items=2)
    history.push("/help")
    history.push("/open https://example.com")
    history.push("/search invoice")
    assert history.recent() == ["/open https://example.com", "/search invoice"]
