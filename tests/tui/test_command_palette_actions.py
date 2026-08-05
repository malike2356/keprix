from __future__ import annotations

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient, ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center.palette import CommandPaletteModel
from keprix.tui.runtime_events import PluginRuntimeItem, SkillRuntimeItem


def test_app_exposes_command_palette_keybindings() -> None:
    keys = {binding.key for binding in KeprixTuiApp.BINDINGS}
    assert "ctrl+p" in keys
    assert "ctrl+space" in keys


def test_app_command_center_registry_uses_live_sources() -> None:
    app = KeprixTuiApp(client=KeprixClient(), session_id="s1")
    app.sessions = [SessionItem(id="s1", title="Live session")]
    app.models = [ModelItem(id="mini", provider="local", name="Mini")]
    app._runtime_store.set_skills([SkillRuntimeItem(name="skill-a", description="Skill A")])
    app._runtime_store.set_plugins([PluginRuntimeItem(name="plugin-a", description="Plugin A", version="1")])
    registry = app._command_center_registry()
    assert registry.get("session:s1") is not None
    assert registry.get("model:mini") is not None
    assert registry.get("skill:skill-a") is not None
    assert registry.get("plugin:plugin-a") is not None


def test_palette_action_plan_can_insert_slash_command() -> None:
    model = CommandPaletteModel(KeprixTuiApp(client=KeprixClient())._command_center_registry(), query="/new")
    result = model.dispatch_selected()
    assert result is not None
    assert result.dispatch_kind == "insert_text"
    assert result.value.startswith("/new")
