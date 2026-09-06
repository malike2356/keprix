import sqlite3

import pytest

from keprix.property_calculators import list_strategies
from keprix.property_calculators.service import run_workspace_calculator, update_calculator_settings
from keprix.property_calculators.registry import CalculatorError


def test_all_native_calculators_are_registered():
    assert len(list_strategies()) >= 28
    assert {item["slug"] for item in list_strategies()} >= {"btl", "sdlt", "mortgage", "rental_yield", "bridging"}


def test_workspace_calculator_override_is_isolated_and_auditable(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    inputs = {"purchase_price": 300000, "profile": "standard"}
    baseline = run_workspace_calculator("ws1", "sdlt", inputs, connection=connection)
    update_calculator_settings("ws1", {"sdlt_residential_bands": [{"up_to": None, "rate": 0.01}]}, connection=connection)
    changed = run_workspace_calculator("ws1", "sdlt", inputs, connection=connection)
    other = run_workspace_calculator("ws2", "sdlt", inputs, connection=connection)
    assert changed["inputs"] == inputs
    assert changed["result"] != baseline["result"]
    assert other["result"] == baseline["result"]


def test_workspace_settings_reject_out_of_range_ltv(tmp_path):
    connection = sqlite3.connect(tmp_path / "property.sqlite")
    with pytest.raises(CalculatorError):
        update_calculator_settings("ws1", {"mortgage_default_ltv_pct": 101}, connection=connection)
