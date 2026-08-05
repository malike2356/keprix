from __future__ import annotations

from keprix.tui.client import ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center.palette import CommandPaletteModel, dispatch_for_action, palette_status_line
from keprix.tui.command_center.registry import build_default_registry


def test_palette_search_includes_required_source_types() -> None:
    registry = build_default_registry(
        sessions=[SessionItem(id="s1", title="Client work")],
        models=[ModelItem(id="mini", provider="local", name="Mini")],
        skills=[RegistryItem(name="research", description="Research skill")],
        plugins=[RegistryItem(name="git", description="Git plugin")],
        recent_files=["notes.md"],
    )
    kinds = {action.kind for action in registry.all()}
    assert {"slash", "session", "model", "skill", "plugin", "file", "runtime", "help"}.issubset(kinds)


def test_palette_fuzzy_search_and_selection() -> None:
    model = CommandPaletteModel(build_default_registry(), query="hlp")
    results = model.results()
    assert results
    assert results[0].kind in {"slash", "help"}
    original = model.selected()
    model.move(1)
    assert model.selected() != original
    model.move(-1)
    assert model.selected() == original


def test_palette_empty_loading_and_error_states() -> None:
    model = CommandPaletteModel(build_default_registry(), query="zzzzzz-no-match")
    assert model.state == "empty"
    assert palette_status_line(model) == "No matching actions."
    model.loading = True
    assert model.state == "loading"
    assert palette_status_line(model) == "Loading actions..."
    model.loading = False
    model.error = "Backend unavailable"
    assert model.state == "error"
    assert palette_status_line(model) == "Backend unavailable"


def test_palette_dispatch_plans_match_action_types() -> None:
    registry = build_default_registry(
        sessions=[SessionItem(id="s1", title="Session")],
        models=[ModelItem(id="mini", provider="local", name="Mini")],
        recent_files=["README.md"],
    )
    slash = registry.get("slash:/help")
    assert slash is not None
    assert dispatch_for_action(slash).dispatch_kind == "insert_text"
    session = registry.get("session:s1")
    assert session is not None
    assert dispatch_for_action(session).dispatch_kind == "switch_session"
    model = registry.get("model:mini")
    assert model is not None
    assert dispatch_for_action(model).dispatch_kind == "switch_model"
    runtime = registry.get("runtime:interrupt")
    assert runtime is not None
    assert dispatch_for_action(runtime).dispatch_kind == "runtime_action"
