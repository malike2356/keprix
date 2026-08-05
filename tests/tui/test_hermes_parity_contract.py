from __future__ import annotations

from pathlib import Path

from keprix.tui.parity_contract import contract_summary, required_contract_failures, tui_parity_contract
from keprix.tui.slash_registry import local_command_metadata


def test_tui_parity_contract_is_complete() -> None:
    items = tui_parity_contract()
    assert len(items) == 100
    assert len({item.id for item in items}) == len(items)
    assert required_contract_failures() == []
    assert contract_summary() == "TUI parity contracts: 100/100 passed"


def test_tui_parity_contract_references_existing_files() -> None:
    for item in tui_parity_contract():
        assert Path(item.keprix_implementation).exists(), item.id
        assert Path(item.test_reference).exists(), item.id


def test_local_slash_commands_have_full_metadata() -> None:
    for item in local_command_metadata():
        assert item.name.startswith("/")
        assert item.description.strip()
        assert item.examples
        assert item.source
        assert item.handler_kind
        assert item.danger_level

