"""All 28 native property calculators, ported faithfully from Propreneur's
real Deal Calculators (propreneur/app/Services/Deals/Calculators/*.php).
Each function matches the source file's calculate() logic line-for-line
where the language allows a direct translation; RULES dicts mirror the
source's rules() validation exactly. Config-driven values (SDLT bands,
mortgage/bridging/R2R/HMO/BRR defaults, verdict bands) come from
constants.ConfigResolver, never a hardcoded literal in a calculator body.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from keprix.property_calculators import commercial as commercial_engine
from keprix.property_calculators import development as development_engine
from keprix.property_calculators import financial
from keprix.property_calculators import hold_projection
from keprix.property_calculators import investment_math
from keprix.property_calculators import strategy_finder as strategy_finder_engine
from keprix.property_calculators.constants import (
    CGT_ANNUAL_EXEMPTION,
    CGT_RESIDENTIAL_RATE_BASIC,
    CGT_RESIDENTIAL_RATE_HIGHER,
    MORTGAGE_STRESS_TEST_RATE_OFFSET,
    SDLT_RULES_VERSION,
    ConfigResolver,
)

Rules = dict[str, list[str]]
CalcResult = dict[str, Any]
CalcFn = Callable[[dict[str, Any], ConfigResolver], CalcResult]

_SNAGGING_ITEMS = [
    {"code": "ext_brick", "area": "External", "item": "Brickwork, render, and pointing defects"},
    {"code": "ext_roof", "area": "External", "item": "Roof tiles, felt, and flashing"},
    {"code": "ext_gutters", "area": "External", "item": "Gutters, downpipes, and drainage"},
    {"code": "ext_windows", "area": "External", "item": "Windows and seals"},
    {"code": "ext_doors", "area": "External", "item": "External doors and locks"},
    {"code": "ext_drive", "area": "External", "item": "Drive, paths, and fencing"},
    {"code": "int_walls", "area": "Internal", "item": "Walls: cracks, finish, and paint"},
    {"code": "int_ceilings", "area": "Internal", "item": "Ceilings: cracks, bowing, and finish"},
    {"code": "int_floors", "area": "Internal", "item": "Floors: level, gaps, and creaks"},
    {"code": "int_doors", "area": "Internal", "item": "Internal doors, frames, and ironmongery"},
    {"code": "int_stairs", "area": "Internal", "item": "Stairs, balustrades, and handrails"},
    {"code": "kitchen_units", "area": "Kitchen", "item": "Units, worktops, and splashbacks"},
    {"code": "kitchen_appliances", "area": "Kitchen", "item": "Appliances wired/plumbed and tested"},
    {"code": "kitchen_plumbing", "area": "Kitchen", "item": "Sink, taps, and waste"},
    {"code": "bath_suite", "area": "Bathroom", "item": "Sanitaryware and sealant"},
    {"code": "bath_tiling", "area": "Bathroom", "item": "Tiling, grout, and waterproofing"},
    {"code": "bath_extract", "area": "Bathroom", "item": "Extractor fan and ventilation"},
    {"code": "elec_sockets", "area": "Electrical", "item": "Sockets, switches, and faceplates"},
    {"code": "elec_lighting", "area": "Electrical", "item": "Lighting and dimmers"},
    {"code": "elec_consumer", "area": "Electrical", "item": "Consumer unit labels and RCBO tests"},
    {"code": "heat_radiators", "area": "Heating", "item": "Radiators, TRVs, and bleeding"},
    {"code": "heat_boiler", "area": "Heating", "item": "Boiler commission and controls"},
    {"code": "misc_safety", "area": "Safety", "item": "Smoke/CO alarms and escape routes"},
]


def _num(inputs: dict, key: str, default: float = 0.0) -> float:
    value = inputs.get(key)
    if value is None or value == "":
        return default
    return float(value)


def _bool(inputs: dict, key: str, default: bool = False) -> bool:
    value = inputs.get(key)
    if value is None:
        return default
    return bool(value)


# ---------------------------------------------------------------- btl -----
BTL_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "monthly_rent": ["required", "numeric", "min:0"],
    "monthly_mortgage": ["nullable", "numeric", "min:0"],
    "monthly_insurance": ["nullable", "numeric", "min:0"],
    "monthly_council_tax": ["nullable", "numeric", "min:0"],
    "monthly_utilities": ["nullable", "numeric", "min:0"],
    "management_pct_rent": ["nullable", "numeric", "min:0", "max:1"],
    "maintenance_pct_value": ["nullable", "numeric", "min:0", "max:0.2"],
    "void_months_per_year": ["nullable", "numeric", "min:0", "max:3"],
    "stress_rent_factor": ["nullable", "numeric", "min:0", "max:1"],
    "stress_mortgage_factor": ["nullable", "numeric", "min:1", "max:3"],
    "deposit_amount": ["nullable", "numeric", "min:0"],
    "legal_fees": ["nullable", "numeric", "min:0"],
    "survey_fees": ["nullable", "numeric", "min:0"],
    "refurb_budget": ["nullable", "numeric", "min:0"],
    "stamp_duty": ["nullable", "numeric", "min:0"],
    "use_additional_sdlt": ["nullable", "boolean"],
}


def calculate_btl(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    monthly_rent = _num(inputs, "monthly_rent")
    monthly_mortgage = _num(inputs, "monthly_mortgage")
    monthly_insurance = _num(inputs, "monthly_insurance")
    monthly_council_tax = _num(inputs, "monthly_council_tax")
    monthly_utilities = _num(inputs, "monthly_utilities")
    mgmt_pct = _num(inputs, "management_pct_rent", 0.12)
    maint_pct = _num(inputs, "maintenance_pct_value", 0.01)
    void_months = _num(inputs, "void_months_per_year", 1)
    stress_rent_factor = _num(inputs, "stress_rent_factor", 0.75)
    stress_mortgage_factor = _num(inputs, "stress_mortgage_factor", 1.25)

    annual_rent = monthly_rent * 12
    annual_mortgage = monthly_mortgage * 12
    annual_insurance = monthly_insurance * 12
    annual_council_tax = monthly_council_tax * 12
    annual_utilities = monthly_utilities * 12
    annual_management = annual_rent * mgmt_pct
    annual_maintenance = purchase * maint_pct
    annual_void = monthly_rent * void_months
    annual_costs = (
        annual_mortgage + annual_insurance + annual_council_tax + annual_utilities
        + annual_management + annual_maintenance + annual_void
    )

    gross_yield = financial.gross_yield_percent(monthly_rent, purchase) or 0.0
    net_yield = financial.net_yield_percent(monthly_rent, purchase, annual_costs) or 0.0

    monthly_management = annual_management / 12
    monthly_maintenance = annual_maintenance / 12
    monthly_void = annual_void / 12
    monthly_cashflow = (
        monthly_rent - monthly_mortgage - monthly_insurance - monthly_council_tax
        - monthly_utilities - monthly_management - monthly_maintenance - monthly_void
    )

    annual_cashflow = monthly_cashflow * 12
    roi = financial.roi_percent(annual_cashflow, _btl_total_investment(inputs, purchase)) or 0.0

    stress_ok = (monthly_rent * stress_rent_factor) >= (monthly_mortgage * stress_mortgage_factor)
    opex_ratio = round(((annual_costs - annual_mortgage) / annual_rent) * 100, 4) if annual_rent > 0 else 0.0

    growth = hold_projection.resolve_growth_inputs(inputs)
    deposit = _num(inputs, "deposit_amount")
    loan_balance = max(0.0, purchase - deposit) if deposit > 0 else (purchase * 0.75 if monthly_mortgage > 0 else 0.0)

    five_year = hold_projection.project(
        {
            "hold_years": growth["hold_years"],
            "annual_rent_growth_pct": growth["rent_growth"],
            "annual_capital_growth_pct": growth["cap_growth"],
            "property_value": purchase,
            "cash_invested": _btl_total_investment(inputs, purchase),
            "monthly_rent": monthly_rent,
            "monthly_mortgage": monthly_mortgage,
            "monthly_insurance": monthly_insurance,
            "monthly_council_tax": monthly_council_tax,
            "monthly_utilities": monthly_utilities,
            "monthly_management": monthly_management,
            "monthly_maintenance": monthly_maintenance,
            "void_months_per_year": void_months,
            "mortgage_balance": loan_balance,
        }
    )

    stamp = _btl_stamp_duty(inputs, purchase)

    return {
        "outputs": {
            "gross_yield_pct": round(gross_yield, 4),
            "net_yield_pct": round(net_yield, 4),
            "monthly_cashflow": round(monthly_cashflow, 2),
            "annual_cashflow": round(annual_cashflow, 2),
            "annual_costs_total": round(annual_costs, 2),
            "annual_council_tax": round(annual_council_tax, 2),
            "annual_utilities": round(annual_utilities, 2),
            "operating_cost_ratio_pct": opex_ratio,
            "roi_pct": round(roi, 4),
            "stamp_duty_computed": round(stamp, 2),
            "total_investment": round(_btl_total_investment(inputs, purchase), 2),
            "mortgage_stress_pass": stress_ok,
            "deal_stacks": monthly_cashflow > 0,
            "hold_years_used": five_year["hold_years"],
            "five_year_cumulative_cashflow": five_year["cumulative_cashflow"],
            "five_year_equity_gain": five_year["equity_gain"],
            "five_year_total_return": five_year["total_return"],
            "five_year_total_return_pct": five_year["total_return_pct"],
            "five_year_schedule": five_year["schedule"],
            "five_year_rent_growth_pct_used": five_year["annual_rent_growth_pct"],
            "five_year_capital_growth_pct_used": five_year["annual_capital_growth_pct"],
        },
        "assumptions": [
            "Gross yield uses (monthly rent x 12) / purchase price.",
            "Net yield subtracts mortgage (12x monthly), insurance, management % of gross rent, maintenance % of value, and void months of rent.",
            "ROI uses annual cashflow / total investment (deposit + SDLT + legal + survey + refurb).",
            "Mortgage stress test: (monthly rent x stress rent factor) >= (monthly mortgage x stress mortgage factor); defaults 0.75 and 1.25 unless overridden.",
            f"{five_year['hold_years']}-year projection: rent grows {five_year['annual_rent_growth_pct']}% p.a.; property value grows {five_year['annual_capital_growth_pct']}% p.a.; IO mortgage balance held constant.",
            f"Total {five_year['hold_years']}-year return = cumulative net cashflow + change in property value (not leveraged sale proceeds).",
        ],
    }


def _btl_stamp_duty(inputs: dict, purchase: float) -> float:
    if inputs.get("stamp_duty") not in (None, ""):
        return float(inputs["stamp_duty"])
    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    return financial.stamp_duty_additional_property(purchase) if use_additional else 0.0


def _btl_total_investment(inputs: dict, purchase: float) -> float:
    stamp = _btl_stamp_duty(inputs, purchase)
    deposit = _num(inputs, "deposit_amount")
    legal = _num(inputs, "legal_fees")
    survey = _num(inputs, "survey_fees")
    refurb = _num(inputs, "refurb_budget")
    total = deposit + stamp + legal + survey + refurb
    if total <= 0:
        total = max(1.0, (purchase * 0.25) + stamp + legal + survey)
    return total


# ---------------------------------------------------------------- ltv -----
LTV_RULES: Rules = {
    "loan_amount": ["required", "numeric", "min:0"],
    "property_value": ["required", "numeric", "min:0.01"],
}


def calculate_ltv(inputs: dict, config: ConfigResolver) -> CalcResult:
    loan = _num(inputs, "loan_amount")
    value = _num(inputs, "property_value")
    ltv_pct = (loan / value) * 100.0 if value > 0 else 0.0
    equity = max(0.0, value - loan)
    return {
        "outputs": {
            "ltv_pct": round(ltv_pct, 4),
            "equity_amount": round(equity, 2),
            "loan_amount": round(loan, 2),
            "property_value": round(value, 2),
        },
        "assumptions": [
            "LTV % = (loan amount / property value) x 100.",
            "Equity = property value minus loan (not costs-adjusted).",
        ],
    }


# --------------------------------------------------------- snagging_list --
SNAGGING_LIST_RULES: Rules = {
    "property_address": ["required", "string", "max:500"],
    "inspector_name": ["nullable", "string", "max:120"],
    "inspection_date": ["nullable", "date"],
    "developer_name": ["nullable", "string", "max:200"],
}


def calculate_snagging_list(inputs: dict, config: ConfigResolver) -> CalcResult:
    return {
        "outputs": {
            "checklist_item_count": len(_SNAGGING_ITEMS),
            "property_address": str(inputs.get("property_address") or ""),
            "inspector_name": str(inputs.get("inspector_name") or ""),
            "inspection_date": str(inputs.get("inspection_date") or ""),
            "developer_name": str(inputs.get("developer_name") or ""),
            "checklist_ready": True,
        },
        "assumptions": [
            "Standard 23-item snagging checklist for UK new builds and refurb handover.",
            "Download the PDF after generating to share with your builder or solicitor.",
            "Professional snagging surveys may find additional defects beyond this list.",
        ],
        "checklist_items": _SNAGGING_ITEMS,
    }


# ------------------------------------------------------ breakeven_occupancy
BREAKEVEN_OCCUPANCY_RULES: Rules = {
    "annual_operating_expenses": ["required", "numeric", "min:0"],
    "annual_debt_service": ["required", "numeric", "min:0"],
    "annual_gross_potential_income": ["required", "numeric", "min:0.01"],
}


def calculate_breakeven_occupancy(inputs: dict, config: ConfigResolver) -> CalcResult:
    opex = _num(inputs, "annual_operating_expenses")
    debt = _num(inputs, "annual_debt_service")
    gpi = _num(inputs, "annual_gross_potential_income")
    required = opex + debt
    breakeven_pct = (required / gpi) * 100.0
    headroom_pct = max(0.0, 100.0 - breakeven_pct)
    return {
        "outputs": {
            "breakeven_occupancy_pct": round(breakeven_pct, 4),
            "headroom_vs_full_occupancy_pct": round(headroom_pct, 4),
            "annual_cash_required_before_income": round(required, 2),
            "annual_gross_potential_income": round(gpi, 2),
        },
        "assumptions": [
            "Breakeven occupancy % = (annual opex + annual debt service) / annual gross potential income x 100.",
            "Gross potential income is at 100% occupancy; compare to your forecast occupancy.",
        ],
    }


# --------------------------------------------------------------- sdlt -----
SDLT_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "profile": ["nullable", "string", "in:standard,additional_property,first_time_buyer"],
}


def calculate_sdlt(inputs: dict, config: ConfigResolver) -> CalcResult:
    price = _num(inputs, "purchase_price")
    profile = str(inputs.get("profile") or "additional_property")
    sdlt = financial.stamp_duty_residential(price, profile, config.get("sdlt_residential_bands"))
    return {
        "outputs": {
            "sdlt_total": round(sdlt, 2),
            "effective_rate_pct": round((sdlt / price) * 100, 4) if price > 0 else 0.0,
            "rules_version": 1.0,
        },
        "assumptions": [
            "England and NI residential illustrative bands; not legal or tax advice.",
            "Profile standard: main rates without surcharge. additional_property: surcharge schedule already used in BTL. first_time_buyer: relief up to £625k then standard.",
            f"Rules label: {SDLT_RULES_VERSION}",
        ],
    }


# ------------------------------------------------------------- npv_irr ----
NPV_IRR_RULES: Rules = {
    "cash_flows": ["required", "array", "min:2"],
    "cash_flows.*": ["numeric"],
    "discount_rate_annual": ["required", "numeric", "min:0", "max:0.5"],
}


def calculate_npv_irr(inputs: dict, config: ConfigResolver) -> CalcResult:
    flows = [float(v) for v in inputs["cash_flows"]]
    r = _num(inputs, "discount_rate_annual")
    npv_value = investment_math.npv(r, flows)
    irr_dec = investment_math.irr_annual_decimal(flows)
    irr_pct = round(irr_dec * 100, 4) if irr_dec is not None else None
    return {
        "outputs": {
            "npv": round(npv_value, 2),
            "irr_pct": irr_pct,
            "discount_rate_annual_pct": round(r * 100, 4),
            "periods": len(flows),
        },
        "assumptions": [
            "NPV uses the supplied annual discount rate as a decimal (e.g. 0.1 for 10%).",
            "IRR is the rate that sets NPV to zero on the same series (Newton-Raphson); null if not solvable.",
            "Index 0 is period 0 (typically initial outlay as a negative number).",
        ],
    }


# ---------------------------------------------------------------- dscr ----
DSCR_RULES: Rules = {
    "annual_noi": ["required", "numeric"],
    "annual_debt_service": ["required", "numeric", "min:0.01"],
}


def calculate_dscr(inputs: dict, config: ConfigResolver) -> CalcResult:
    noi = _num(inputs, "annual_noi")
    debt = _num(inputs, "annual_debt_service")
    dscr = noi / debt if debt > 0 else 0.0
    hurdle = float(config.get("illustrative_dscr_min") or 1.25)
    passes = dscr >= hurdle
    return {
        "outputs": {
            "dscr": round(dscr, 4),
            "passes_1_25x": passes,
            "dscr_hurdle_used": hurdle,
            "annual_noi": round(noi, 2),
            "annual_debt_service": round(debt, 2),
        },
        "assumptions": [
            "DSCR = annual NOI / annual debt service (principal plus interest).",
            f"passes_1_25x is true when DSCR is at least {hurdle} (illustrative lender hurdle from platform settings).",
        ],
    }


# -------------------------------------------------------------- coc_roe ---
COC_ROE_RULES: Rules = {
    "annual_pre_tax_cash_flow": ["required", "numeric"],
    "total_cash_invested": ["required", "numeric", "min:0.01"],
    "annual_net_income_equity": ["nullable", "numeric"],
    "current_equity": ["nullable", "numeric", "min:0.01"],
}


def calculate_coc_roe(inputs: dict, config: ConfigResolver) -> CalcResult:
    cf = _num(inputs, "annual_pre_tax_cash_flow")
    cash_in = _num(inputs, "total_cash_invested")
    coc = round((cf / cash_in) * 100, 4) if cash_in > 0 else 0.0

    ni = float(inputs["annual_net_income_equity"]) if inputs.get("annual_net_income_equity") not in (None, "") else cf
    equity = float(inputs["current_equity"]) if inputs.get("current_equity") not in (None, "") else None
    roe = round((ni / equity) * 100, 4) if (equity is not None and equity > 0) else None

    return {
        "outputs": {"coc_pct": coc, "roe_pct": roe},
        "assumptions": [
            "CoC = (annual pre-tax cash flow / total cash invested) x 100.",
            "ROE uses annual_net_income_equity when provided, otherwise the same cash flow figure, divided by current_equity.",
            "ROE is null when current_equity is omitted.",
        ],
    }


# -------------------------------------------------------------- bridging --
BRIDGING_RULES: Rules = {
    "loan_amount": ["required", "numeric", "min:1"],
    "annual_interest_rate": ["required", "numeric", "min:0", "max:2"],
    "term_months": ["required", "numeric", "min:1", "max:60"],
    "arrangement_fee_pct": ["nullable", "numeric", "min:0", "max:0.1"],
    "arrangement_fee_flat": ["nullable", "numeric", "min:0"],
    "exit_fee_flat": ["nullable", "numeric", "min:0"],
    "broker_fee_flat": ["nullable", "numeric", "min:0"],
}


def calculate_bridging(inputs: dict, config: ConfigResolver) -> CalcResult:
    loan = _num(inputs, "loan_amount")
    annual_rate = _num(inputs, "annual_interest_rate")
    months = round(_num(inputs, "term_months"))
    fee_pct = _num(inputs, "arrangement_fee_pct")
    fee_flat = _num(inputs, "arrangement_fee_flat")
    exit_fee = _num(inputs, "exit_fee_flat")
    broker = _num(inputs, "broker_fee_flat")

    interest = loan * annual_rate * (months / 12)
    arrangement_from_pct = loan * fee_pct
    arrangement_total = arrangement_from_pct + fee_flat
    fees_total = arrangement_total + exit_fee + broker
    total_cost = interest + fees_total

    return {
        "outputs": {
            "interest_cost": round(interest, 2),
            "arrangement_fees_total": round(arrangement_total, 2),
            "other_fees_total": round(exit_fee + broker, 2),
            "total_financing_cost": round(total_cost, 2),
            "cost_as_pct_of_loan": round((total_cost / loan) * 100, 4) if loan > 0 else 0.0,
        },
        "assumptions": [
            "Interest is loan x annual rate x (term months / 12); no rolled interest compounding in this model.",
            "Arrangement fee is percentage of loan plus optional flat; exit and broker fees are one-off.",
        ],
    }


# --------------------------------------------------------- income_multiples
INCOME_MULTIPLES_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "annual_gross_rent": ["nullable", "numeric", "min:0", "required_without:monthly_rent"],
    "monthly_rent": ["nullable", "numeric", "min:0", "required_without:annual_gross_rent"],
    "annual_operating_expenses": ["nullable", "numeric", "min:0"],
}


def calculate_income_multiples(inputs: dict, config: ConfigResolver) -> CalcResult:
    price = _num(inputs, "purchase_price")
    annual_gross = (
        _num(inputs, "annual_gross_rent")
        if inputs.get("annual_gross_rent") not in (None, "")
        else _num(inputs, "monthly_rent") * 12.0
    )
    opex = _num(inputs, "annual_operating_expenses")

    noi = annual_gross - opex
    cap_rate = round((noi / price) * 100, 4) if price > 0 else 0.0
    grm = round(price / annual_gross, 4) if annual_gross > 0 else 0.0
    monthly_for_yield = annual_gross / 12.0 if annual_gross > 0 else None
    gross_yield = (financial.gross_yield_percent(monthly_for_yield, price) or 0.0) if monthly_for_yield is not None else 0.0

    return {
        "outputs": {
            "annual_gross_rent": round(annual_gross, 2),
            "noi_annual": round(noi, 2),
            "cap_rate_pct": cap_rate,
            "grm": grm,
            "gross_yield_pct": gross_yield,
        },
        "assumptions": [
            "NOI = annual gross rent minus annual operating expenses (excludes debt service).",
            "Cap rate = (NOI / purchase price) x 100.",
            "GRM = purchase price / annual gross rent.",
            "Gross yield uses monthly rent implied from annual gross rent when monthly_rent is not supplied alone.",
        ],
    }


# ---------------------------------------------------------- rental_yield --
RENTAL_YIELD_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "monthly_rent": ["required", "numeric", "min:0"],
    "void_weeks_per_year": ["nullable", "numeric", "min:0", "max:52"],
    "annual_mortgage_interest": ["nullable", "numeric", "min:0"],
    "annual_insurance": ["nullable", "numeric", "min:0"],
    "annual_maintenance": ["nullable", "numeric", "min:0"],
    "annual_letting_fees": ["nullable", "numeric", "min:0"],
    "annual_ground_rent_service": ["nullable", "numeric", "min:0"],
    "annual_other_costs": ["nullable", "numeric", "min:0"],
}


def calculate_rental_yield(inputs: dict, config: ConfigResolver) -> CalcResult:
    price = _num(inputs, "purchase_price")
    monthly_rent = _num(inputs, "monthly_rent")
    void_weeks = _num(inputs, "void_weeks_per_year", 2)
    annual_rent_gross = monthly_rent * 12
    void_cost = round(monthly_rent * (void_weeks / 52) * 12, 2)
    effective_rent = annual_rent_gross - void_cost

    opex = (
        _num(inputs, "annual_mortgage_interest") + _num(inputs, "annual_insurance") + _num(inputs, "annual_maintenance")
        + _num(inputs, "annual_letting_fees") + _num(inputs, "annual_ground_rent_service") + _num(inputs, "annual_other_costs")
    )

    gross_yield = financial.gross_yield_percent(monthly_rent, price) or 0.0
    net_yield = round(((effective_rent - opex) / price) * 100, 4) if price > 0 else 0.0
    monthly_net = round((effective_rent - opex) / 12, 2)

    return {
        "outputs": {
            "gross_yield_pct": round(gross_yield, 4),
            "net_yield_pct": net_yield,
            "annual_rent_gross": round(annual_rent_gross, 2),
            "void_cost_annual": void_cost,
            "effective_rent_annual": round(effective_rent, 2),
            "annual_expenses_total": round(opex, 2),
            "monthly_net_income": monthly_net,
            "annual_net_income": round(effective_rent - opex, 2),
            "deal_stacks": monthly_net > 0,
        },
        "assumptions": [
            "Gross yield = (monthly rent x 12) / purchase price.",
            "Void cost = monthly rent x (void weeks / 52) x 12, deducted before expenses.",
            "Net yield = (effective rent after void minus annual expenses) / purchase price.",
            "Mortgage field is annual interest/cost only (not full repayment unless you enter it).",
        ],
    }


# ------------------------------------------------------------ void_period -
VOID_PERIOD_RULES: Rules = {
    "monthly_rent": ["required", "numeric", "min:0"],
    "void_weeks": ["required", "numeric", "min:0.5", "max:52"],
    "weekly_mortgage": ["nullable", "numeric", "min:0"],
    "weekly_insurance": ["nullable", "numeric", "min:0"],
    "weekly_utilities": ["nullable", "numeric", "min:0"],
    "weekly_council_tax": ["nullable", "numeric", "min:0"],
    "weekly_maintenance": ["nullable", "numeric", "min:0"],
    "prep_cleaning": ["nullable", "numeric", "min:0"],
    "prep_redecoration": ["nullable", "numeric", "min:0"],
    "prep_marketing": ["nullable", "numeric", "min:0"],
    "prep_viewings_admin": ["nullable", "numeric", "min:0"],
    "prep_tenant_checks": ["nullable", "numeric", "min:0"],
}


def calculate_void_period(inputs: dict, config: ConfigResolver) -> CalcResult:
    monthly_rent = _num(inputs, "monthly_rent")
    weeks = _num(inputs, "void_weeks")
    weekly_rent = monthly_rent / 4.33
    lost_rent = round(weekly_rent * weeks, 2)

    weekly_running = (
        _num(inputs, "weekly_mortgage") + _num(inputs, "weekly_insurance") + _num(inputs, "weekly_utilities")
        + _num(inputs, "weekly_council_tax") + _num(inputs, "weekly_maintenance")
    )
    running_total = round(weekly_running * weeks, 2)

    prep_total = round(
        _num(inputs, "prep_cleaning") + _num(inputs, "prep_redecoration") + _num(inputs, "prep_marketing")
        + _num(inputs, "prep_viewings_admin") + _num(inputs, "prep_tenant_checks"),
        2,
    )

    total = round(lost_rent + running_total + prep_total, 2)
    daily_cost = round(total / (weeks * 7), 2) if weeks > 0 else 0.0

    return {
        "outputs": {
            "weekly_rent_implied": round(weekly_rent, 2),
            "lost_rent_total": lost_rent,
            "running_costs_total": running_total,
            "preparation_costs_total": prep_total,
            "total_void_cost": total,
            "cost_per_day": daily_cost,
            "void_weeks_used": weeks,
        },
        "assumptions": [
            "Weekly rent implied from monthly rent using PCM / 4.33 (UK convention).",
            "Lost rent = weekly rent x void weeks.",
            "Running costs = sum of weekly holding costs x void weeks.",
            "Preparation costs are one-off turnover costs added to the void total.",
        ],
    }


# --------------------------------------------------------------- flip -----
FLIP_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "refurb_cost": ["required", "numeric", "min:0"],
    "selling_price": ["required", "numeric", "min:1"],
    "legal_buy": ["nullable", "numeric", "min:0"],
    "legal_sell": ["nullable", "numeric", "min:0"],
    "survey_fees": ["nullable", "numeric", "min:0"],
    "finance_holding": ["nullable", "numeric", "min:0"],
    "marketing_cost": ["nullable", "numeric", "min:0"],
    "holding_months_cost": ["nullable", "numeric", "min:0"],
    "agent_fee_pct": ["nullable", "numeric", "min:0", "max:0.1"],
    "use_additional_sdlt": ["nullable", "boolean"],
}


def calculate_flip(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    refurb = _num(inputs, "refurb_cost")
    sell = _num(inputs, "selling_price")
    legal_buy = _num(inputs, "legal_buy", 1500)
    legal_sell = _num(inputs, "legal_sell", 1500)
    survey = _num(inputs, "survey_fees", 500)
    finance = _num(inputs, "finance_holding")
    marketing = _num(inputs, "marketing_cost", 500)
    holding = _num(inputs, "holding_months_cost")
    agent_pct = _num(inputs, "agent_fee_pct", 0.02)

    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    stamp = financial.stamp_duty_additional_property(purchase) if use_additional else 0.0

    total_cost = purchase + stamp + legal_buy + survey + refurb + finance + marketing + holding
    selling_costs = sell * agent_pct + legal_sell
    net_profit = sell - total_cost - selling_costs
    roi = round((net_profit / total_cost) * 100, 4) if total_cost > 0 else 0.0
    margin_pct = round((net_profit / sell) * 100, 4) if sell > 0 else 0.0

    return {
        "outputs": {
            "stamp_duty": round(stamp, 2),
            "total_cost": round(total_cost, 2),
            "selling_costs": round(selling_costs, 2),
            "net_profit": round(net_profit, 2),
            "roi_pct": roi,
            "profit_margin_pct": margin_pct,
            "total_cash_in": round(total_cost, 2),
            "deal_stacks": net_profit > 0,
        },
        "assumptions": [
            "Total cost includes purchase, SDLT (additional property), legal buy, survey, refurb, finance, marketing, holding.",
            "Selling costs = agent % of selling price + legal sell.",
        ],
    }


# -------------------------------------------------------------- mortgage --
MORTGAGE_RULES: Rules = {
    "loan_amount": ["required", "numeric", "min:1"],
    "annual_interest_rate": ["required", "numeric", "min:0", "max:0.25"],
    "term_years": ["required", "numeric", "min:1", "max:40"],
    "interest_only": ["nullable", "boolean"],
}


def calculate_mortgage(inputs: dict, config: ConfigResolver) -> CalcResult:
    principal = _num(inputs, "loan_amount")
    annual = _num(inputs, "annual_interest_rate")
    years = round(_num(inputs, "term_years"))
    months = max(1, years * 12)
    interest_only = _bool(inputs, "interest_only")
    r = annual / 12

    if interest_only or r <= 0:
        monthly = principal * r
        total_paid = monthly * months + principal
        return {
            "outputs": {
                "monthly_payment": round(monthly, 2),
                "annual_payment": round(monthly * 12, 2),
                "total_paid_over_term": round(total_paid, 2),
                "total_interest_paid": round(monthly * months, 2),
                "interest_only": True,
            },
            "assumptions": ["Interest-only: monthly payment is loan x (annual rate / 12); principal unchanged over term."],
        }

    pow_ = (1 + r) ** months
    monthly = principal * (r * pow_) / (pow_ - 1)
    total_paid = monthly * months
    interest_paid = total_paid - principal

    return {
        "outputs": {
            "monthly_payment": round(monthly, 2),
            "annual_payment": round(monthly * 12, 2),
            "total_paid_over_term": round(total_paid, 2),
            "total_interest_paid": round(interest_paid, 2),
            "interest_only": False,
        },
        "assumptions": ["Repayment mortgage with equal monthly instalments (standard amortisation formula)."],
    }


# ------------------------------------------------------------ mini_refurb -
MINI_REFURB_RULES: Rules = {
    "bedrooms": ["nullable", "integer", "min:0", "max:10"],
    "bathrooms": ["nullable", "integer", "min:0", "max:5"],
    "reception_rooms": ["nullable", "integer", "min:0", "max:5"],
    "kitchen": ["nullable", "boolean"],
    "quality": ["nullable", "string", "in:light,standard,full"],
    "contingency_pct": ["nullable", "numeric", "min:0", "max:0.25"],
}


def calculate_mini_refurb(inputs: dict, config: ConfigResolver) -> CalcResult:
    beds = max(0, int(_num(inputs, "bedrooms", 2)))
    baths = max(0, int(_num(inputs, "bathrooms", 1)))
    receptions = max(0, int(_num(inputs, "reception_rooms", 1)))
    kitchen = _bool(inputs, "kitchen", True)
    quality = str(inputs.get("quality") or "standard")
    cont_pct = _num(inputs, "contingency_pct", 0.10)

    tier_mult = {"light": 0.55, "full": 1.35}.get(quality, 1.0)
    catalogue_avg = float(config.get("mini_refurb_catalogue_average_job_cost") or 450.0)
    per_bed = catalogue_avg * 2.8
    per_bath = catalogue_avg * 3.6
    per_reception = catalogue_avg * 1.6
    kitchen_cost = catalogue_avg * 4.2 if kitchen else 0.0

    subtotal = ((beds * per_bed) + (baths * per_bath) + (receptions * per_reception) + kitchen_cost) * tier_mult
    contingency = round(subtotal * cont_pct, 2)
    total = round(subtotal + contingency, 2)
    weeks_estimate = int(max(2, min(24, -(-total // 8000))))

    return {
        "outputs": {
            "refurb_subtotal": round(subtotal, 2),
            "contingency": contingency,
            "refurb_total_estimate": total,
            "estimated_duration_weeks": weeks_estimate,
            "quality_tier": quality,
        },
        "assumptions": [
            "Quick estimate uses average unit costs from the Propreneur UK refurb catalogue.",
            "Light = cosmetic refresh; Standard = mid-spec landlord refurb; Full = higher-spec fit-out.",
            "Contingency added on top. Use the Refurb bill of quantities (BOQ) calculator for line-item accuracy.",
        ],
    }


# ---------------------------------------------------------- boq_estimator -
BOQ_SCOPE_VOCABULARY = frozenset(
    {
        "repaint",
        "reflooring",
        "replaster",
        "rewire",
        "new_kitchen_fit_out",
        "new_bathroom_fit_out",
    }
)

BOQ_ESTIMATOR_RULES: Rules = {
    "rooms": ["required", "array", "min:1"],
    "rooms.*.label": ["required", "string"],
    "rooms.*.floor_area_sqm": ["required", "numeric", "min:0.01"],
    "rooms.*.room_type": ["nullable", "string", "in:bedroom,bathroom,kitchen,reception,hallway,other"],
    "rooms.*.scope": ["nullable", "array"],
    "rooms.*.flooring_material": ["nullable", "string", "in:carpet,laminate,vinyl,tile"],
    "quality": ["nullable", "string", "in:light,standard,full"],
    "contingency_pct": ["nullable", "numeric", "min:0", "max:0.25"],
}


def _boq_quality_tier_mult(quality: str) -> float:
    return {"light": 0.55, "full": 1.35}.get(quality, 1.0)


def _boq_fitout_rate(config: ConfigResolver, prefix: str, quality: str) -> float:
    key = f"{prefix}_fitout_gbp_{quality}"
    fallback = {"light": 3500.0, "standard": 6500.0, "full": 12000.0}[quality if quality in {"light", "standard", "full"} else "standard"]
    if prefix == "boq_bathroom":
        fallback = {"light": 2800.0, "standard": 4500.0, "full": 7500.0}[quality if quality in {"light", "standard", "full"} else "standard"]
    return float(config.get(key) or fallback)


def calculate_boq_estimator(inputs: dict, config: ConfigResolver) -> CalcResult:
    from keprix.property_calculators.validation import ValidationError

    rooms = inputs.get("rooms") or []
    quality = str(inputs.get("quality") or "standard")
    cont_pct = _num(inputs, "contingency_pct", 0.10)
    tier_mult = _boq_quality_tier_mult(quality)

    paint_rate = float(config.get("boq_paint_gbp_per_sqm") or 8.0)
    paint_litres_per_sqm = float(config.get("boq_paint_litres_per_sqm") or 0.12)
    paintable_mult = float(config.get("boq_paintable_sqm_per_floor_sqm") or 3.2)
    plaster_rate = float(config.get("boq_plaster_gbp_per_sqm") or 18.0)
    plasterable_mult = float(config.get("boq_plasterable_sqm_per_floor_sqm") or 3.2)
    rewire_rate = float(config.get("boq_rewire_gbp_per_room") or 850.0)
    default_flooring = str(config.get("boq_flooring_default_material") or "laminate")
    flooring_rates = {
        "carpet": float(config.get("boq_flooring_gbp_per_sqm_carpet") or 28.0),
        "laminate": float(config.get("boq_flooring_gbp_per_sqm_laminate") or 32.0),
        "vinyl": float(config.get("boq_flooring_gbp_per_sqm_vinyl") or 26.0),
        "tile": float(config.get("boq_flooring_gbp_per_sqm_tile") or 45.0),
    }

    scope_errors: dict[str, list[str]] = {}
    line_items: list[dict[str, Any]] = []
    rooms_report: list[dict[str, Any]] = []
    category_subtotals: dict[str, float] = {
        "paint": 0.0,
        "flooring": 0.0,
        "plaster": 0.0,
        "electrical": 0.0,
        "kitchen": 0.0,
        "bathroom": 0.0,
    }

    for idx, room in enumerate(rooms):
        if not isinstance(room, dict):
            continue
        label = str(room.get("label") or f"Room {idx + 1}")
        floor_area = float(room.get("floor_area_sqm") or 0)
        room_type = str(room.get("room_type") or "")
        scope = room.get("scope") or []
        if not isinstance(scope, list):
            scope = []
        scope = [str(item).strip() for item in scope if str(item).strip()]

        invalid = [item for item in scope if item not in BOQ_SCOPE_VOCABULARY]
        if invalid:
            scope_errors[f"rooms.{idx}.scope"] = [f"unknown scope item(s): {', '.join(invalid)}"]

        if not scope:
            rooms_report.append(
                {
                    "label": label,
                    "room_type": room_type or None,
                    "floor_area_sqm": round(floor_area, 2),
                    "status": "no work specified",
                    "line_items": [],
                    "room_subtotal": 0.0,
                }
            )
            continue

        room_lines: list[dict[str, Any]] = []
        for work in scope:
            if work == "repaint":
                quantity = round(floor_area * paintable_mult, 2)
                litres = round(quantity * paint_litres_per_sqm, 2)
                unit_rate = round(paint_rate * tier_mult, 2)
                line_cost = round(quantity * unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "sqm paintable",
                    "litres": litres,
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "paint",
                }
            elif work == "reflooring":
                material = str(room.get("flooring_material") or default_flooring)
                if material not in flooring_rates:
                    scope_errors.setdefault(f"rooms.{idx}.flooring_material", []).append(
                        f"must be one of {', '.join(flooring_rates)} when reflooring is scoped"
                    )
                    continue
                quantity = round(floor_area, 2)
                unit_rate = round(flooring_rates[material] * tier_mult, 2)
                line_cost = round(quantity * unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "sqm floor",
                    "flooring_material": material,
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "flooring",
                }
            elif work == "replaster":
                quantity = round(floor_area * plasterable_mult, 2)
                unit_rate = round(plaster_rate * tier_mult, 2)
                line_cost = round(quantity * unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "sqm plasterable",
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "plaster",
                }
            elif work == "rewire":
                quantity = 1.0
                unit_rate = rewire_rate
                line_cost = round(unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "room (rough rate)",
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "electrical",
                    "note": "Rough per-room rewiring allowance; actual cost varies widely with property age and access.",
                }
            elif work == "new_kitchen_fit_out":
                quantity = 1.0
                unit_rate = _boq_fitout_rate(config, "boq_kitchen", quality)
                line_cost = round(unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "kitchen unit",
                    "quality_tier": quality,
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "kitchen",
                }
            elif work == "new_bathroom_fit_out":
                quantity = 1.0
                unit_rate = _boq_fitout_rate(config, "boq_bathroom", quality)
                line_cost = round(unit_rate, 2)
                entry = {
                    "room": label,
                    "work_item": work,
                    "quantity": quantity,
                    "quantity_unit": "bathroom unit",
                    "quality_tier": quality,
                    "unit_rate_gbp": unit_rate,
                    "line_cost_gbp": line_cost,
                    "category": "bathroom",
                }
            else:
                continue

            room_lines.append(entry)
            line_items.append(entry)
            category_subtotals[entry["category"]] = round(category_subtotals[entry["category"]] + line_cost, 2)

        rooms_report.append(
            {
                "label": label,
                "room_type": room_type or None,
                "floor_area_sqm": round(floor_area, 2),
                "status": "costed",
                "line_items": room_lines,
                "room_subtotal": round(sum(item["line_cost_gbp"] for item in room_lines), 2),
            }
        )

    if scope_errors:
        raise ValidationError(scope_errors)

    refurb_subtotal = round(sum(category_subtotals.values()), 2)
    contingency = round(refurb_subtotal * cont_pct, 2)
    refurb_total = round(refurb_subtotal + contingency, 2)

    assumptions = [
        "Deterministic BOQ arithmetic only; no LLM inference and no guessed room dimensions.",
        f"Quality tier '{quality}' multiplier {tier_mult} applied to paint, flooring, and plaster line rates (not rewiring or fit-outs).",
        f"Paint: {paintable_mult} sqm paintable per sqm floor at GBP {paint_rate}/sqm ({paint_litres_per_sqm} L/sqm coverage disclosure).",
        f"Plaster: {plasterable_mult} sqm plasterable per sqm floor at GBP {plaster_rate}/sqm.",
        f"Reflooring default material when not specified: {default_flooring}.",
        f"Rewiring: rough GBP {rewire_rate} per room (not area-based).",
        f"Kitchen fit-out ({quality}): GBP {_boq_fitout_rate(config, 'boq_kitchen', quality)} per kitchen scoped.",
        f"Bathroom fit-out ({quality}): GBP {_boq_fitout_rate(config, 'boq_bathroom', quality)} per bathroom scoped.",
        f"Contingency {round(cont_pct * 100, 1)}% on subtotal, same convention as mini_refurb.",
        "Rooms with an empty scope list cost zero and are reported as 'no work specified'.",
    ]

    return {
        "outputs": {
            "line_items": line_items,
            "category_subtotals": {k: round(v, 2) for k, v in category_subtotals.items()},
            "rooms_report": rooms_report,
            "refurb_subtotal": refurb_subtotal,
            "contingency": contingency,
            "refurb_total": refurb_total,
            "quality_tier": quality,
        },
        "assumptions": assumptions,
    }


# ----------------------------------------------------- mortgage_affordability
MORTGAGE_AFFORDABILITY_RULES: Rules = {
    "annual_income": ["required", "numeric", "min:1"],
    "joint_annual_income": ["nullable", "numeric", "min:0"],
    "monthly_credit_cards": ["nullable", "numeric", "min:0"],
    "monthly_loans": ["nullable", "numeric", "min:0"],
    "monthly_car_finance": ["nullable", "numeric", "min:0"],
    "monthly_other_commitments": ["nullable", "numeric", "min:0"],
    "deposit_amount": ["required", "numeric", "min:0"],
    "income_multiplier": ["nullable", "numeric", "min:3", "max:6"],
    "interest_rate": ["nullable", "numeric", "min:0", "max:0.25"],
    "term_years": ["nullable", "numeric", "min:1", "max:40"],
}


def calculate_mortgage_affordability(inputs: dict, config: ConfigResolver) -> CalcResult:
    from keprix.property_calculators.constants import MORTGAGE_DEFAULT_INTEREST_RATE, MORTGAGE_DEFAULT_TERM_YEARS

    income = _num(inputs, "annual_income") + _num(inputs, "joint_annual_income")
    mult = _num(inputs, "income_multiplier", 4.5)
    commitments = (
        _num(inputs, "monthly_credit_cards") + _num(inputs, "monthly_loans")
        + _num(inputs, "monthly_car_finance") + _num(inputs, "monthly_other_commitments")
    )
    annual_commitments = commitments * 12
    gross_borrow = max(0.0, (income * mult) - (annual_commitments * 0.5))
    deposit = _num(inputs, "deposit_amount")
    max_price = gross_borrow + deposit

    rate = _num(inputs, "interest_rate", MORTGAGE_DEFAULT_INTEREST_RATE)
    years = round(_num(inputs, "term_years", MORTGAGE_DEFAULT_TERM_YEARS))
    months = max(1, years * 12)
    r = rate / 12
    loan_for_payment = gross_borrow
    if r <= 0:
        monthly_payment = loan_for_payment / months
    else:
        pow_ = (1 + r) ** months
        monthly_payment = loan_for_payment * (r * pow_) / (pow_ - 1)

    stress_rate = rate + MORTGAGE_STRESS_TEST_RATE_OFFSET
    sr = stress_rate / 12
    stress_pow = (1 + sr) ** months
    stress_payment = loan_for_payment * (sr * stress_pow) / (stress_pow - 1)

    return {
        "outputs": {
            "max_loan_amount": round(gross_borrow, 2),
            "max_purchase_price": round(max_price, 2),
            "deposit_amount": round(deposit, 2),
            "income_used": round(income, 2),
            "income_multiplier_used": mult,
            "monthly_payment_estimate": round(monthly_payment, 2),
            "stressed_monthly_payment": round(stress_payment, 2),
            "monthly_commitments": round(commitments, 2),
            "deal_stacks": gross_borrow > 0 and monthly_payment > 0,
        },
        "assumptions": [
            "Max loan = (gross income x multiplier) minus half of annualised monthly commitments (illustrative lender stress).",
            "Max purchase price = max loan + deposit.",
            "Monthly payment uses capital repayment at stated rate and term on the full max loan.",
            f"Stressed payment adds {round(MORTGAGE_STRESS_TEST_RATE_OFFSET * 100, 1)}% to the interest rate for illustration (FCA-style stress simplification).",
        ],
    }


# --------------------------------------------------------------- cgt ------
CGT_RULES: Rules = {
    "purchase_date": ["required", "date"],
    "sale_date": ["required", "date"],
    "purchase_price": ["required", "numeric", "min:1"],
    "purchase_fees": ["nullable", "numeric", "min:0"],
    "improvement_costs": ["nullable", "numeric", "min:0"],
    "sale_price": ["required", "numeric", "min:1"],
    "sale_fees": ["nullable", "numeric", "min:0"],
    "months_lived_in_property": ["nullable", "integer", "min:0", "max:600"],
    "tax_band": ["nullable", "string", "in:basic,higher"],
}


def _months_between(start: date, end: date) -> int:
    return max(1, (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0))


def calculate_cgt(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    purchase_fees = _num(inputs, "purchase_fees")
    improvements = _num(inputs, "improvement_costs")
    sale = _num(inputs, "sale_price")
    sale_fees = _num(inputs, "sale_fees")

    cost_base = purchase + purchase_fees + improvements
    gross_gain = max(0.0, sale - sale_fees - cost_base)

    purchase_date = datetime.strptime(str(inputs["purchase_date"])[:10], "%Y-%m-%d").date()
    sale_date = datetime.strptime(str(inputs["sale_date"])[:10], "%Y-%m-%d").date()
    total_months = _months_between(purchase_date, sale_date)
    months_lived = min(total_months, max(0, int(_num(inputs, "months_lived_in_property"))))
    prr_fraction = min(1.0, months_lived / total_months)
    taxable_before_allowance = max(0.0, gross_gain * (1.0 - prr_fraction))
    annual_exemption = CGT_ANNUAL_EXEMPTION
    after_allowance = max(0.0, taxable_before_allowance - annual_exemption)

    band = str(inputs.get("tax_band") or "basic")
    rate = CGT_RESIDENTIAL_RATE_HIGHER if band == "higher" else CGT_RESIDENTIAL_RATE_BASIC
    tax_due = round(after_allowance * rate, 2)
    net_after_tax = round(sale - sale_fees - cost_base - tax_due, 2)

    return {
        "outputs": {
            "gross_gain": round(gross_gain, 2),
            "prr_relief_pct": round(prr_fraction * 100, 2),
            "taxable_gain_before_allowance": round(taxable_before_allowance, 2),
            "annual_exempt_amount_used": round(min(annual_exemption, taxable_before_allowance), 2),
            "taxable_gain_after_allowance": round(after_allowance, 2),
            "cgt_rate_pct": round(rate * 100, 2),
            "cgt_due": tax_due,
            "net_profit_after_cgt": net_after_tax,
            "ownership_months": total_months,
        },
        "assumptions": [
            f"Illustrative UK residential CGT for 2024/25 tax year; annual exempt amount £{annual_exemption:,.0f}.",
            "Private Residence Relief (PRR) applied as months lived / total months owned.",
            f"Basic rate {round(CGT_RESIDENTIAL_RATE_BASIC * 100)}% and higher rate {round(CGT_RESIDENTIAL_RATE_HIGHER * 100)}% on residential property gains (simplified single band selection).",
            "Does not model letting relief, spousal transfers, or company ownership. Not tax advice.",
        ],
    }


# ------------------------------------------------------------- btl_roi ----
BTL_ROI_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "stamp_duty": ["nullable", "numeric", "min:0"],
    "refurb_cost": ["nullable", "numeric", "min:0"],
    "legal_survey_fees": ["nullable", "numeric", "min:0"],
    "deposit_amount": ["required", "numeric", "min:0"],
    "mortgage_interest_rate": ["nullable", "numeric", "min:0", "max:0.25"],
    "mortgage_interest_only": ["nullable", "boolean"],
    "mortgage_term_years": ["nullable", "numeric", "min:1", "max:40"],
    "monthly_rent": ["required", "numeric", "min:0"],
    "monthly_service_charge": ["nullable", "numeric", "min:0"],
    "annual_maintenance": ["nullable", "numeric", "min:0"],
    "annual_insurance": ["nullable", "numeric", "min:0"],
    "letting_agent_pct": ["nullable", "numeric", "min:0", "max:1"],
    "use_additional_sdlt": ["nullable", "boolean"],
}


def calculate_btl_roi(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    deposit = _num(inputs, "deposit_amount")
    loan = max(0.0, purchase - deposit)
    rate = _num(inputs, "mortgage_interest_rate", 0.055)
    term_years = round(_num(inputs, "mortgage_term_years", 25))
    io = inputs.get("mortgage_interest_only")
    io = True if io is None else bool(io)
    months = max(1, term_years * 12)
    r = rate / 12

    if io or r <= 0:
        monthly_mortgage = loan * r
    else:
        pow_ = (1 + r) ** months
        monthly_mortgage = loan * (r * pow_) / (pow_ - 1)

    monthly_rent = _num(inputs, "monthly_rent")
    service = _num(inputs, "monthly_service_charge")
    maint_annual = _num(inputs, "annual_maintenance")
    ins_annual = _num(inputs, "annual_insurance")
    agent_pct = _num(inputs, "letting_agent_pct", 0.10)
    agent_monthly = monthly_rent * agent_pct
    maint_monthly = maint_annual / 12
    ins_monthly = ins_annual / 12

    monthly_cashflow = monthly_rent - monthly_mortgage - service - agent_monthly - maint_monthly - ins_monthly
    annual_cashflow = monthly_cashflow * 12

    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    stamp = (
        _num(inputs, "stamp_duty")
        if inputs.get("stamp_duty") not in (None, "")
        else (financial.stamp_duty_additional_property(purchase) if use_additional else financial.stamp_duty_standard_residential(purchase))
    )

    cash_in = deposit + stamp + _num(inputs, "refurb_cost") + _num(inputs, "legal_survey_fees")
    cash_in = max(1.0, cash_in)
    cash_on_cash = round((annual_cashflow / cash_in) * 100, 4)
    gross_yield = financial.gross_yield_percent(monthly_rent, purchase) or 0.0

    return {
        "outputs": {
            "monthly_mortgage": round(monthly_mortgage, 2),
            "monthly_cashflow": round(monthly_cashflow, 2),
            "annual_cashflow": round(annual_cashflow, 2),
            "cash_on_cash_pct": cash_on_cash,
            "gross_yield_pct": round(gross_yield, 4),
            "total_cash_invested": round(cash_in, 2),
            "stamp_duty_used": round(stamp, 2),
            "loan_amount": round(loan, 2),
            "deal_stacks": monthly_cashflow > 0,
        },
        "assumptions": [
            "Cash invested = deposit + SDLT + refurb + legal/survey (unless SDLT entered manually).",
            "Cash-on-cash = annual pre-tax cashflow / total cash invested.",
            "Mortgage payment uses interest-only by default, or repayment amortisation if unchecked.",
        ],
    }


# ---------------------------------------------------------------- sa ------
SA_RULES: Rules = {
    "nightly_rate": ["required", "numeric", "min:0"],
    "occupancy_pct": ["required", "numeric", "min:0", "max:100"],
    "rooms": ["nullable", "integer", "min:1", "max:50"],
    "purchase_price": ["nullable", "numeric", "min:1"],
    "cleaning_pct_revenue": ["nullable", "numeric", "min:0", "max:0.5"],
    "cleaning_monthly": ["nullable", "numeric", "min:0"],
    "utilities_monthly": ["nullable", "numeric", "min:0"],
    "management_pct_revenue": ["nullable", "numeric", "min:0", "max:0.5"],
    "management_fee_monthly": ["nullable", "numeric", "min:0"],
    "platform_pct_revenue": ["nullable", "numeric", "min:0", "max:0.25"],
    "other_monthly": ["nullable", "numeric", "min:0"],
    "council_tax_monthly": ["nullable", "numeric", "min:0"],
    "insurance_monthly": ["nullable", "numeric", "min:0"],
    "setup_costs": ["nullable", "numeric", "min:0"],
    "monthly_mortgage": ["nullable", "numeric", "min:0"],
}


def calculate_sa(inputs: dict, config: ConfigResolver) -> CalcResult:
    nightly = _num(inputs, "nightly_rate")
    occ = _num(inputs, "occupancy_pct") / 100
    rooms = max(1, int(_num(inputs, "rooms", 1)))
    purchase = _num(inputs, "purchase_price")

    clean_pct = _num(inputs, "cleaning_pct_revenue", 0.25)
    clean_fixed = _num(inputs, "cleaning_monthly")
    mgmt_pct = _num(inputs, "management_pct_revenue", 0.15)
    mgmt_fixed = _num(inputs, "management_fee_monthly")
    plat_pct = _num(inputs, "platform_pct_revenue", 0.10)
    utils = _num(inputs, "utilities_monthly")
    council_tax = _num(inputs, "council_tax_monthly")
    insurance = _num(inputs, "insurance_monthly")
    other = _num(inputs, "other_monthly")
    mortgage = _num(inputs, "monthly_mortgage")
    setup = _num(inputs, "setup_costs")

    monthly_revenue = round(nightly * occ * 30.4 * rooms, 2)
    annual_revenue = round(monthly_revenue * 12, 2)
    cleaning = clean_fixed * 12 if clean_fixed > 0 else round(annual_revenue * clean_pct, 2)
    mgmt = mgmt_fixed * 12 if mgmt_fixed > 0 else round(annual_revenue * mgmt_pct, 2)
    plat = round(annual_revenue * plat_pct, 2)
    fixed_monthly_costs = (utils + council_tax + insurance + other) * 12
    opex = round(cleaning + mgmt + plat + fixed_monthly_costs, 2)
    noi = round(annual_revenue - opex, 2)
    monthly_noi = round(noi / 12, 2)
    monthly_cashflow = round(monthly_noi - mortgage, 2)
    annual_cashflow = round(monthly_cashflow * 12, 2)

    net_margin_pct = round((noi / annual_revenue) * 100, 4) if annual_revenue > 0 else 0.0
    opex_ratio = round((opex / annual_revenue) * 100, 4) if annual_revenue > 0 else 0.0
    revpar = round(annual_revenue / rooms / 365, 2) if rooms > 0 else 0.0
    gross_yield = (financial.gross_yield_percent(monthly_revenue, purchase) or 0.0) if (purchase > 0 and monthly_revenue > 0) else None
    net_yield = round((noi / purchase) * 100, 4) if (purchase > 0 and noi > 0) else None
    return_on_setup = round((noi / setup) * 100, 4) if (setup > 0 and noi > 0) else None
    setup_recovery_months = round(setup / monthly_cashflow, 2) if (monthly_cashflow > 0 and setup > 0) else None

    return {
        "outputs": {
            "monthly_revenue": monthly_revenue,
            "annual_revenue": annual_revenue,
            "operating_costs": opex,
            "annual_noi": noi,
            "monthly_noi": monthly_noi,
            "monthly_cashflow": monthly_cashflow,
            "annual_cashflow": annual_cashflow,
            "net_margin_pct": net_margin_pct,
            "operating_cost_ratio_pct": opex_ratio,
            "revpar_daily": revpar,
            "gross_yield_pct": gross_yield,
            "net_yield_pct": net_yield,
            "setup_costs_total": round(setup, 2),
            "return_on_setup_capital_pct": return_on_setup,
            "setup_recovery_months": setup_recovery_months,
            "deal_stacks": monthly_cashflow > 0,
            "rooms_used": rooms,
        },
        "assumptions": [
            "Monthly revenue = nightly rate x occupancy x 30.4 x room count.",
            f"Cleaning uses a fixed monthly fee when entered; otherwise {round(clean_pct * 100, 1)}% of revenue.",
            f"Management uses a fixed monthly fee when entered; otherwise {round(mgmt_pct * 100, 1)}% of revenue.",
            f"Platform fee defaults to {round(plat_pct * 100, 1)}% of revenue (Airbnb/Booking commission proxy).",
        ],
    }


# ------------------------------------------------------------- skip_hire --
SKIP_HIRE_RULES: Rules = {
    "waste_type": ["nullable", "string", "max:64"],
    "location": ["nullable", "string", "max:64"],
    "rooms_stripped": ["nullable", "integer", "min:0", "max:30"],
    "internal_walls_removed": ["nullable", "integer", "min:0", "max:20"],
    "kitchen_bathroom_units": ["nullable", "integer", "min:0", "max:10"],
    "flooring_sqm": ["nullable", "numeric", "min:0", "max:500"],
    "black_bags": ["nullable", "integer", "min:0", "max:200"],
}

_SKIP_LOCATION_MULTIPLIER = {"london": 1.25, "south_east": 1.10, "midlands": 1.00, "north": 0.92, "scotland_wales": 0.95}
_SKIP_SIZES = [
    ("4_yard", 4, 220, 4),
    ("6_yard", 6, 280, 6),
    ("8_yard", 8, 320, 8),
    ("12_yard", 12, 420, 10),
    ("16_yard", 16, 520, 12),
]


def calculate_skip_hire(inputs: dict, config: ConfigResolver) -> CalcResult:
    rooms = int(_num(inputs, "rooms_stripped", 1))
    walls = int(_num(inputs, "internal_walls_removed"))
    units = int(_num(inputs, "kitchen_bathroom_units"))
    flooring = _num(inputs, "flooring_sqm")
    bags = int(_num(inputs, "black_bags"))

    cubic_yards = (rooms * 2.0) + (walls * 1.5) + (units * 3.0) + (flooring * 0.08) + (bags * 0.05)
    cubic_yards = max(1.0, round(cubic_yards, 2))

    waste_type = str(inputs.get("waste_type") or "mixed").lower()
    if "rubble" in waste_type or "soil" in waste_type:
        cubic_yards = min(cubic_yards, 8.0)

    recommended = None
    for key, yards, hire, max_tonnes in _SKIP_SIZES:
        if cubic_yards <= yards * 0.95:
            recommended = {"key": key, "label": f"{yards} yard", "yards": yards, "hire": hire, "max_tonnes": max_tonnes}
            break
    if recommended is None:
        _, yards, hire, max_tonnes = _SKIP_SIZES[-1]
        recommended = {"key": "16_yard", "label": f"{yards} yard (may need multiple skips)", "yards": yards, "hire": hire, "max_tonnes": max_tonnes}

    location = str(inputs.get("location") or "midlands").lower()
    mult = _SKIP_LOCATION_MULTIPLIER.get(location, 1.0)
    hire_cost = round(recommended["hire"] * mult, 2)
    permits_estimate = round(50 * mult, 2)

    return {
        "outputs": {
            "estimated_cubic_yards": cubic_yards,
            "recommended_skip_size": recommended["label"],
            "recommended_skip_yards": recommended["yards"],
            "estimated_hire_cost": hire_cost,
            "permit_allowance_estimate": permits_estimate,
            "total_estimate": round(hire_cost + permits_estimate, 2),
            "max_weight_tonnes": recommended["max_tonnes"],
        },
        "assumptions": [
            "Volume model is illustrative: rooms stripped, walls, kitchen/bath units, flooring m2, and bags.",
            "Rubble/soil waste is capped at 8-yard skip due to weight limits on collection vehicles.",
            "Hire costs are UK indicative averages; location multiplier adjusts London and regions.",
            "Add permit costs if the skip is placed on public highway (council dependent).",
        ],
    }


# ------------------------------------------------------ bmv_no_money_down -
BMV_RULES: Rules = {
    "market_value": ["required", "numeric", "min:1"],
    "purchase_price": ["required", "numeric", "min:1"],
    "remortgage_ltv": ["nullable", "numeric", "min:0.01", "max:1"],
    "bridging_arrangement_fee_pct": ["nullable", "numeric", "min:0", "max:0.2"],
    "legal_fees": ["nullable", "numeric", "min:0"],
    "valuation_fee": ["nullable", "numeric", "min:0"],
    "property_value_for_sdlt": ["nullable", "numeric", "min:1"],
    "is_additional_property": ["nullable", "boolean"],
}


def _normalize_rate(value: float, default: float) -> float:
    if value <= 0:
        return default
    return value / 100 if value > 1 else value


def calculate_bmv_no_money_down(inputs: dict, config: ConfigResolver) -> CalcResult:
    market_value = _num(inputs, "market_value")
    purchase_price = _num(inputs, "purchase_price")
    remortgage_ltv = _normalize_rate(_num(inputs, "remortgage_ltv", 0.75), 0.75)
    bridging_fee_pct = _normalize_rate(_num(inputs, "bridging_arrangement_fee_pct", 0.02), 0.02)
    legal_fees = _num(inputs, "legal_fees", 2500)
    valuation_fee = _num(inputs, "valuation_fee", 500)
    sdlt_value = _num(inputs, "property_value_for_sdlt") or purchase_price
    is_additional = inputs.get("is_additional_property")
    is_additional = True if is_additional is None else bool(is_additional)

    discount_amount = market_value - purchase_price
    discount_pct = (discount_amount / market_value) * 100 if market_value > 0 else 0.0
    remortgage_amount = market_value * remortgage_ltv
    bridging_fee = purchase_price * bridging_fee_pct
    sdlt = (
        financial.stamp_duty_additional_property(sdlt_value)
        if is_additional
        else financial.stamp_duty_standard_residential(sdlt_value)
    )
    total_costs = bridging_fee + legal_fees + valuation_fee + sdlt

    proceeds_after_bridging = remortgage_amount - purchase_price - bridging_fee
    net_cash_position = proceeds_after_bridging - legal_fees - valuation_fee - sdlt
    is_no_money_down = net_cash_position >= 0

    breakeven_discount_pct = (
        ((total_costs + purchase_price - remortgage_amount) / market_value) * 100 if market_value > 0 else 0.0
    )

    if is_no_money_down and net_cash_position >= 5000:
        verdict = "cash_out"
    elif is_no_money_down:
        verdict = "no_money_down"
    elif discount_pct >= 20:
        verdict = "reduced_money_in"
    else:
        verdict = "standard_btl"

    return {
        "outputs": {
            "market_value": round(market_value),
            "purchase_price": round(purchase_price),
            "discount_amount": round(discount_amount),
            "discount_pct": round(discount_pct, 1),
            "remortgage_amount": round(remortgage_amount),
            "remortgage_ltv_pct": round(remortgage_ltv * 100, 1),
            "bridging_amount": round(purchase_price),
            "bridging_fee": round(bridging_fee),
            "bridging_arrangement_fee_pct": round(bridging_fee_pct * 100, 2),
            "sdlt": round(sdlt),
            "legal_fees": round(legal_fees),
            "valuation_fee": round(valuation_fee),
            "total_costs": round(total_costs),
            "proceeds_after_bridging": round(proceeds_after_bridging),
            "net_cash_position": round(net_cash_position),
            "is_no_money_down": is_no_money_down,
            "breakeven_discount_pct": round(max(0.0, breakeven_discount_pct), 1),
            "max_purchase_for_no_money_down": max(0, round(market_value * (1 - max(0.0, breakeven_discount_pct) / 100))),
            "verdict": verdict,
        },
        "assumptions": [
            "Same-day remortgage model: 100% bridging on purchase price; remortgage at market value x LTV (default 75%).",
            f"SDLT uses {'additional dwelling' if is_additional else 'standard residential'} bands via {SDLT_RULES_VERSION}.",
            "Bridging arrangement fee is a one-off percentage of purchase price (default 2%).",
            "Net cash position = remortgage proceeds - purchase - bridging fee - legal - valuation - SDLT.",
            "Not legal or tax advice; lender valuation and same-day remortgage availability vary.",
        ],
    }


# --------------------------------------------------------------- hmo ------
HMO_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "rooms": ["required", "integer", "min:2", "max:20"],
    "rent_per_room_monthly": ["required", "numeric", "min:0"],
    "void_months_per_year": ["nullable", "numeric", "min:0", "max:3"],
    "annual_licence_fee": ["nullable", "numeric", "min:0"],
    "annual_council_tax": ["nullable", "numeric", "min:0"],
    "annual_utilities": ["nullable", "numeric", "min:0"],
    "annual_insurance": ["nullable", "numeric", "min:0"],
    "management_pct_rent": ["nullable", "numeric", "min:0", "max:0.25"],
    "management_fee_monthly": ["nullable", "numeric", "min:0"],
    "maintenance_pct_rent": ["nullable", "numeric", "min:0", "max:0.25"],
    "maintenance_monthly": ["nullable", "numeric", "min:0"],
    "annual_mortgage": ["nullable", "numeric", "min:0"],
    "monthly_mortgage": ["nullable", "numeric", "min:0"],
    "total_investment": ["nullable", "numeric", "min:1"],
    "deposit_amount": ["nullable", "numeric", "min:0"],
    "legal_fees": ["nullable", "numeric", "min:0"],
    "survey_fees": ["nullable", "numeric", "min:0"],
    "setup_costs": ["nullable", "numeric", "min:0"],
    "use_additional_sdlt": ["nullable", "boolean"],
    "stamp_duty": ["nullable", "numeric", "min:0"],
}


def calculate_hmo(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    rooms = int(_num(inputs, "rooms"))
    rpm = _num(inputs, "rent_per_room_monthly")
    void_months = _num(inputs, "void_months_per_year", 1)

    gross_monthly = rpm * rooms
    gross_potential_annual = gross_monthly * 12
    void_allowance = rpm * void_months * rooms
    annual_gross = gross_potential_annual - void_allowance

    licence = _num(inputs, "annual_licence_fee", 800)
    ct = _num(inputs, "annual_council_tax")
    utils = _num(inputs, "annual_utilities")
    ins = _num(inputs, "annual_insurance")
    mgmt_pct = _num(inputs, "management_pct_rent", 0.12)
    mgmt_fixed_monthly = _num(inputs, "management_fee_monthly")
    annual_mgmt = mgmt_fixed_monthly * 12 if mgmt_fixed_monthly > 0 else gross_potential_annual * mgmt_pct

    maint_pct = _num(inputs, "maintenance_pct_rent", 0.05)
    maint_fixed_monthly = _num(inputs, "maintenance_monthly")
    annual_maint = maint_fixed_monthly * 12 if maint_fixed_monthly > 0 else gross_potential_annual * maint_pct

    opex = round(licence + ct + utils + ins + annual_mgmt + annual_maint, 2)
    noi = round(annual_gross - opex, 2)

    annual_mortgage = (
        _num(inputs, "annual_mortgage")
        if inputs.get("annual_mortgage") not in (None, "")
        else _num(inputs, "monthly_mortgage") * 12
    )

    monthly_noi = noi / 12
    monthly_mortgage = annual_mortgage / 12
    monthly_cashflow = round(monthly_noi - monthly_mortgage, 2)
    annual_cashflow = round(monthly_cashflow * 12, 2)

    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    stamp = (
        _num(inputs, "stamp_duty")
        if inputs.get("stamp_duty") not in (None, "")
        else (financial.stamp_duty_additional_property(purchase) if use_additional else 0.0)
    )

    deposit = _num(inputs, "deposit_amount")
    legal = _num(inputs, "legal_fees")
    survey = _num(inputs, "survey_fees")
    setup = _num(inputs, "setup_costs")
    investment = _num(inputs, "total_investment")
    if investment <= 0:
        investment = max(1.0, (purchase * 0.25) + stamp + legal + survey + setup)

    gross_yield = financial.gross_yield_percent(gross_monthly, purchase) or 0.0
    net_yield = round((noi / purchase) * 100, 4) if purchase > 0 else 0.0
    coc = round((annual_cashflow / investment) * 100, 4) if investment > 0 else 0.0
    opex_ratio = round((opex / gross_potential_annual) * 100, 4) if gross_potential_annual > 0 else 0.0
    profit_per_room = round(annual_cashflow / rooms, 2) if rooms > 0 else 0.0
    breakeven_occupancy = (
        round(min(100, ((opex + annual_mortgage) / gross_potential_annual) * 100), 4) if gross_potential_annual > 0 else 0.0
    )

    return {
        "outputs": {
            "gross_monthly_rent": round(gross_monthly, 2),
            "gross_annual_rent": round(annual_gross, 2),
            "void_allowance_annual": round(void_allowance, 2),
            "operating_expenses": opex,
            "noi_annual": noi,
            "monthly_noi": round(monthly_noi, 2),
            "annual_mortgage": round(annual_mortgage, 2),
            "monthly_cashflow": monthly_cashflow,
            "annual_cashflow": annual_cashflow,
            "gross_yield_pct": round(gross_yield, 4),
            "net_yield_pct": net_yield,
            "cash_on_cash_pct": coc,
            "operating_cost_ratio_pct": opex_ratio,
            "profit_per_room": profit_per_room,
            "breakeven_occupancy_pct": breakeven_occupancy,
            "stamp_duty_computed": round(stamp, 2),
            "total_investment": round(investment, 2),
            "deal_stacks": monthly_cashflow > 0,
            "rooms_used": rooms,
        },
        "assumptions": [
            "Gross annual rent = (rent per room x rooms x 12) minus void allowance (void months x rent per room x rooms).",
            "Operating costs include licence, council tax, utilities, insurance, management, and maintenance.",
            f"Management uses a fixed monthly fee when entered; otherwise {round(mgmt_pct * 100, 1)}% of gross potential rent.",
            "Monthly cashflow = NOI/12 minus monthly mortgage.",
            "Breakeven occupancy = (opex + annual mortgage) / gross potential annual rent.",
        ],
    }


# --------------------------------------------------------------- r2r ------
R2R_RULES: Rules = {
    "rent_from_subtenants_monthly": ["required_without:rent_per_room_monthly", "nullable", "numeric", "min:0"],
    "rent_per_room_monthly": ["nullable", "numeric", "min:0"],
    "rent_to_landlord_monthly": ["required", "numeric", "min:0"],
    "subtenant_count": ["nullable", "integer", "min:1", "max:50"],
    "management_fee_monthly": ["nullable", "numeric", "min:0"],
    "management_pct_rent": ["nullable", "numeric", "min:0", "max:0.5"],
    "utilities_monthly": ["nullable", "numeric", "min:0"],
    "insurance_monthly": ["nullable", "numeric", "min:0"],
    "council_tax_monthly": ["nullable", "numeric", "min:0"],
    "maintenance_monthly": ["nullable", "numeric", "min:0"],
    "maintenance_pct_rent": ["nullable", "numeric", "min:0", "max:0.5"],
    "cleaning_monthly": ["nullable", "numeric", "min:0"],
    "compliance_monthly": ["nullable", "numeric", "min:0"],
    "void_months_subrent": ["nullable", "numeric", "min:0", "max:3"],
    "landlord_deposit": ["nullable", "numeric", "min:0"],
    "furnishing_setup": ["nullable", "numeric", "min:0"],
    "licence_and_compliance_setup": ["nullable", "numeric", "min:0"],
    "legal_and_marketing_setup": ["nullable", "numeric", "min:0"],
    "other_setup_costs": ["nullable", "numeric", "min:0"],
}


def calculate_r2r(inputs: dict, config: ConfigResolver) -> CalcResult:
    doors = max(1, int(_num(inputs, "subtenant_count", 1)))
    rent_per_room = _num(inputs, "rent_per_room_monthly")
    gross_monthly = _num(inputs, "rent_from_subtenants_monthly")
    if gross_monthly <= 0 and rent_per_room > 0:
        gross_monthly = rent_per_room * doors

    head_rent = _num(inputs, "rent_to_landlord_monthly")
    mgmt_pct = _num(inputs, "management_pct_rent") or (float(config.get("r2r_default_management_pct")) / 100)
    mgmt_fixed = _num(inputs, "management_fee_monthly")
    mgmt_monthly = mgmt_fixed if mgmt_fixed > 0 else round(gross_monthly * mgmt_pct, 2)

    maint_pct = _num(inputs, "maintenance_pct_rent", 0.05)
    maint_fixed = _num(inputs, "maintenance_monthly")
    maint_monthly = maint_fixed if maint_fixed > 0 else round(gross_monthly * maint_pct, 2)

    utilities = _num(inputs, "utilities_monthly")
    insurance = _num(inputs, "insurance_monthly")
    council_tax = _num(inputs, "council_tax_monthly")
    cleaning = _num(inputs, "cleaning_monthly")
    compliance = _num(inputs, "compliance_monthly")

    monthly_opex = round(mgmt_monthly + utilities + insurance + council_tax + maint_monthly + cleaning + compliance, 2)
    gross_margin_monthly = round(gross_monthly - head_rent, 2)
    monthly_profit = round(gross_margin_monthly - monthly_opex, 2)

    void_months = _num(inputs, "void_months_subrent", 1)
    annual_gross = round(gross_monthly * 12, 2)
    annual_head_rent = round(head_rent * 12, 2)
    annual_opex = round(monthly_opex * 12, 2)
    annual_profit = round((monthly_profit * 12) - (gross_margin_monthly * void_months), 2)

    setup_total = round(
        _num(inputs, "landlord_deposit") + _num(inputs, "furnishing_setup") + _num(inputs, "licence_and_compliance_setup")
        + _num(inputs, "legal_and_marketing_setup") + _num(inputs, "other_setup_costs"),
        2,
    )

    gross_margin_pct = round((gross_margin_monthly / gross_monthly) * 100, 4) if gross_monthly > 0 else 0.0
    operating_cost_ratio_pct = round((monthly_opex / gross_monthly) * 100, 4) if gross_monthly > 0 else 0.0
    net_margin_pct = round((annual_profit / annual_gross) * 100, 4) if annual_gross > 0 else 0.0
    profit_per_door = round(annual_profit / doors, 2) if doors > 0 else 0.0

    breakeven_occupancy_pct = (
        round(min(100, ((head_rent + monthly_opex) / gross_monthly) * 100), 4) if gross_monthly > 0 else 0.0
    )

    return_on_setup_pct = round((annual_profit / setup_total) * 100, 4) if setup_total > 0 else 0.0
    setup_recovery_months = round(setup_total / monthly_profit, 2) if (monthly_profit > 0 and setup_total > 0) else None

    ten_pct_threshold = float(config.get("r2r_ten_percent_rule_pct")) / 100
    min_margin_pct = float(config.get("r2r_min_monthly_income_pct")) / 100

    ten_pct_rule_pass = (gross_monthly >= (head_rent * (1 + ten_pct_threshold))) if head_rent > 0 else gross_monthly > 0
    minimum_income_rule_pass = ((gross_monthly - head_rent) / head_rent >= min_margin_pct) if head_rent > 0 else gross_monthly > 0

    return {
        "outputs": {
            "rent_difference_monthly": gross_margin_monthly,
            "gross_margin_pct": gross_margin_pct,
            "monthly_operating_costs": monthly_opex,
            "monthly_profit": monthly_profit,
            "annual_gross_income": annual_gross,
            "annual_head_rent": annual_head_rent,
            "annual_operating_costs": annual_opex,
            "annual_profit": annual_profit,
            "profit_per_door": profit_per_door,
            "net_margin_pct": net_margin_pct,
            "operating_cost_ratio_pct": operating_cost_ratio_pct,
            "breakeven_occupancy_pct": breakeven_occupancy_pct,
            "setup_costs_total": setup_total,
            "return_on_setup_capital_pct": return_on_setup_pct,
            "setup_recovery_months": setup_recovery_months,
            "ten_percent_rule_pass": ten_pct_rule_pass,
            "minimum_income_rule_pass": minimum_income_rule_pass,
            "deal_stacks": monthly_profit > 0,
            "subtenant_count_used": doors,
            "rent_per_room_used": round(rent_per_room, 2) if rent_per_room > 0 else None,
        },
        "assumptions": [
            "Gross monthly income uses total subtenant rent, or rooms x rent per room when room rent is supplied.",
            f"Management uses a fixed monthly fee when entered; otherwise {round(mgmt_pct * 100, 1)}% of gross subtenant rent.",
            f"Maintenance uses a fixed monthly fee when entered; otherwise {round(maint_pct * 100, 1)}% of gross subtenant rent.",
            "Annual profit = (monthly profit x 12) minus void cost (gross margin x void months).",
            "Breakeven occupancy = (head rent + monthly operating costs) / gross subtenant rent.",
            f"10% rule: subtenant rent must be at least {config.get('r2r_ten_percent_rule_pct')}% above head rent.",
            f"Minimum margin rule: gross margin on head rent must be at least {config.get('r2r_min_monthly_income_pct')}%.",
        ],
    }


# --------------------------------------------------------------- brr ------
BRR_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "refurb_cost": ["required", "numeric", "min:0"],
    "post_refurb_value": ["required", "numeric", "min:1"],
    "legal_fees": ["nullable", "numeric", "min:0"],
    "survey_fees": ["nullable", "numeric", "min:0"],
    "finance_costs": ["nullable", "numeric", "min:0"],
    "refinance_ltv": ["nullable", "numeric", "min:0.1", "max:0.95"],
    "contingency_pct_refurb": ["nullable", "numeric", "min:0", "max:0.5"],
    "use_additional_sdlt": ["nullable", "boolean"],
    "monthly_rent": ["nullable", "numeric", "min:0"],
    "refinance_rate_annual": ["nullable", "numeric", "min:0", "max:0.3"],
    "management_fee_monthly": ["nullable", "numeric", "min:0"],
    "management_pct": ["nullable", "numeric", "min:0", "max:0.5"],
    "maintenance_monthly": ["nullable", "numeric", "min:0"],
    "maintenance_pct_rent": ["nullable", "numeric", "min:0", "max:0.5"],
    "insurance_monthly": ["nullable", "numeric", "min:0"],
    "utilities_monthly": ["nullable", "numeric", "min:0"],
    "council_tax_monthly": ["nullable", "numeric", "min:0"],
    "void_weeks_per_year": ["nullable", "numeric", "min:0", "max:12"],
}


def _brr_stress_tests(rent, refinance_value, base_rate, mgmt_pct, mgmt_fixed, maint_monthly, other_opex_monthly):
    scenarios = [
        {"label": "Base case", "rate_delta": 0, "rent_delta": 0, "value_mult": 1.0},
        {"label": "Rate +1%", "rate_delta": 0.01, "rent_delta": 0, "value_mult": 1.0},
        {"label": "Rate +2%", "rate_delta": 0.02, "rent_delta": 0, "value_mult": 1.0},
        {"label": "GDV -10%", "rate_delta": 0, "rent_delta": 0, "value_mult": 0.9},
        {"label": "Rent -15%", "rate_delta": 0, "rent_delta": -0.15, "value_mult": 1.0},
        {"label": "Worst case", "rate_delta": 0.02, "rent_delta": -0.15, "value_mult": 0.9},
    ]
    results = []
    for s in scenarios:
        r = rent * (1 + s["rent_delta"])
        value = refinance_value * s["value_mult"]
        mortgage = value * (base_rate + s["rate_delta"]) / 12
        mgmt = mgmt_fixed if mgmt_fixed > 0 else (r * mgmt_pct)
        cf = round(r - mortgage - mgmt - maint_monthly - other_opex_monthly, 2)
        results.append({"label": s["label"], "monthly_cashflow": cf, "passes": cf > 0})
    return results


def calculate_brr(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    refurb = _num(inputs, "refurb_cost")
    arv = _num(inputs, "post_refurb_value")
    legal = _num(inputs, "legal_fees") or float(config.get("default_legal_purchase"))
    survey = _num(inputs, "survey_fees") or float(config.get("default_survey_cost"))
    finance = _num(inputs, "finance_costs")
    cont_pct = _num(inputs, "contingency_pct_refurb", 0.10)
    refi_ltv = _num(inputs, "refinance_ltv") or (float(config.get("brr_default_ltv")) / 100)

    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    stamp = financial.stamp_duty_additional_property(purchase) if use_additional else 0.0

    contingency = refurb * cont_pct
    total_cost = purchase + stamp + legal + survey + refurb + finance + contingency
    refinance_value = arv * refi_ltv
    cash_out = refinance_value - total_cost
    cash_left_in = max(0.0, -cash_out)
    capital_recycled_pct = round(min(refinance_value / total_cost * 100, 100), 2) if total_cost > 0 else 0.0
    equity_created = arv - refinance_value
    final_ltv = round((refinance_value / arv) * 100, 4) if arv > 0 else 0.0

    recycle_strong_pct = float(config.get("verdict_brr_recycled_strong_pct"))
    recycle_marginal_pct = float(config.get("verdict_brr_recycled_marginal_pct"))
    min_roi_pct = float(config.get("outcome_min_roi_pct"))
    min_yield_pct = float(config.get("verdict_yield_marginal_pct") or 5)

    capital_recycled_pass = capital_recycled_pct >= recycle_marginal_pct
    capital_recycled_strong = capital_recycled_pct >= recycle_strong_pct

    outputs: dict[str, Any] = {
        "stamp_duty": round(stamp, 2),
        "legal_fees_used": round(legal, 2),
        "survey_fees_used": round(survey, 2),
        "finance_costs_used": round(finance, 2),
        "contingency": round(contingency, 2),
        "contingency_pct_used": round(cont_pct * 100, 2),
        "refinance_ltv_pct_used": round(refi_ltv * 100, 2),
        "total_cost": round(total_cost, 2),
        "refinance_gross": round(refinance_value, 2),
        "cash_out": round(cash_out, 2),
        "cash_left_in": round(cash_left_in, 2),
        "capital_recycled_pct": capital_recycled_pct,
        "equity_created": round(equity_created, 2),
        "final_ltv_pct": final_ltv,
        "capital_recycled_pass": capital_recycled_pass,
        "capital_recycled_strong": capital_recycled_strong,
        "purchase_plus_costs": round(purchase + stamp + legal + survey + finance, 2),
        "refurb_with_contingency": round(refurb + contingency, 2),
    }

    assumptions = [
        "Total cost = purchase + SDLT (additional property when enabled) + legal + survey + refurb + bridging/finance + refurb contingency.",
        f"Refinance gross = post-refurb value x refinance LTV (default {config.get('brr_default_ltv')}%).",
        "Cash left in = max(0, total cost - refinance gross). Capital recycled % = refinance gross / total cost (capped at 100%).",
        f"Capital recycle pass uses platform marginal band (>={recycle_marginal_pct}% recycled).",
    ]

    monthly_rent = inputs.get("monthly_rent")
    monthly_rent = float(monthly_rent) if monthly_rent not in (None, "") else None

    stress_tests = None

    if monthly_rent is not None and monthly_rent >= 0:
        refi_rate = _num(inputs, "refinance_rate_annual") or (float(config.get("brr_default_refinance_rate")) / 100)
        mgmt_pct = _num(inputs, "management_pct") or (float(config.get("brr_default_management_pct")) / 100)
        mgmt_fixed = _num(inputs, "management_fee_monthly")
        mgmt_monthly = mgmt_fixed if mgmt_fixed > 0 else round(monthly_rent * mgmt_pct, 2)

        maint_pct = _num(inputs, "maintenance_pct_rent", 0.05)
        maint_fixed = _num(inputs, "maintenance_monthly")
        maint_monthly = maint_fixed if maint_fixed > 0 else round(monthly_rent * maint_pct, 2)

        insurance = _num(inputs, "insurance_monthly")
        utilities = _num(inputs, "utilities_monthly")
        council_tax = _num(inputs, "council_tax_monthly")
        void_weeks = _num(inputs, "void_weeks_per_year") or float(config.get("brr_default_void_weeks_pa"))

        monthly_mortgage = round(refinance_value * refi_rate / 12, 2) if refinance_value > 0 else 0.0
        monthly_opex = round(mgmt_monthly + maint_monthly + insurance + utilities + council_tax, 2)
        monthly_cashflow = round(monthly_rent - monthly_mortgage - monthly_opex, 2)
        void_cost_annual = round(monthly_rent * (void_weeks / 52) * 12, 2)
        annual_cashflow = round((monthly_cashflow * 12) - void_cost_annual, 2)
        gross_yield_pct = round(monthly_rent * 12 / arv * 100, 2) if arv > 0 else 0.0
        annual_roi_pct = round(annual_cashflow / cash_left_in * 100, 2) if cash_left_in > 0 else None
        operating_cost_ratio_pct = round((monthly_opex / monthly_rent) * 100, 2) if monthly_rent > 0 else 0.0
        net_margin_pct = round((annual_cashflow / (monthly_rent * 12)) * 100, 2) if (monthly_rent * 12) > 0 else 0.0

        maint_is_pct = maint_fixed <= 0
        denom = 1 - (0.0 if mgmt_fixed > 0 else mgmt_pct) - (maint_pct if maint_is_pct else 0.0)
        breakeven_numerator = (
            monthly_mortgage + (mgmt_fixed if mgmt_fixed > 0 else 0.0) + (0.0 if maint_is_pct else maint_monthly)
            + insurance + utilities + council_tax
        )
        breakeven_rent = round(breakeven_numerator / denom, 2) if denom > 0.001 else None

        hold_stacks = monthly_cashflow > 0
        positive_cashflow_pass = hold_stacks
        min_yield_pass = gross_yield_pct >= min_yield_pct
        roi_on_cash_left_pass = cash_left_in <= 0 or (annual_roi_pct is not None and annual_roi_pct >= min_roi_pct)
        deal_stacks = capital_recycled_pass and hold_stacks

        outputs["monthly_rent_used"] = round(monthly_rent, 2)
        outputs["monthly_mortgage"] = monthly_mortgage
        outputs["management_monthly"] = mgmt_monthly
        outputs["maintenance_monthly"] = maint_monthly
        outputs["insurance_monthly"] = round(insurance, 2)
        outputs["utilities_monthly"] = round(utilities, 2)
        outputs["council_tax_monthly"] = round(council_tax, 2)
        outputs["monthly_operating_costs"] = monthly_opex
        outputs["monthly_cashflow"] = monthly_cashflow
        outputs["void_weeks_used"] = void_weeks
        outputs["void_cost_annual"] = void_cost_annual
        outputs["annual_cashflow"] = annual_cashflow
        outputs["gross_yield_pct"] = gross_yield_pct
        outputs["annual_roi_pct"] = annual_roi_pct
        outputs["operating_cost_ratio_pct"] = operating_cost_ratio_pct
        outputs["net_margin_pct"] = net_margin_pct
        outputs["breakeven_rent_monthly"] = breakeven_rent
        outputs["hold_deal_stacks"] = hold_stacks
        outputs["positive_cashflow_pass"] = positive_cashflow_pass
        outputs["min_yield_pass"] = min_yield_pass
        outputs["roi_on_cash_left_pass"] = roi_on_cash_left_pass
        outputs["deal_stacks"] = deal_stacks

        mgmt_label = f"fixed £{mgmt_fixed:,.0f} per month" if mgmt_fixed > 0 else f"{round(mgmt_pct * 100)}% of rent"
        assumptions.append(f"Hold phase: IO mortgage at {round(refi_rate * 100, 2)}% on refinance gross; management {mgmt_label}.")
        assumptions.append("Annual cashflow = (monthly cashflow x 12) minus void cost (rent x void weeks / 52 x 12).")
        assumptions.append("Breakeven rent is the monthly rent needed for zero cashflow after mortgage and opex.")
        assumptions.append("Deal stacks (overall) = capital recycle pass AND positive monthly cashflow.")
        assumptions.append(f"Min gross yield pass uses marginal yield band (>={min_yield_pct}% on ARV).")
        assumptions.append(f"ROI on cash left pass: N/A when fully recycled; otherwise annual cashflow / cash left in >= {min_roi_pct}%.")

        stress_tests = _brr_stress_tests(monthly_rent, refinance_value, refi_rate, mgmt_pct, mgmt_fixed, maint_monthly, insurance + utilities + council_tax)

        growth = hold_projection.resolve_growth_inputs(inputs)
        void_months = void_weeks / 52 * 12
        five_year = hold_projection.project(
            {
                "hold_years": growth["hold_years"],
                "annual_rent_growth_pct": growth["rent_growth"],
                "annual_capital_growth_pct": growth["cap_growth"],
                "property_value": arv,
                "cash_invested": max(1.0, cash_left_in),
                "monthly_rent": monthly_rent,
                "monthly_mortgage": monthly_mortgage,
                "monthly_insurance": insurance,
                "monthly_council_tax": council_tax,
                "monthly_utilities": utilities,
                "monthly_management": mgmt_monthly,
                "monthly_maintenance": maint_monthly,
                "void_months_per_year": void_months,
                "mortgage_balance": refinance_value,
            }
        )
        outputs["hold_years_used"] = five_year["hold_years"]
        outputs["five_year_cumulative_cashflow"] = five_year["cumulative_cashflow"]
        outputs["five_year_equity_gain"] = five_year["equity_gain"]
        outputs["five_year_total_return"] = five_year["total_return"]
        outputs["five_year_total_return_pct"] = five_year["total_return_pct"] if cash_left_in > 0 else None
        outputs["five_year_schedule"] = five_year["schedule"]
        outputs["five_year_rent_growth_pct_used"] = five_year["annual_rent_growth_pct"]
        outputs["five_year_capital_growth_pct_used"] = five_year["annual_capital_growth_pct"]
        assumptions.append(
            f"{five_year['hold_years']}-year hold projection uses ARV as starting value, {five_year['annual_rent_growth_pct']}% rent growth and {five_year['annual_capital_growth_pct']}% capital growth p.a."
        )
        assumptions.append("Total return over hold period = cumulative cashflow + property value uplift (IO debt held at refinance gross).")
    else:
        outputs["deal_stacks"] = capital_recycled_pass
        outputs["hold_deal_stacks"] = None
        assumptions.append("Add monthly rent after refurb to model hold-phase cashflow, stress test, and combined deal stacks.")

    return {"outputs": outputs, "assumptions": assumptions, "stress_tests": stress_tests}


# --------------------------------------------------------- strategy_finder
STRATEGY_FINDER_RULES: Rules = {
    "capital_bucket": ["required", "in:under_5k,5k_to_25k,25_to_50k,50_to_100k,100_to_250k,over_250k"],
    "primary_goal": ["required", "in:passive_income,capital_growth,both,build_quickly"],
    "weekly_hours": ["required", "in:under_2,2_to_5,5_to_15,over_15"],
    "risk_tolerance": ["required", "in:low,medium,high"],
    "pro_skills": ["required", "in:none,finance,trades,sales,property,tech"],
}


def calculate_strategy_finder(inputs: dict, config: ConfigResolver) -> CalcResult:
    result = strategy_finder_engine.run(inputs)
    scores = result["strategy_scores"]
    top = result["top_strategy"]
    top_score = int(scores.get(top, 0))
    feasibility = result["feasibility"]
    can_start = bool(feasibility.get("can_start_top_today") or False)
    top_proj = result["projections"].get(top) or {}

    ranked = sorted(({"strategy": slug, "score": s} for slug, s in scores.items()), key=lambda r: r["score"], reverse=True)

    return {
        "outputs": {
            "top_strategy": top,
            "top_strategy_score": top_score,
            "top_three": result["top_three"],
            "strategy_scores": scores,
            "typical_monthly_income": top_proj.get("typical_monthly_income"),
            "typical_setup_capital": top_proj.get("typical_deposit_or_capital"),
            "typical_months_to_income": top_proj.get("typical_months_to_first_income"),
            "can_start_top_strategy": can_start,
            "capital_gap": feasibility.get("capital_gap"),
            "bridge_strategy": feasibility.get("bridge_strategy"),
            "deal_stacks": can_start,
            "ranked_strategies": ranked,
        },
        "assumptions": [
            "Scores combine capital, goal, weekly time, risk tolerance, and professional skills (max 100 per strategy).",
            "Top three strategies are the highest total scores; projections use illustrative UK deal templates for your capital band.",
            "Feasibility compares your capital band midpoint to typical entry cost for the top strategy.",
        ],
        "detail": {
            "projections": result["projections"],
            "skill_insight": result["skill_insight"],
            "feasibility": feasibility,
        },
    }


# --------------------------------------------------------- commercial -----
COMMERCIAL_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "passing_rent_annual": ["nullable", "numeric", "min:0"],
    "monthly_rent": ["nullable", "numeric", "min:0"],
    "erv_annual": ["nullable", "numeric", "min:0"],
    "erv_monthly": ["nullable", "numeric", "min:0"],
    "vacancy_status": ["nullable", "string", "in:fully_let,partially_let,vacant"],
    "target_yield_pct": ["nullable", "numeric", "min:0.1", "max:25"],
}


def calculate_commercial(inputs: dict, config: ConfigResolver) -> CalcResult:
    if (
        "passing_rent_annual" not in inputs
        and "monthly_rent" not in inputs
        and not inputs.get("leases")
        and "vacancy_status" not in inputs
    ):
        inputs = dict(inputs)
        inputs["monthly_rent"] = 0
    result = commercial_engine.calculate(inputs)
    monthly = float(result["outputs"].get("net_monthly_cash") or 0)
    result["outputs"]["deal_stacks"] = monthly > 0
    return result


# -------------------------------------------------------------- development
DEVELOPMENT_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "build_cost_per_unit": ["required", "numeric", "min:1"],
    "unit_count": ["required", "integer", "min:1", "max:200"],
    "average_unit_value": ["required", "numeric", "min:1"],
    "average_monthly_rent": ["required", "numeric", "min:0"],
    "professional_fees": ["required", "numeric", "min:0"],
    "project_months": ["required", "integer", "min:3", "max:60"],
    "finance_rate_monthly": ["nullable", "numeric", "min:0.001", "max:0.03"],
    "exit_preference": ["required", "in:sell,hold,both"],
    "supported_housing_exit": ["nullable", "boolean"],
    "supported_housing_monthly_rent": ["nullable", "numeric", "min:0"],
    "supported_housing_lease_years": ["nullable", "integer", "min:5", "max:25"],
}


def calculate_development(inputs: dict, config: ConfigResolver) -> CalcResult:
    result = development_engine.calculate(inputs)
    return {
        "outputs": {
            "gdv_total": float(result["gdv"]["total"]),
            "gross_dev_costs": float(result["costs"]["gross_dev_costs"]),
            "total_project_cost": float(result["costs"]["total_project_cost"]),
            "development_loan": float(result["finance"]["development_loan"]),
            "equity_required": float(result["finance"]["equity_required"]),
            "sell_profit": float(result["exit_sell"]["profit"]),
            "sell_margin_pct": float(result["exit_sell"]["margin_pct"]),
            "sell_cash_on_cash_pct": float(result["exit_sell"]["cash_on_cash_pct"]),
            "hold_monthly_net_cashflow": float(result["exit_hold"]["monthly_net_cashflow"]),
            "hold_gross_yield_pct": float(result["exit_hold"]["gross_yield_pct"]),
            "is_viable": bool(result["viability"]["is_viable"]),
            "is_target": bool(result["viability"]["is_target"]),
            "deal_stacks": bool(result["viability"]["is_viable"]),
        },
        "assumptions": [
            "Max LTC 80%, max LTV on GDV 65%, 15% construction contingency.",
            "Development finance interest on 60% average draw over project term.",
            "Sell exit: 1.5% agent fee. Hold exit: refinance at 70% LTV, 5.5% stressed IO.",
        ],
        "detail": result,
    }


# ---------------------------------------------------------------- sa_vs_btl
SA_VS_BTL_SLUG = "sa_vs_btl"
SA_VS_BTL_RULES: Rules = {
    "purchase_price": ["required", "numeric", "min:1"],
    "monthly_rent": ["required", "numeric", "min:0"],
    "nightly_rate": ["required", "numeric", "min:0"],
    "occupancy_pct": ["required", "numeric", "min:0", "max:100"],
}


def _monthly_mortgage_payment(principal: float, annual_rate: float, term_years: int, interest_only: bool) -> float:
    if principal <= 0:
        return 0.0
    result = calculate_mortgage(
        {"loan_amount": principal, "annual_interest_rate": annual_rate, "term_years": term_years, "interest_only": interest_only},
        ConfigResolver(),
    )
    return float(result["outputs"].get("monthly_payment") or 0)


def _sa_vs_btl_calc_btl(inputs, purchase, total_acquisition, btl_refurb, mortgage, monthly_mortgage):
    monthly_rent = _num(inputs, "monthly_rent")
    void_pct = _num(inputs, "btl_void_rate_pct", 5) / 100
    mgmt_type = str(inputs.get("btl_management_fee_type") or "percent")
    mgmt_pct = _num(inputs, "btl_management_fee_percent", 10) / 100
    mgmt_fixed = _num(inputs, "btl_management_fee_fixed")
    maint_monthly = _num(inputs, "btl_monthly_maintenance", 50)
    insurance = _num(inputs, "btl_annual_insurance", 400)

    gross_annual = monthly_rent * 12 * (1 - void_pct)
    annual_mortgage = monthly_mortgage * 12
    annual_management = mgmt_fixed * 12 if mgmt_type == "fixed" else gross_annual * mgmt_pct
    annual_maintenance = maint_monthly * 12
    annual_costs = annual_mortgage + annual_management + annual_maintenance + insurance
    net_annual = gross_annual - annual_costs
    equity = max(1.0, (purchase - mortgage) + (total_acquisition - purchase) + btl_refurb)

    gross_yield = (gross_annual / purchase) * 100 if purchase > 0 else 0.0
    roi = financial.roi_percent(net_annual, equity) or 0.0

    return {
        "total_acquisition_cost": round(total_acquisition + btl_refurb, 2),
        "equity_deployed": round(equity, 2),
        "gross_annual_income": round(gross_annual, 2),
        "gross_yield_pct": round(gross_yield, 4),
        "net_annual_income": round(net_annual, 2),
        "net_monthly_cash": round(net_annual / 12, 2),
        "net_roi_pct": round(roi, 4),
        "annual_costs": round(annual_costs, 2),
    }


def _sa_vs_btl_calc_sa(inputs, purchase, total_acquisition, sa_fitout, mortgage, monthly_mortgage):
    nightly = _num(inputs, "nightly_rate")
    occ = _num(inputs, "occupancy_pct") / 100
    platform_pct = _num(inputs, "platform_commission_pct", 3) / 100
    mgmt_pct = _num(inputs, "sa_management_fee_pct") / 100
    clean_per_stay = _num(inputs, "cleaning_cost_per_stay", 45)
    stay_nights = max(0.5, _num(inputs, "avg_stay_length_nights", 2))
    channel_monthly = _num(inputs, "channel_manager_monthly")
    dynamic_monthly = _num(inputs, "dynamic_pricing_monthly")
    maint_monthly = _num(inputs, "sa_monthly_maintenance", 75)
    insurance = _num(inputs, "sa_annual_insurance", 500)

    occupied_nights = 365 * occ
    gross_annual = nightly * occupied_nights
    platform_fee = gross_annual * platform_pct
    stays = occupied_nights / stay_nights
    cleaning = stays * clean_per_stay
    mgmt_fee = gross_annual * mgmt_pct
    annual_mortgage = monthly_mortgage * 12
    annual_costs = (
        platform_fee + cleaning + mgmt_fee + (channel_monthly * 12) + (dynamic_monthly * 12)
        + (maint_monthly * 12) + insurance + annual_mortgage
    )
    net_annual = gross_annual - annual_costs
    equity = max(1.0, (purchase - mortgage) + (total_acquisition - purchase) + sa_fitout)

    gross_yield = (gross_annual / purchase) * 100 if purchase > 0 else 0.0
    roi = financial.roi_percent(net_annual, equity) or 0.0

    return {
        "total_acquisition_cost": round(total_acquisition + sa_fitout, 2),
        "equity_deployed": round(equity, 2),
        "gross_annual_income": round(gross_annual, 2),
        "gross_yield_pct": round(gross_yield, 4),
        "net_annual_income": round(net_annual, 2),
        "net_monthly_cash": round(net_annual / 12, 2),
        "net_roi_pct": round(roi, 4),
        "annual_costs": round(annual_costs, 2),
    }


def _sa_vs_btl_summary(annual_cash_delta, fitout_premium, payback_months, better_model) -> str:
    abs_delta = abs(annual_cash_delta)
    delta_formatted = f"£{abs_delta:,.0f}"

    if better_model == "tie":
        return "On these assumptions, BTL and SA produce similar net ROI. Adjust occupancy, nightly rate, or costs to see a clearer winner."

    lead = (
        f"On this property, SA generates {delta_formatted} more per year than BTL"
        if better_model == "sa"
        else f"On this property, BTL generates {delta_formatted} more per year than SA"
    )

    if fitout_premium > 0 and payback_months is not None:
        return f"{lead}, requiring £{fitout_premium:,.0f} more upfront in fit-out costs, recovering the premium in {payback_months} months."
    if fitout_premium > 0:
        return f"{lead}, with £{fitout_premium:,.0f} additional upfront fit-out for SA."
    return f"{lead}."


def calculate_sa_vs_btl(inputs: dict, config: ConfigResolver) -> CalcResult:
    purchase = _num(inputs, "purchase_price")
    legal = _num(inputs, "legal_purchase_costs")
    mortgage = _num(inputs, "mortgage_amount")
    rate_pct = _num(inputs, "mortgage_rate_pct", 5.5)
    term_years = round(_num(inputs, "mortgage_term_years", 25))
    interest_only = inputs.get("interest_only")
    interest_only = True if interest_only is None else bool(interest_only)

    use_additional = inputs.get("use_additional_sdlt")
    use_additional = True if use_additional is None else bool(use_additional)
    stamp = (
        _num(inputs, "stamp_duty")
        if inputs.get("stamp_duty") not in (None, "")
        else (financial.stamp_duty_additional_property(purchase) if use_additional else 0.0)
    )

    monthly_mortgage = _monthly_mortgage_payment(mortgage, rate_pct / 100, term_years, interest_only)
    total_acquisition = purchase + stamp + legal

    btl_refurb = _num(inputs, "btl_refurb_cost")
    sa_fitout = _num(inputs, "sa_fitout_cost")

    btl = _sa_vs_btl_calc_btl(inputs, purchase, total_acquisition, btl_refurb, mortgage, monthly_mortgage)
    sa = _sa_vs_btl_calc_sa(inputs, purchase, total_acquisition, sa_fitout, mortgage, monthly_mortgage)

    annual_cash_delta = round(sa["net_annual_income"] - btl["net_annual_income"], 2)
    fitout_premium = max(0.0, sa_fitout - btl_refurb)
    monthly_extra = annual_cash_delta / 12
    payback_months = int(-(-fitout_premium // monthly_extra)) if (fitout_premium > 0 and monthly_extra > 0) else None
    sa["payback_months_on_fitout_premium"] = payback_months

    if sa["net_roi_pct"] > btl["net_roi_pct"]:
        better_model = "sa"
    elif btl["net_roi_pct"] > sa["net_roi_pct"]:
        better_model = "btl"
    else:
        better_model = "tie"

    summary = _sa_vs_btl_summary(annual_cash_delta, fitout_premium, payback_months, better_model)

    return {
        "shared": {
            "total_acquisition_cost": round(total_acquisition, 2),
            "monthly_mortgage_payment": round(monthly_mortgage, 2),
            "stamp_duty_computed": round(stamp, 2),
        },
        "btl": btl,
        "sa": sa,
        "comparison": {
            "better_roi_model": better_model,
            "annual_cash_delta": annual_cash_delta,
            "monthly_cash_delta": round(annual_cash_delta / 12, 2),
            "fitout_premium": round(fitout_premium, 2),
            "payback_months_on_fitout_premium": payback_months,
            "summary": summary,
        },
        "assumptions": [
            "ROI = net annual profit / equity deployed x 100. Equity = purchase + acquisition costs + fit-out - mortgage.",
            "BTL gross income applies void rate to annual rent. SA gross = nightly rate x (365 x occupancy).",
            "SA cleaning stays = occupied nights / average stay length (minimum 0.5 nights to avoid division by zero).",
            "Mortgage: interest-only when toggled; otherwise standard repayment amortisation.",
        ],
    }
