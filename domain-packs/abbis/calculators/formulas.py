"""Canonical ABBIS calculation services from abbis/prompts/spec/07-calculator-formulas.md.

Numbers are deterministic. Agents may explain inputs/results but must not alter math.
"""

from __future__ import annotations

import math
from typing import Any

FORMULA_VERSION = "abbis-spec-07@1.0.0"

PIPE_LENGTH_M = 3.0
DEFAULT_OVERBURDEN_M = 45.0
STANDARD_ROD_LENGTH_M = 5.0
BUCKET_SIZE_L = 20.0
MARGIN_TARGET_LOW_PCT = 10.0
MARGIN_RISK_BUFFER_PCT = 50.0

PUMP_HP_RULES: list[tuple[float, float]] = [
    (50.0, 1.0),
    (80.0, 1.5),
    (200.0, 2.0),
]


def pipe_count(overburden_m: float, pipe_length_m: float = PIPE_LENGTH_M) -> int:
    if overburden_m < 0:
        raise ValueError("overburden_m must be >= 0")
    if pipe_length_m <= 0:
        raise ValueError("pipe_length_m must be > 0")
    return int(math.ceil(overburden_m / pipe_length_m))


def screen_plain_split(
    overburden_m: float,
    total_depth_m: float,
    *,
    pipe_length_m: float = PIPE_LENGTH_M,
) -> dict[str, Any]:
    if total_depth_m < overburden_m:
        raise ValueError("total_depth_m must be >= overburden_m")
    plain = pipe_count(overburden_m, pipe_length_m)
    screen = pipe_count(total_depth_m - overburden_m, pipe_length_m)
    return {
        "plain": plain,
        "screen": screen,
        "total": plain + screen,
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
    }


def depth_from_rods(rod_lengths_m: list[float]) -> float:
    return float(sum(rod_lengths_m))


def nominal_depth(rod_count: int, nominal_rod_m: float = STANDARD_ROD_LENGTH_M) -> float:
    return float(rod_count) * nominal_rod_m


def depth_error_pct(rod_lengths_m: list[float]) -> float:
    if not rod_lengths_m:
        return 0.0
    actual = depth_from_rods(rod_lengths_m)
    nominal = nominal_depth(len(rod_lengths_m))
    if nominal <= 0:
        return 0.0
    return ((nominal - actual) / nominal) * 100.0


def recommended_hp(depth_m: float) -> float | None:
    for max_depth, hp in PUMP_HP_RULES:
        if depth_m <= max_depth:
            return hp
    return None


def pe_hose_rolls(depth_m: float) -> dict[str, Any]:
    length = depth_m + 5.0
    roll = 100 if depth_m > 45 else 50
    return {
        "length_m": length,
        "rolls": int(math.ceil(length / roll)),
        "roll_length_m": roll,
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
    }


def bucket_fill_lpm(bucket_litres: float, fill_seconds: float) -> float:
    if fill_seconds <= 0:
        raise ValueError("fill_seconds must be > 0")
    return (bucket_litres / fill_seconds) * 60.0


def average_yield_lpm(fills: list[dict[str, Any]]) -> float:
    if not fills:
        raise ValueError("fills required")
    lpms = [bucket_fill_lpm(float(f["bucket_litres"]), float(f["fill_seconds"])) for f in fills]
    return sum(lpms) / len(lpms)


def pump_test_result(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    if not cycles:
        raise ValueError("cycles required")
    safe_pump = min(float(c["drawdown_minutes"]) for c in cycles)
    rest = max(float(c["recovery_minutes"]) for c in cycles)
    all_fills = [f for c in cycles for f in (c.get("bucket_fills") or [])]
    yield_lpm = average_yield_lpm(all_fills)
    cycle_window = safe_pump + rest
    cycles_per_day = int(1440 // cycle_window) if cycle_window > 0 else 0
    daily = cycles_per_day * yield_lpm * safe_pump
    return {
        "yield_lpm": round(yield_lpm, 1),
        "safe_pump_min": int(safe_pump),
        "rest_min": int(rest),
        "cycles_per_day": cycles_per_day,
        "daily_yield_litres": round(daily),
        "automation_needed": yield_lpm < 120,
        "timer_on_min": int(safe_pump),
        "timer_off_min": int(rest),
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
    }


def estimate_quote(inputs: dict[str, Any]) -> dict[str, Any]:
    """Build a contractor quote from cost components and margin."""
    overburden_m = float(inputs.get("overburden_m", DEFAULT_OVERBURDEN_M))
    depth_m = float(inputs.get("depth_m", overburden_m))
    margin_pct = float(inputs.get("margin_pct", 20.0))
    if margin_pct >= 100 or margin_pct < 0:
        raise ValueError("margin_pct must be in [0, 100)")

    location_unknown = bool(inputs.get("location_unknown", False))
    rig_rental = float(inputs.get("rig_rental_ghs", 0.0))
    if location_unknown:
        rig_rental *= 1.0 + (MARGIN_RISK_BUFFER_PCT / 100.0)
        overburden_m = float(inputs.get("overburden_m", DEFAULT_OVERBURDEN_M))

    split = screen_plain_split(overburden_m, depth_m)
    plain_price = float(inputs.get("plain_pipe_price_ghs", 250.0))
    screen_price = float(inputs.get("screen_pipe_price_ghs", 275.0))
    gravel_bag_price = float(inputs.get("gravel_bag_price_ghs", 40.0))
    accessories_flat = float(inputs.get("accessories_flat_ghs", 0.0))
    pump_cost = float(inputs.get("pump_cost_ghs", 0.0))
    pe_hose_cost = float(inputs.get("pe_hose_cost_ghs", 0.0))
    survey = float(inputs.get("survey_cost_ghs", 0.0))
    transport = float(inputs.get("transport_ghs", 0.0))
    labour = float(inputs.get("labour_ghs", 0.0))
    misc = float(inputs.get("misc_ghs", 0.0))

    gravel_bags = split["plain"] + split["screen"]
    materials = (
        split["plain"] * plain_price
        + split["screen"] * screen_price
        + gravel_bags * gravel_bag_price
        + pump_cost
        + pe_hose_cost
        + accessories_flat
    )
    subtotal = rig_rental + materials + survey + transport + labour + misc
    total_price = subtotal / (1.0 - margin_pct / 100.0)
    margin_ghs = total_price - subtotal
    hp = recommended_hp(depth_m)
    hose = pe_hose_rolls(depth_m)

    return {
        "overburden_m": overburden_m,
        "depth_m": depth_m,
        "pipes_plain": split["plain"],
        "pipes_screen": split["screen"],
        "pipes_total": split["total"],
        "gravel_bags": gravel_bags,
        "recommended_hp": hp,
        "pe_hose": hose,
        "materials_ghs": round(materials, 2),
        "subtotal_ghs": round(subtotal, 2),
        "margin_pct": margin_pct,
        "margin_ghs": round(margin_ghs, 2),
        "total_price_ghs": round(total_price, 2),
        "location_unknown": location_unknown,
        "currency": "GHS",
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
        "quote_prefix_forbidden": ["KB", "Kari"],
    }
