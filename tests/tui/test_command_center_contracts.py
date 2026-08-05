from __future__ import annotations

from pathlib import Path

from keprix.tui.command_center.contracts import (
    COMMAND_CENTER_CONTRACTS,
    command_center_contract_failures,
    command_center_contract_summary,
)
from keprix.tui.command_center.layout import COMMAND_CENTER_LAYOUT_ZONES, layout_zone


def test_layout_zones_cover_command_center_surfaces() -> None:
    zones = {zone.name for zone in COMMAND_CENTER_LAYOUT_ZONES}
    assert zones == {
        "cockpit",
        "transcript",
        "runtime_timeline",
        "sidebar",
        "status_bar",
        "overlay",
        "review_mode",
    }
    assert layout_zone("runtime_timeline").collapsible is True
    assert layout_zone("overlay").focusable is True


def test_command_center_contract_paths_exist() -> None:
    missing: list[str] = []
    for item in COMMAND_CENTER_CONTRACTS:
        for path in (item.implementation, item.test):
            if not Path(path).exists():
                missing.append(f"{item.id}:{path}")
    assert missing == []


def test_command_center_contract_summary_passes() -> None:
    assert command_center_contract_failures() == []
    assert command_center_contract_summary() == "Command Center contracts: passed"
