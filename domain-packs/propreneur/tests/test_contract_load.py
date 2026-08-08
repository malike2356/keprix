from __future__ import annotations

import pytest

from tools.registry import (
    PropreneurContractVersionError,
    list_tool_names,
    load_action_risk_contract,
    load_tools_contract,
)


def test_tools_contract_loads() -> None:
    raw = load_tools_contract()
    assert raw["version"] == "1.0.0"
    names = list_tool_names()
    assert "propreneur-get-portfolio" in names
    assert "propreneur-propose-financial-log" in names


def test_rejects_wrong_expected_version() -> None:
    with pytest.raises(PropreneurContractVersionError):
        load_tools_contract(expected_version="9.9.9")


def test_action_risk_has_financial_explicit() -> None:
    risk = load_action_risk_contract()
    assert risk["classes"]["financial"]["default_approval"] == "explicit"
    assert "permanent_delete" in risk["always_require_explicit_approval"]
