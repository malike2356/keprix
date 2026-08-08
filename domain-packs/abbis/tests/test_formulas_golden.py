"""Golden formula fixtures from abbis/prompts/spec/07-calculator-formulas.md."""

from __future__ import annotations

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK_ROOT))

from calculators.formulas import (  # noqa: E402
    estimate_quote,
    pe_hose_rolls,
    pipe_count,
    pump_test_result,
    recommended_hp,
    screen_plain_split,
)


def test_pipe_count_golden_table() -> None:
    assert pipe_count(5) == 2
    assert pipe_count(20) == 7
    assert pipe_count(45) == 15
    assert pipe_count(50) == 17


def test_screen_plain_split_60_30() -> None:
    split = screen_plain_split(30, 60)
    assert split["plain"] == 10
    assert split["screen"] == 10
    assert split["total"] == 20


def test_pump_yield_fixture_20l_10s() -> None:
    result = pump_test_result(
        [
            {
                "drawdown_minutes": 15,
                "recovery_minutes": 45,
                "bucket_fills": [{"bucket_litres": 20, "fill_seconds": 10}],
            }
        ]
    )
    assert result["yield_lpm"] == 120.0
    assert result["cycles_per_day"] == 24
    assert result["daily_yield_litres"] == 43200
    assert result["automation_needed"] is False


def test_quote_margin_math() -> None:
    quote = estimate_quote(
        {
            "overburden_m": 45,
            "depth_m": 60,
            "margin_pct": 20,
            "rig_rental_ghs": 10000,
            "plain_pipe_price_ghs": 250,
            "screen_pipe_price_ghs": 275,
            "gravel_bag_price_ghs": 0,
            "pump_cost_ghs": 0,
            "pe_hose_cost_ghs": 0,
        }
    )
    assert quote["pipes_plain"] == 15
    assert quote["pipes_screen"] == 5
    assert quote["currency"] == "GHS"
    assert quote["total_price_ghs"] > quote["subtotal_ghs"]
    assert abs(quote["margin_ghs"] - (quote["total_price_ghs"] - quote["subtotal_ghs"])) < 0.01


def test_pump_hp_and_hose() -> None:
    assert recommended_hp(50) == 1.0
    assert recommended_hp(80) == 1.5
    assert recommended_hp(200) == 2.0
    assert recommended_hp(250) is None
    hose = pe_hose_rolls(45)
    assert hose["roll_length_m"] == 50
    assert hose["rolls"] == 1
