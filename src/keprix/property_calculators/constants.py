"""Config, not hardcoded constants (prompt 154's own acceptance criterion).

Ported from propreneur/config/property_constants.php (SDLT/CGT/mortgage/HMO
regulatory constants, HMRC-sourced, versioned) and propreneur/config/
calculators.php (defaults, verdict/illustrative bands). Single source of
truth every calculator reads from - change a value here (or via the
workspace override table, see aiva_property_calculator_settings.py) and
every calculator that uses it changes with no code deploy, same pattern
prompt 137/139 already established for outreach engine config.
"""

from __future__ import annotations

from typing import Any

# ---- SDLT (England and NI residential). Source: HMRC, last updated
# October 2024 Budget. Cumulative "up_to" bands, rate as a decimal fraction
# (0.05 = 5%), matching config/property_constants.php exactly. ----
SDLT_RULES_VERSION = "2024-09_england_ni_residential"

SDLT_RESIDENTIAL_STANDARD: list[dict[str, Any]] = [
    {"up_to": 250_000, "rate": 0.00},
    {"up_to": 925_000, "rate": 0.05},
    {"up_to": 1_500_000, "rate": 0.10},
    {"up_to": None, "rate": 0.12},
]

SDLT_RESIDENTIAL_ADDITIONAL: list[dict[str, Any]] = [
    {"up_to": 250_000, "rate": 0.05},
    {"up_to": 925_000, "rate": 0.10},
    {"up_to": 1_500_000, "rate": 0.15},
    {"up_to": None, "rate": 0.17},
]

SDLT_COMMERCIAL: list[dict[str, Any]] = [
    {"up_to": 150_000, "rate": 0.00},
    {"up_to": 250_000, "rate": 0.02},
    {"up_to": None, "rate": 0.05},
]

SDLT_FIRST_TIME_BUYER_RELIEF_MAX_PRICE = 625_000
SDLT_FIRST_TIME_BUYER_NIL_THRESHOLD = 425_000
SDLT_FIRST_TIME_BUYER_ABOVE_NIL_RATE = 0.05

# ---- CGT (2024/25 tax year) ----
CGT_ANNUAL_EXEMPTION = 3_000
CGT_RESIDENTIAL_RATE_BASIC = 0.18
CGT_RESIDENTIAL_RATE_HIGHER = 0.24

# ---- Mortgage / bridging defaults ----
MORTGAGE_DEFAULT_STRESS_TEST_RATE = 0.085
MORTGAGE_DEFAULT_LTV = 0.75
MORTGAGE_STRESS_TEST_RATE_OFFSET = 0.03
MORTGAGE_DEFAULT_INTEREST_RATE = 0.055
MORTGAGE_DEFAULT_TERM_YEARS = 25
BRIDGING_DEFAULT_MONTHLY_RATE = 0.0075
BRIDGING_DEFAULT_LTV = 0.75

# ---- HMO room sizes (England, Housing Act 2004) ----
HMO_MIN_ROOM_SIZE_SQM_SINGLE = 6.51
HMO_MIN_ROOM_SIZE_SQM_DOUBLE = 10.22
HMO_MIN_ROOM_SIZE_SQM_CHILD = 4.64

# ---- Calculator defaults + illustrative/verdict bands (calculators.php) ----
DEFAULT_CONFIG: dict[str, Any] = {
    "mortgage_default_ltv_pct": 75,
    "mortgage_default_rate_pct": 5.5,
    "mortgage_default_term_years": 25,
    "bridging_default_monthly_rate_pct": 0.75,
    "bridging_default_arrangement_fee_pct": 2,
    "bridging_default_exit_fee_pct": 0,
    "r2r_ten_percent_rule_pct": 10,
    "r2r_default_occupancy_pct": 90,
    "r2r_default_management_pct": 10,
    "r2r_default_deposit_weeks": 5,
    "r2r_min_monthly_income_pct": 50,
    "hmo_default_occupancy_pct": 95,
    "hmo_default_management_pct": 10,
    "default_legal_purchase": 1500,
    "default_survey_cost": 600,
    "default_broker_fee": 500,
    "default_legal_remortgage": 800,
    "flip_default_agent_fee_pct": 1.25,
    "brr_default_ltv": 75,
    "brr_default_refinance_rate": 5.5,
    "brr_default_term_years": 25,
    "brr_default_management_pct": 10,
    "brr_default_void_weeks_pa": 2,
    "brr_default_maintenance_pa": 0,
    "sourcing_default_tax_rate_pct": 20,
    "sa_default_occupancy_pct": 75,
    "sa_default_ota_commission_pct": 15,
    "sa_default_management_pct": 0,
    "scenario_default_management_pct": 10,
    "scenario_default_occupancy_pct": 90,
    "scenario_default_void_weeks_pa": 2,
    "scenario_default_cost_model": "exclude_mortgage",
    "single_let_default_management_pct": 10,
    "single_let_default_maintenance_voids_pct": 5,
    "area_comparison_weights": {
        "yield": 30,
        "price_growth": 25,
        "demand": 20,
        "liquidity": 15,
        "affordability": 10,
    },
    "outcome_min_roi_pct": 10,
    "outcome_min_net_monthly_cashflow": 0,
    "illustrative_dscr_min": 1.25,
    "illustrative_ltv_btl_band_pct": 75,
    "illustrative_ltv_upper_band_pct": 80,
    "illustrative_breakeven_strong_pct": 70,
    "illustrative_breakeven_moderate_pct": 75,
    "illustrative_cap_rate_min_pct": 4,
    "illustrative_coc_strong_pct": 8,
    "illustrative_coc_moderate_pct": 5,
    "illustrative_bridging_cost_max_pct_of_loan": 8,
    "verdict_yield_strong_pct": 8,
    "verdict_yield_marginal_pct": 5,
    "verdict_brr_recycled_strong_pct": 75,
    "verdict_brr_recycled_marginal_pct": 50,
    "verdict_sa_revenue_strong": 40000,
    "verdict_sa_revenue_marginal": 20000,
    "verdict_r2r_profit_strong": 6000,
    "verdict_r2r_profit_marginal": 2400,
    "verdict_r2r_margin_strong_pct": 20,
    "verdict_flip_roi_strong_pct": 20,
    "verdict_flip_roi_marginal_pct": 10,
    "verdict_flip_profit_strong": 20000,
    "mini_refurb_catalogue_average_job_cost": 450.0,
    # BOQ refurb unit rates (UK landlord refurb, indicative mid-range Aug 2026).
    # Sources: Checkatrade/RBCI 2025-26 trade cost guides (rounded, not fabricated precision).
    "boq_paint_gbp_per_sqm": 8.0,
    "boq_paint_litres_per_sqm": 0.12,
    "boq_paintable_sqm_per_floor_sqm": 3.2,
    "boq_flooring_gbp_per_sqm_carpet": 28.0,
    "boq_flooring_gbp_per_sqm_laminate": 32.0,
    "boq_flooring_gbp_per_sqm_vinyl": 26.0,
    "boq_flooring_gbp_per_sqm_tile": 45.0,
    "boq_flooring_default_material": "laminate",
    "boq_plaster_gbp_per_sqm": 18.0,
    "boq_plasterable_sqm_per_floor_sqm": 3.2,
    "boq_rewire_gbp_per_room": 850.0,
    "boq_kitchen_fitout_gbp_light": 3500.0,
    "boq_kitchen_fitout_gbp_standard": 6500.0,
    "boq_kitchen_fitout_gbp_full": 12000.0,
    "boq_bathroom_fitout_gbp_light": 2800.0,
    "boq_bathroom_fitout_gbp_standard": 4500.0,
    "boq_bathroom_fitout_gbp_full": 7500.0,
}


def compute_progressive_tax(amount: float, bands: list[dict[str, Any]]) -> float:
    """Slice-band progressive tax, exact port of PropertyConstantsService::
    computeProgressiveTax - each band's rate applies only to the slice of
    `amount` between the previous cap and this band's cap."""
    if amount <= 0 or not bands:
        return 0.0

    tax = 0.0
    previous_cap = 0.0
    for band in bands:
        cap = band.get("up_to")
        rate = float(band.get("rate", 0))
        upper = amount if cap is None else float(cap)

        if amount <= previous_cap:
            break

        taxable = min(amount, upper) - previous_cap
        if taxable > 0:
            tax += taxable * rate

        if cap is None or amount <= upper:
            break

        previous_cap = upper

    return round(tax, 2)


class ConfigResolver:
    """Merges DEFAULT_CONFIG with an optional workspace override dict -
    the aiva2 equivalent of Propreneur's CalculatorConfigService (DB
    platform_settings override config file). Workspace overrides come from
    the property_calculator_settings table (see
    hermes_cli/web_routers/aiva_property_calculators.py)."""

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._overrides = overrides or {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides and self._overrides[key] is not None:
            return self._overrides[key]
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]
        return default
