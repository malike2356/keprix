from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.command_center.states import STATE_IDS, TUI_STATES, render_tui_state, state_has_safe_copy


def test_all_required_tui_states_are_represented() -> None:
    assert tuple(TUI_STATES) == STATE_IDS
    for state_id in STATE_IDS:
        state = TUI_STATES[state_id]
        assert state.title
        assert state.explanation
        assert state.suggested_action
        assert state_has_safe_copy(state)


def test_state_action_ids_resolve_when_present() -> None:
    registry = build_default_registry()
    known = set(registry.actions)

    missing = [
        state.command_palette_action_id
        for state in TUI_STATES.values()
        if state.command_palette_action_id and state.command_palette_action_id not in known
    ]

    assert missing == []


def test_rendered_state_copy_is_compact() -> None:
    rendered = render_tui_state(TUI_STATES["backend_offline"])

    assert "Backend offline" in rendered
    assert "Action:" in rendered
    assert len(rendered.splitlines()) <= 5
