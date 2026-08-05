from keprix.tui.command_center.states import TUI_STATES, render_tui_state
from keprix.tui.hardening import state_for_http_status
from keprix.tui.widgets.state_view import StateView


def test_error_states_do_not_include_traceback_language() -> None:
    banned = ("Traceback", "AttributeError", "HTTPStatusError", "stack trace")

    for state_id in ("backend_offline", "auth_expired", "forbidden_action", "rate_limited", "server_error", "tool_failed"):
        rendered = render_tui_state(TUI_STATES[state_id])
        assert not any(item in rendered for item in banned)


def test_http_status_maps_to_actionable_state() -> None:
    assert state_for_http_status(401).id == "auth_expired"
    assert state_for_http_status(403).id == "forbidden_action"
    assert state_for_http_status(429).id == "rate_limited"
    assert state_for_http_status(500).id == "server_error"


def test_state_view_updates_rendered_text() -> None:
    widget = StateView("")
    widget.update_state(TUI_STATES["tool_failed"])

    assert "Tool failed" in str(widget.render())
