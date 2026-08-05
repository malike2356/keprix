from pathlib import Path

from keprix.tui.surpass_contract import required_surpass_failures, surpass_summary, tui_surpass_contract


def test_final_surpass_contract_has_no_required_failures() -> None:
    assert required_surpass_failures() == []
    assert surpass_summary() == "TUI surpass contracts: passed"


def test_command_center_proof_group_is_documented() -> None:
    doc = Path("docs/architecture/tui-surpass-hermes-contract.md").read_text(encoding="utf-8")

    assert "Command Center" in doc
    assert "keyboard model" in doc


def test_command_center_proof_group_lists_all_new_capabilities() -> None:
    item = next(item for item in tui_surpass_contract() if item.id == "command_center.01")
    text = item.why_it_surpasses.lower()

    for capability in (
        "command palette",
        "cockpit",
        "runtime timeline",
        "tool cards",
        "session map",
        "themes",
        "status bar",
        "review mode",
        "state views",
        "keyboard model",
    ):
        assert capability in text
