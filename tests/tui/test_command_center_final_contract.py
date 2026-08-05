from pathlib import Path

from keprix.tui.command_center.registry import build_default_registry
from keprix.tui.command_center.status import StatusSnapshot, render_status_bar
from keprix.tui.command_center.states import TUI_STATES
from keprix.tui.surpass_contract import tui_surpass_contract


def test_command_center_feature_files_exist() -> None:
    expected = [
        "src/keprix/tui/command_center/actions.py",
        "src/keprix/tui/command_center/palette.py",
        "src/keprix/tui/command_center/cockpit.py",
        "src/keprix/tui/command_center/runtime_timeline.py",
        "src/keprix/tui/renderer/tool_cards.py",
        "src/keprix/tui/sessions/map.py",
        "src/keprix/tui/theme_system.py",
        "src/keprix/tui/command_center/status.py",
        "src/keprix/tui/command_center/review.py",
        "src/keprix/tui/command_center/states.py",
    ]

    missing = [path for path in expected if not Path(path).is_file()]
    assert missing == []


def test_command_palette_mirrors_keyboard_actions() -> None:
    registry = build_default_registry()
    for action_id in ("ui:help", "ui:review", "runtime:flush-queue", "runtime:reconnect", "slash:/search", "slash:/model", "slash:/sessions"):
        assert action_id in registry.actions


def test_command_center_contract_surpass_item_is_present() -> None:
    item = next(item for item in tui_surpass_contract() if item.id == "command_center.01")

    assert item.status == "passed"
    assert item.required is True
    assert "command palette" in item.why_it_surpasses.lower()


def test_final_status_and_states_render_without_blank_copy() -> None:
    status = render_status_bar(StatusSnapshot(backend_healthy=True, model="mini"), width=100)

    assert len(status) == 100
    assert TUI_STATES["empty_transcript"].title == "No messages yet"
