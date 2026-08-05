from __future__ import annotations

import importlib

from keprix.tui.client import ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center import CommandCenterAction, CommandCenterState, build_default_registry
from keprix.tui.command_center.actions import action_id
from keprix.tui.command_center.registry import CommandCenterRegistry
from keprix.tui.command_center.telemetry import UiTelemetryBuffer, UiTelemetryEvent


def test_command_center_package_imports_without_side_effects() -> None:
    module = importlib.import_module("keprix.tui.command_center")
    assert module.CommandCenterAction is CommandCenterAction


def test_action_model_has_search_text_and_stable_id() -> None:
    action = CommandCenterAction(
        id=action_id("runtime", "Interrupt Turn"),
        title="Interrupt turn",
        description="Stop the current turn",
        kind="runtime",
        category="Runtime",
        keywords=("stop", "cancel"),
    )
    assert action.id == "runtime:interrupt-turn"
    assert "cancel" in action.search_text()
    assert "runtime" in action.search_text()


def test_registry_includes_all_foundation_sources() -> None:
    registry = build_default_registry(
        sessions=[SessionItem(id="s1", title="Build", preview="Prompt work")],
        models=[ModelItem(id="mini", provider="local", name="Mini", context_window=4096)],
        skills=[RegistryItem(name="research", description="Research skill")],
        plugins=[RegistryItem(name="git", description="Git plugin")],
        recent_files=["README.md"],
    )
    kinds = {action.kind for action in registry.all()}
    assert {"slash", "session", "model", "skill", "plugin", "file", "runtime", "help"}.issubset(kinds)
    assert registry.get("session:s1") is not None
    assert registry.search("research")[0].kind == "skill"


def test_registry_search_is_pure_and_ranked() -> None:
    registry = CommandCenterRegistry()
    registry.add(CommandCenterAction("a", "Alpha", "First", "ui"))
    registry.add(CommandCenterAction("b", "Beta", "Second", "ui"))
    assert [action.id for action in registry.search("alp")] == ["a"]
    assert [action.id for action in registry.search("", limit=1)] == ["a"]


def test_state_model_tracks_command_center_surface() -> None:
    state = CommandCenterState(
        active_surface="palette",
        selected_action_id="runtime:interrupt",
        focus_target="overlay",
        transport_mode="http",
        current_session_id="s1",
        queue_depth=2,
        runtime_status="busy",
        theme="Keprix Matrix",
    )
    assert state.overlay_open is True
    next_state = state.with_updates(active_surface="chat", focus_target="input")
    assert next_state.overlay_open is False
    assert next_state.queue_depth == 2


def test_local_telemetry_buffer_is_bounded() -> None:
    buffer = UiTelemetryBuffer(max_items=2)
    buffer.record(UiTelemetryEvent("a", "palette"))
    buffer.record(UiTelemetryEvent("b", "palette"))
    buffer.record(UiTelemetryEvent("c", "palette"))
    assert [event.action_id for event in buffer.snapshot()] == ["b", "c"]
