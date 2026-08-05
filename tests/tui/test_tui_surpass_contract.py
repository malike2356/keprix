from __future__ import annotations

from pathlib import Path

from keprix.tui.surpass_contract import required_surpass_failures, surpass_summary, tui_surpass_contract


def test_surpass_contract_has_required_groups() -> None:
    groups = {item.id.split(".", 1)[0] for item in tui_surpass_contract()}
    assert groups == {
        "granularity",
        "renderer",
        "runtime_transport",
        "performance",
        "reliability",
        "terminal_matrix",
        "developer_experience",
        "command_center",
        "look_and_feel_boundary",
    }


def test_required_surpass_contracts_have_no_failures() -> None:
    assert required_surpass_failures() == []
    assert surpass_summary() == "TUI surpass contracts: passed"


def test_surpass_contract_paths_exist() -> None:
    missing: list[str] = []
    for item in tui_surpass_contract():
        for path in (item.implementation, item.test):
            if path.endswith("boundary"):
                continue
            if path.startswith("Keprix "):
                continue
            if not Path(path).exists():
                missing.append(f"{item.id}:{path}")
    assert missing == []


def test_visual_identity_boundary_is_documented_and_enforced() -> None:
    doc = Path("docs/architecture/tui-surpass-hermes-contract.md").read_text(encoding="utf-8")
    assert "Keprix keeps its own look and feel" in doc
    assert "Hermes has a custom renderer" in doc
    assert "different by design" in doc
    forbidden_visual_claims = ("must copy Hermes UI", "Hermes visual identity copied")
    assert not any(claim in doc for claim in forbidden_visual_claims)


def test_surpass_contract_uses_plain_ascii_style() -> None:
    paths = [
        Path("src/keprix/tui/surpass_contract.py"),
        Path("docs/architecture/tui-surpass-hermes-contract.md"),
        Path("tests/tui/test_tui_surpass_contract.py"),
        Path("scripts/check-tui-surpass-hermes.sh"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "\u2013" not in text
        assert "\u2014" not in text
        for char in text:
            code = ord(char)
            assert not (0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF), path
