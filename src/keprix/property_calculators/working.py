"""Show working: step-by-step arithmetic breakdown alongside a calculator's
outputs, matching the CalculatorWorkingStep contract real Propreneur ships
(propreneur/app/Services/Deals/CalculatorWorking/CalculatorWorkingStep.php)
- key/display_name/formula/value/unit/variables/steps/plain_summary -
minus the xelox_slug citation field, which pointed at Propreneur's own
branded help content and has no aiva2 equivalent yet (dropped deliberately,
matching this codebase's established brand-masking discipline rather than
leaking a foreign product's URL into Aiva's UI).

This is a real, additive layer beyond prompt 154's own written acceptance
criteria (which only requires `assumptions`, already populated for all 28
calculators in calculators.py) - covers the most commonly used strategies
first; a calculator with no builder here simply returns an empty `working`
list, which the frontend renders as "step-by-step working not yet
available for this calculator" rather than fabricating one.
"""

from __future__ import annotations

from typing import Any, Callable

WorkingBuilder = Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]


def _money(value: float | None) -> str:
    if value is None:
        return "£0"
    sign = "-" if value < 0 else ""
    return f"{sign}£{abs(value):,.0f}"


def _pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "0%"
    return f"{value:,.{decimals}f}%"


def _step(key: str, display_name: str, formula: str, value: str, unit: str, variables: list[dict[str, str]], steps: list[str], plain_summary: str = "") -> dict[str, Any]:
    return {
        "key": key,
        "display_name": display_name,
        "formula": formula,
        "value": value,
        "unit": unit,
        "variables": variables,
        "steps": steps,
        "plain_summary": plain_summary,
    }


def _build_btl(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    purchase = float(inputs.get("purchase_price") or 0)
    rent = float(inputs.get("monthly_rent") or 0)
    annual_rent = rent * 12
    gross_yield = outputs.get("gross_yield_pct")

    steps = [
        _step(
            "gross_yield_pct",
            "Gross yield",
            "(monthly rent x 12) / purchase price x 100",
            _pct(gross_yield),
            "%",
            [
                {"name": "Monthly rent", "value": _money(rent), "description": "Rent you enter"},
                {"name": "Purchase price", "value": _money(purchase), "description": "Purchase price you enter"},
            ],
            [
                f"Annual rent = {_money(rent)} x 12 = {_money(annual_rent)}",
                f"Gross yield = {_money(annual_rent)} / {_money(purchase)} x 100 = {_pct(gross_yield)}",
            ],
            "How much rent this property generates per year, as a percentage of what it cost - before any costs.",
        ),
        _step(
            "monthly_cashflow",
            "Monthly cashflow",
            "rent - mortgage - insurance - council tax - utilities - management - maintenance - void allowance",
            _money(outputs.get("monthly_cashflow")),
            "£",
            [{"name": "Monthly rent", "value": _money(rent), "description": "Rent you enter"}],
            [
                "Every monthly cost line (mortgage, insurance, council tax, utilities, management, maintenance, void) is subtracted from rent.",
                f"Result: {_money(outputs.get('monthly_cashflow'))} left over each month.",
            ],
            "What's actually left in your pocket each month after every cost.",
        ),
        _step(
            "roi_pct",
            "ROI",
            "(annual cashflow / total investment) x 100",
            _pct(outputs.get("roi_pct")),
            "%",
            [
                {"name": "Annual cashflow", "value": _money(outputs.get("annual_cashflow")), "description": "Monthly cashflow x 12"},
                {"name": "Total investment", "value": _money(outputs.get("total_investment")), "description": "Deposit + SDLT + legal + survey + refurb"},
            ],
            [
                f"Annual cashflow = {_money(outputs.get('monthly_cashflow'))} x 12 = {_money(outputs.get('annual_cashflow'))}",
                f"ROI = {_money(outputs.get('annual_cashflow'))} / {_money(outputs.get('total_investment'))} x 100 = {_pct(outputs.get('roi_pct'))}",
            ],
            "The annual return on the actual cash you put in, not the full purchase price.",
        ),
    ]
    return steps


def _build_sdlt(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    from keprix.property_calculators.constants import (
        SDLT_RESIDENTIAL_ADDITIONAL,
        SDLT_RESIDENTIAL_STANDARD,
    )

    price = float(inputs.get("purchase_price") or 0)
    profile = str(inputs.get("profile") or "additional_property")
    bands = SDLT_RESIDENTIAL_ADDITIONAL if profile == "additional_property" else SDLT_RESIDENTIAL_STANDARD

    lines = []
    previous_cap = 0.0
    for band in bands:
        cap = band["up_to"]
        rate = band["rate"]
        upper = price if cap is None else min(price, float(cap))
        if price <= previous_cap:
            break
        taxable = upper - previous_cap
        if taxable > 0:
            lines.append(f"£{previous_cap:,.0f} to £{upper:,.0f}: £{taxable:,.0f} at {rate * 100:.0f}% = £{taxable * rate:,.2f}")
        if cap is None or price <= upper:
            break
        previous_cap = upper

    return [
        _step(
            "sdlt_total",
            "SDLT total",
            "sum of each price band's slice at its own rate",
            _money(outputs.get("sdlt_total")),
            "£",
            [{"name": "Purchase price", "value": _money(price), "description": "Purchase price you enter"}, {"name": "Profile", "value": profile, "description": "Which SDLT band table applies"}],
            lines or ["No SDLT due at this price."],
            "SDLT is charged in slices, like income tax - each band of the price is taxed at its own rate, not the whole price at the top rate.",
        )
    ]


def _build_mortgage(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    principal = float(inputs.get("loan_amount") or 0)
    annual = float(inputs.get("annual_interest_rate") or 0)
    interest_only = bool(outputs.get("interest_only"))
    monthly = outputs.get("monthly_payment")

    if interest_only:
        steps = [f"Monthly rate = {annual * 100:.3f}% / 12 = {(annual / 12) * 100:.4f}%", f"Monthly payment = {_money(principal)} x {(annual / 12) * 100:.4f}% = {_money(monthly)}"]
        formula = "loan x (annual rate / 12)"
    else:
        steps = [
            f"Monthly rate r = {annual * 100:.3f}% / 12 = {(annual / 12) * 100:.4f}%",
            "Payment = loan x (r x (1+r)^n) / ((1+r)^n - 1), n = term in months",
            f"Result: {_money(monthly)} per month",
        ]
        formula = "standard amortisation: loan x (r(1+r)^n) / ((1+r)^n - 1)"

    return [
        _step(
            "monthly_payment",
            "Monthly payment",
            formula,
            _money(monthly),
            "£",
            [{"name": "Loan amount", "value": _money(principal), "description": "Amount borrowed"}, {"name": "Annual rate", "value": _pct(annual * 100), "description": "Annual interest rate"}],
            steps,
            "Interest-only pays only the interest each month; repayment pays down some capital too, so it's a bigger monthly amount.",
        )
    ]


def _build_bridging(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    loan = float(inputs.get("loan_amount") or 0)
    rate = float(inputs.get("annual_interest_rate") or 0)
    months = float(inputs.get("term_months") or 0)

    return [
        _step(
            "total_financing_cost",
            "Total financing cost",
            "interest + arrangement fee + exit fee + broker fee",
            _money(outputs.get("total_financing_cost")),
            "£",
            [
                {"name": "Loan amount", "value": _money(loan), "description": "Bridging loan amount"},
                {"name": "Term", "value": f"{months:.0f} months", "description": "Loan term"},
            ],
            [
                f"Interest = {_money(loan)} x {rate * 100:.2f}% x ({months:.0f}/12) = {_money(outputs.get('interest_cost'))}",
                f"Fees = arrangement {_money(outputs.get('arrangement_fees_total'))} + other {_money(outputs.get('other_fees_total'))}",
                f"Total = {_money(outputs.get('interest_cost'))} + {_money(outputs.get('arrangement_fees_total'))} + {_money(outputs.get('other_fees_total'))} = {_money(outputs.get('total_financing_cost'))}",
            ],
            "Bridging interest here is simple (not compounded/rolled-up) - loan x rate x time, plus the one-off fees.",
        )
    ]


def _build_ltv(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    loan = float(inputs.get("loan_amount") or 0)
    value = float(inputs.get("property_value") or 0)
    return [
        _step(
            "ltv_pct",
            "Loan-to-value",
            "(loan amount / property value) x 100",
            _pct(outputs.get("ltv_pct")),
            "%",
            [{"name": "Loan amount", "value": _money(loan), "description": ""}, {"name": "Property value", "value": _money(value), "description": ""}],
            [f"LTV = {_money(loan)} / {_money(value)} x 100 = {_pct(outputs.get('ltv_pct'))}"],
            "How much of the property's value is borrowed - lower LTV usually means better mortgage rates.",
        )
    ]


def _build_dscr(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    noi = float(inputs.get("annual_noi") or 0)
    debt = float(inputs.get("annual_debt_service") or 0)
    return [
        _step(
            "dscr",
            "DSCR",
            "annual NOI / annual debt service",
            f"{outputs.get('dscr'):.2f}x" if outputs.get("dscr") is not None else "-",
            "x",
            [{"name": "Annual NOI", "value": _money(noi), "description": "Net operating income"}, {"name": "Annual debt service", "value": _money(debt), "description": "Total loan repayments"}],
            [f"DSCR = {_money(noi)} / {_money(debt)} = {outputs.get('dscr'):.4f}x"],
            "How many times over the rental income covers the loan repayments - lenders typically want at least 1.25x.",
        )
    ]


def _build_rental_yield(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    price = float(inputs.get("purchase_price") or 0)
    rent = float(inputs.get("monthly_rent") or 0)
    return [
        _step(
            "gross_yield_pct",
            "Gross yield",
            "(monthly rent x 12) / purchase price x 100",
            _pct(outputs.get("gross_yield_pct")),
            "%",
            [{"name": "Monthly rent", "value": _money(rent), "description": ""}, {"name": "Purchase price", "value": _money(price), "description": ""}],
            [f"Annual rent = {_money(rent)} x 12 = {_money(rent * 12)}", f"Gross yield = {_money(rent * 12)} / {_money(price)} x 100 = {_pct(outputs.get('gross_yield_pct'))}"],
            "",
        ),
        _step(
            "net_yield_pct",
            "Net yield",
            "(effective rent after void - annual expenses) / purchase price x 100",
            _pct(outputs.get("net_yield_pct")),
            "%",
            [{"name": "Effective rent", "value": _money(outputs.get("effective_rent_annual")), "description": "Annual rent minus void cost"}, {"name": "Expenses", "value": _money(outputs.get("annual_expenses_total")), "description": ""}],
            [f"Net income = {_money(outputs.get('effective_rent_annual'))} - {_money(outputs.get('annual_expenses_total'))} = {_money(outputs.get('annual_net_income'))}", f"Net yield = {_money(outputs.get('annual_net_income'))} / {_money(price)} x 100 = {_pct(outputs.get('net_yield_pct'))}"],
            "",
        ),
    ]


def _build_hmo(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    rooms = int(inputs.get("rooms") or 0)
    rpm = float(inputs.get("rent_per_room_monthly") or 0)
    return [
        _step(
            "gross_monthly_rent",
            "Gross monthly rent",
            "rent per room x number of rooms",
            _money(outputs.get("gross_monthly_rent")),
            "£",
            [{"name": "Rent per room", "value": _money(rpm), "description": ""}, {"name": "Rooms", "value": str(rooms), "description": ""}],
            [f"{_money(rpm)} x {rooms} rooms = {_money(outputs.get('gross_monthly_rent'))}"],
            "",
        ),
        _step(
            "monthly_cashflow",
            "Monthly cashflow",
            "NOI/12 - monthly mortgage",
            _money(outputs.get("monthly_cashflow")),
            "£",
            [{"name": "NOI", "value": _money(outputs.get("noi_annual")), "description": "Gross rent minus all operating costs"}],
            [f"Monthly NOI = {_money(outputs.get('noi_annual'))} / 12 = {_money(outputs.get('monthly_noi'))}", f"Monthly cashflow = {_money(outputs.get('monthly_noi'))} - {_money(outputs.get('annual_mortgage', 0) / 12)} = {_money(outputs.get('monthly_cashflow'))}"],
            "",
        ),
    ]


def _build_r2r(inputs: dict, outputs: dict) -> list[dict[str, Any]]:
    head_rent = float(inputs.get("rent_to_landlord_monthly") or 0)
    return [
        _step(
            "monthly_profit",
            "Monthly profit",
            "(subtenant rent - head rent) - operating costs",
            _money(outputs.get("monthly_profit")),
            "£",
            [{"name": "Head rent (to landlord)", "value": _money(head_rent), "description": ""}, {"name": "Operating costs", "value": _money(outputs.get("monthly_operating_costs")), "description": ""}],
            [
                f"Gross margin = subtenant rent - {_money(head_rent)} = {_money(outputs.get('rent_difference_monthly'))}",
                f"Monthly profit = {_money(outputs.get('rent_difference_monthly'))} - {_money(outputs.get('monthly_operating_costs'))} = {_money(outputs.get('monthly_profit'))}",
            ],
            "The margin between what subtenants pay you and what you pay the landlord, minus your running costs.",
        )
    ]


_BUILDERS: dict[str, WorkingBuilder] = {
    "btl": _build_btl,
    "sdlt": _build_sdlt,
    "mortgage": _build_mortgage,
    "bridging": _build_bridging,
    "ltv": _build_ltv,
    "dscr": _build_dscr,
    "rental_yield": _build_rental_yield,
    "hmo": _build_hmo,
    "r2r": _build_r2r,
}


def build_working(strategy: str, inputs: dict[str, Any], outputs: dict[str, Any]) -> list[dict[str, Any]]:
    builder = _BUILDERS.get(strategy)
    if builder is None:
        return []
    return builder(inputs, outputs)


def supported_strategies() -> list[str]:
    return list(_BUILDERS.keys())
