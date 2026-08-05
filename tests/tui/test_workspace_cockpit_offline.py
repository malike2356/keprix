from __future__ import annotations

from keprix.tui.command_center.cockpit import build_cockpit_state, render_workspace_cockpit


def test_offline_cockpit_renders_without_traceback() -> None:
    state = build_cockpit_state(connected=False, transport_mode="http")
    rendered = render_workspace_cockpit(state)
    assert "Backend: offline" in rendered
    assert "Traceback" not in rendered
    assert "No recent sessions" in rendered


def test_setup_warning_is_actionable() -> None:
    state = build_cockpit_state(setup_required=True, connected=False)
    rendered = render_workspace_cockpit(state)
    assert "Provider setup required. Use /setup." in rendered
