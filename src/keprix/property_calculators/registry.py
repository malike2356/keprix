"""Dispatch registry for all 28 native calculators - the aiva2 equivalent
of DealCalculatorRegistry.php's get()/rulesFor(). One place that maps a
strategy slug to its calculate function, its rules, and its label."""

from __future__ import annotations

from typing import Any

from keprix.property_calculators import calculators as calc
from keprix.property_calculators.constants import ConfigResolver
from keprix.property_calculators.validation import ValidationError, validate


class CalculatorError(Exception):
    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None) -> None:
        self.field_errors = field_errors or {}
        super().__init__(message)


_REGISTRY: dict[str, tuple[calc.CalcFn, calc.Rules]] = {
    "btl": (calc.calculate_btl, calc.BTL_RULES),
    "brr": (calc.calculate_brr, calc.BRR_RULES),
    "hmo": (calc.calculate_hmo, calc.HMO_RULES),
    "r2r": (calc.calculate_r2r, calc.R2R_RULES),
    "sa": (calc.calculate_sa, calc.SA_RULES),
    "flip": (calc.calculate_flip, calc.FLIP_RULES),
    "bmv_no_money_down": (calc.calculate_bmv_no_money_down, calc.BMV_RULES),
    "commercial": (calc.calculate_commercial, calc.COMMERCIAL_RULES),
    "development": (calc.calculate_development, calc.DEVELOPMENT_RULES),
    "strategy_finder": (calc.calculate_strategy_finder, calc.STRATEGY_FINDER_RULES),
    "npv_irr": (calc.calculate_npv_irr, calc.NPV_IRR_RULES),
    "dscr": (calc.calculate_dscr, calc.DSCR_RULES),
    "income_multiples": (calc.calculate_income_multiples, calc.INCOME_MULTIPLES_RULES),
    "coc_roe": (calc.calculate_coc_roe, calc.COC_ROE_RULES),
    "ltv": (calc.calculate_ltv, calc.LTV_RULES),
    "breakeven_occupancy": (calc.calculate_breakeven_occupancy, calc.BREAKEVEN_OCCUPANCY_RULES),
    "sdlt": (calc.calculate_sdlt, calc.SDLT_RULES),
    "bridging": (calc.calculate_bridging, calc.BRIDGING_RULES),
    "mortgage": (calc.calculate_mortgage, calc.MORTGAGE_RULES),
    "rental_yield": (calc.calculate_rental_yield, calc.RENTAL_YIELD_RULES),
    "btl_roi": (calc.calculate_btl_roi, calc.BTL_ROI_RULES),
    "void_period": (calc.calculate_void_period, calc.VOID_PERIOD_RULES),
    "skip_hire": (calc.calculate_skip_hire, calc.SKIP_HIRE_RULES),
    "cgt": (calc.calculate_cgt, calc.CGT_RULES),
    "mortgage_affordability": (calc.calculate_mortgage_affordability, calc.MORTGAGE_AFFORDABILITY_RULES),
    "mini_refurb": (calc.calculate_mini_refurb, calc.MINI_REFURB_RULES),
    "boq_estimator": (calc.calculate_boq_estimator, calc.BOQ_ESTIMATOR_RULES),
    "snagging_list": (calc.calculate_snagging_list, calc.SNAGGING_LIST_RULES),
    calc.SA_VS_BTL_SLUG: (calc.calculate_sa_vs_btl, calc.SA_VS_BTL_RULES),
}

CALCULATOR_LABELS: dict[str, str] = {
    "btl": "Buy-to-Let",
    "brr": "BRR (buy, refurb, refinance)",
    "hmo": "HMO",
    "r2r": "Rent-to-rent",
    "sa": "Serviced accommodation",
    "flip": "Flip",
    "bmv_no_money_down": "BMV No Money Down (same-day remortgage)",
    "commercial": "Commercial / mixed use",
    "development": "Development (commercial-to-residential)",
    "strategy_finder": "Strategy Finder",
    "npv_irr": "NPV and IRR",
    "dscr": "DSCR",
    "income_multiples": "Income multiples (NOI, cap, GRM)",
    "coc_roe": "Cash-on-cash and ROE",
    "ltv": "Loan-to-value (LTV %)",
    "breakeven_occupancy": "Breakeven occupancy %",
    "sdlt": "SDLT (England and NI residential)",
    "bridging": "Bridging finance cost",
    "mortgage": "Mortgage repayment (IO or repayment)",
    "rental_yield": "Rental yield (gross and net)",
    "btl_roi": "Buy-to-let ROI",
    "void_period": "Void period cost",
    "skip_hire": "Skip hire estimator",
    "cgt": "Capital gains tax (CGT)",
    "mortgage_affordability": "Mortgage affordability",
    "mini_refurb": "Quick refurb estimate",
    "boq_estimator": "Refurb bill of quantities (BOQ)",
    "snagging_list": "Snagging list generator",
    calc.SA_VS_BTL_SLUG: "SA vs BTL side-by-side",
}

CALCULATOR_DESCRIPTIONS: dict[str, str] = {
    "btl": "Model gross yield, net cashflow, ROI, and illustrative stress using purchase price, rent, and optional mortgage payment.",
    "brr": "Capital recycle plus optional hold underwriting: refinance LTV, cash left in, stress tests, breakeven rent.",
    "hmo": "Full HMO model: room rents, voids, licence and opex, mortgage, cashflow, breakeven occupancy, cash-on-cash.",
    "r2r": "Full rent-to-rent model: gross margin, operating costs, setup capital, breakeven occupancy, operator rules.",
    "sa": "Full SA model: nightly rate, occupancy, platform and cleaning costs, NOI, cashflow, setup return.",
    "flip": "Net profit and ROI after purchase, refurb, and sale price including selling cost assumptions.",
    "bmv_no_money_down": "Buy below market value with 100% bridging and same-day remortgage - model whether all costs are covered with zero cash left in.",
    "commercial": "Commercial yields (passing and reversionary), WAULT, commercial SDLT, lease-driven rent, value-add scenarios.",
    "development": "Small-scale commercial-to-residential conversion: GDV, GDC, development finance, sell vs hold refinance.",
    "strategy_finder": "Five-question matcher: scores BTL, BRR, HMO, R2R, SA, Flip, and Commercial against your capital, goals, time, risk, and skills.",
    "npv_irr": "Discounted NPV and IRR from a cash-flow series (period 0 is initial equity outlay, typically negative).",
    "dscr": "Annual NOI divided by annual debt service; includes a 1.25x illustrative pass flag.",
    "income_multiples": "NOI, cap rate, gross rent multiplier, and gross yield from price and rent (optional opex).",
    "coc_roe": "Cash-on-cash from pre-tax cash flow and cash in; optional ROE when current equity is supplied.",
    "ltv": "Loan balance as a percentage of property value, plus implied equity.",
    "breakeven_occupancy": "Minimum occupancy at which gross potential income covers operating expenses plus debt service.",
    "sdlt": "Illustrative stamp duty for England and NI residential purchases by profile (standard, additional property, first-time buyer).",
    "bridging": "Interest and stated fees over a fixed term for a bridging loan (no rolled interest compounding).",
    "mortgage": "Monthly payment for interest-only or capital repayment over a fixed term at a given annual rate.",
    "rental_yield": "Gross and net rental yield with void weeks and annual expense lines.",
    "btl_roi": "Cash-on-cash return and monthly cashflow for a classic BTL purchase (deposit, SDLT, mortgage, agent fees).",
    "void_period": "Total cost of an empty property: lost rent, weekly holding costs, and one-off preparation.",
    "skip_hire": "Estimate waste volume and recommended skip size with indicative UK hire costs.",
    "cgt": "Illustrative UK residential CGT on disposal with PRR and annual exempt amount (2024/25).",
    "mortgage_affordability": "How much you may borrow from income, commitments, deposit, and stressed payment.",
    "mini_refurb": "Under-two-minute refurb budget from room counts and quality tier (UK catalogue averages).",
    "boq_estimator": "Line-item refurb BOQ from explicit room areas and scoped works; feeds BRR/Flip refurb_cost.",
    "snagging_list": "Generate a 23-item snagging checklist for new builds and refurb handover.",
    calc.SA_VS_BTL_SLUG: "Compare Buy-to-Let and Serviced Accommodation on the same purchase: ROI, cashflow, and fit-out payback in parallel columns.",
}


def list_strategies() -> list[dict[str, str]]:
    return [
        {"slug": slug, "label": CALCULATOR_LABELS.get(slug, slug), "description": CALCULATOR_DESCRIPTIONS.get(slug, "")}
        for slug in _REGISTRY
    ]


def get_calculator(strategy: str) -> calc.CalcFn:
    entry = _REGISTRY.get(strategy)
    if entry is None:
        raise CalculatorError(f"unknown calculator strategy: {strategy}")
    return entry[0]


def rules_for(strategy: str) -> calc.Rules:
    entry = _REGISTRY.get(strategy)
    if entry is None:
        raise CalculatorError(f"unknown calculator strategy: {strategy}")
    return entry[1]


def run_calculator(strategy: str, inputs: dict[str, Any], config: ConfigResolver | None = None) -> dict[str, Any]:
    """Validates inputs against the strategy's real rules, then runs the
    calculator. Raises CalculatorError (unknown strategy) or
    validation.ValidationError (bad inputs, field_errors attached)."""
    fn, rules = _REGISTRY.get(strategy, (None, None))
    if fn is None:
        raise CalculatorError(f"unknown calculator strategy: {strategy}")

    try:
        cleaned = validate(inputs, rules)
    except ValidationError as exc:
        raise CalculatorError(f"invalid inputs for {strategy}", field_errors=exc.errors) from exc

    try:
        return fn(cleaned, config or ConfigResolver())
    except ValidationError as exc:
        raise CalculatorError(f"invalid inputs for {strategy}", field_errors=exc.errors) from exc
