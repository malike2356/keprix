"""Port of InvestmentSeriesMath.php - NPV and IRR (Newton-Raphson) on a
periodic cash-flow series, t=0,1,2,... (period 0 is typically the initial
outlay, negative)."""

from __future__ import annotations

import math


def npv(discount_rate_annual: float, cash_flows: list[float]) -> float:
    total = 0.0
    for t, cf in enumerate(cash_flows):
        total += float(cf) / ((1.0 + discount_rate_annual) ** t)
    return total


def irr_annual_decimal(cash_flows: list[float], guess: float = 0.1) -> float | None:
    has_positive = any(cf > 0 for cf in cash_flows)
    has_negative = any(cf < 0 for cf in cash_flows)
    if not has_positive or not has_negative:
        return None

    rate = guess
    for _ in range(80):
        npv_value = 0.0
        deriv = 0.0
        for t, cf in enumerate(cash_flows):
            cf = float(cf)
            disc = (1.0 + rate) ** t
            npv_value += cf / disc
            if t > 0:
                deriv += -t * cf / ((1.0 + rate) ** (t + 1))

        if not math.isfinite(npv_value) or not math.isfinite(deriv):
            return None
        if abs(deriv) < 1e-12:
            break

        rate_next = rate - npv_value / deriv
        if not math.isfinite(rate_next):
            return None
        if abs(rate_next - rate) < 1e-8:
            rate = rate_next
            break
        if rate_next < -0.9999 or rate_next > 10.0:
            return None
        rate = rate_next

    return rate if math.isfinite(rate) else None
