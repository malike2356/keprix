"""Port of PropertyFinancialService.php - UK yield/ROI/SDLT maths shared
across many calculators. Every calculator that needs this logic calls these
same functions rather than duplicating the arithmetic (prompt 154's own
"port shared helper once" acceptance criterion)."""

from __future__ import annotations

from keprix.property_calculators.constants import (
    SDLT_COMMERCIAL,
    SDLT_FIRST_TIME_BUYER_ABOVE_NIL_RATE,
    SDLT_FIRST_TIME_BUYER_NIL_THRESHOLD,
    SDLT_FIRST_TIME_BUYER_RELIEF_MAX_PRICE,
    SDLT_RESIDENTIAL_ADDITIONAL,
    SDLT_RESIDENTIAL_STANDARD,
    compute_progressive_tax,
)


def gross_yield_percent(monthly_rent: float | None, property_value: float | None) -> float | None:
    if monthly_rent is None or property_value is None or property_value <= 0:
        return None
    return round((monthly_rent * 12 / property_value) * 100, 4)


def net_yield_percent(
    monthly_rent: float | None, property_value: float | None, annual_costs: float | None
) -> float | None:
    if monthly_rent is None or property_value is None or property_value <= 0:
        return None
    annual_rent = monthly_rent * 12
    costs = annual_costs or 0.0
    net_income = annual_rent - costs
    return round((net_income / property_value) * 100, 4)


def roi_percent(annual_cashflow: float | None, total_investment: float | None) -> float | None:
    if annual_cashflow is None or total_investment is None or total_investment <= 0:
        return None
    return round((annual_cashflow / total_investment) * 100, 4)


def stamp_duty_standard_residential(price: float, bands: list[dict] | None = None) -> float:
    return compute_progressive_tax(price, bands or SDLT_RESIDENTIAL_STANDARD)


def stamp_duty_additional_property(price: float, bands: list[dict] | None = None) -> float:
    return compute_progressive_tax(price, bands or SDLT_RESIDENTIAL_ADDITIONAL)


def stamp_duty_commercial(price: float) -> float:
    return compute_progressive_tax(price, SDLT_COMMERCIAL)


def stamp_duty_first_time_buyer(price: float, bands: list[dict] | None = None) -> float:
    if price <= 0:
        return 0.0
    if price > SDLT_FIRST_TIME_BUYER_RELIEF_MAX_PRICE:
        return stamp_duty_standard_residential(price, bands)
    if price <= SDLT_FIRST_TIME_BUYER_NIL_THRESHOLD:
        return 0.0
    return round((price - SDLT_FIRST_TIME_BUYER_NIL_THRESHOLD) * SDLT_FIRST_TIME_BUYER_ABOVE_NIL_RATE, 2)


def stamp_duty_residential(price: float, profile: str, bands: list[dict] | None = None) -> float:
    if profile == "additional_property":
        return stamp_duty_additional_property(price, bands)
    if profile == "first_time_buyer":
        return stamp_duty_first_time_buyer(price, bands)
    return stamp_duty_standard_residential(price, bands)
