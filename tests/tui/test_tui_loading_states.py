from keprix.tui.command_center.states import TUI_STATES, render_tui_state


def test_loading_states_have_retry_or_action_guidance() -> None:
    for state_id in ("loading_sessions", "loading_models", "loading_runtime_data"):
        state = TUI_STATES[state_id]
        rendered = render_tui_state(state)
        assert state.title.startswith("Loading")
        assert "Action:" in rendered
        assert "Wait" in rendered or state.retry_action


def test_terminal_too_small_state_is_specific() -> None:
    rendered = render_tui_state(TUI_STATES["terminal_too_small"])

    assert "40 columns" in rendered
    assert "10 rows" in rendered
