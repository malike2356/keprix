from __future__ import annotations

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient, ModelItem, RegistryItem, SessionItem
from keprix.tui.command_center.cockpit import build_cockpit_state, render_workspace_cockpit
from keprix.tui.widgets.workspace_cockpit import WorkspaceCockpit


def test_cockpit_state_contains_operational_sections() -> None:
    state = build_cockpit_state(
        session_id="s1",
        sessions=[SessionItem(id="s1", title="Client build", preview="Work")],
        model="mini",
        models=[ModelItem(id="mini", provider="local", name="Mini")],
        transport_mode="http",
        connected=True,
        queue_depth=2,
        skills=[RegistryItem(name="research", description="Research")],
        plugins=[RegistryItem(name="git", description="Git")],
    )
    rendered = render_workspace_cockpit(state)
    assert "Keprix Command Center" in rendered
    assert "Session: Client build (s1)" in rendered
    assert "Model: mini" in rendered
    assert "Runtime: http | Backend: online" in rendered
    assert "Queue: 2" in rendered
    assert "research" in rendered
    assert "git" in rendered
    assert "Quick actions" in rendered


def test_cockpit_quick_actions_are_command_center_actions() -> None:
    state = build_cockpit_state()
    assert state.quick_actions
    assert {action.kind for action in state.quick_actions} >= {"runtime", "help"}


def test_workspace_cockpit_widget_updates_and_hides() -> None:
    widget = WorkspaceCockpit("")
    state = build_cockpit_state(connected=True)
    widget.update_state(state, visible=True)
    assert widget.display is True
    widget.update_state(state, visible=False)
    assert widget.display is False


def test_app_builds_cockpit_state_from_live_sources() -> None:
    app = KeprixTuiApp(client=KeprixClient(model="mini"), session_id="s1")
    app.connected = True
    app.sessions = [SessionItem(id="s1", title="Active")]
    app.models = [ModelItem(id="mini", provider="local", name="Mini")]
    state = app._build_cockpit_state()
    assert state.active_session_title == "Active"
    assert state.selected_model == "mini"
    assert state.backend_health == "online"
