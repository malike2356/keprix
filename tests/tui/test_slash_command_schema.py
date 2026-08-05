from __future__ import annotations

from keprix.tui.slash_registry import local_command_metadata, slash_command_metadata


def test_every_local_slash_command_has_interaction_metadata() -> None:
    metadata = local_command_metadata()
    assert metadata
    for item in metadata:
        assert item.name.startswith("/")
        assert item.description.strip()
        assert item.examples
        assert item.source in {"local", "backend", "skill", "plugin", "system"}
        assert item.handler_kind in {"local", "backend", "panel", "turn", "external"}
        assert item.danger_level


def test_command_metadata_resolves_aliases_and_args() -> None:
    clear = slash_command_metadata("/clear")
    assert clear is not None
    assert clear.description == "Clear the transcript"

    open_cmd = slash_command_metadata("/open")
    assert open_cmd is not None
    assert open_cmd.args == "<url>"
    assert "/open https://example.com" in open_cmd.examples

    quit_cmd = slash_command_metadata("/q")
    assert quit_cmd is not None
    assert quit_cmd.name == "/quit"

