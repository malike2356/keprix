"""Port of HoldProjectionService.php - year-by-year hold projection (default
5 years) shared by BTL and BRR's hold phase."""

from __future__ import annotations

from typing import Any


def resolve_growth_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    years = int(inputs.get("hold_years") or 5)
    rent_growth_raw = inputs.get("annual_rent_growth_pct")
    if rent_growth_raw is None:
        rent_growth = 0.02
    else:
        rent_growth = float(rent_growth_raw)
        if rent_growth > 1:
            rent_growth /= 100
    cap_growth_raw = inputs.get("annual_capital_growth_pct")
    if cap_growth_raw is None:
        cap_growth = 0.02
    else:
        cap_growth = float(cap_growth_raw)
        if cap_growth > 1:
            cap_growth /= 100

    return {
        "hold_years": max(1, min(30, years)),
        "rent_growth": rent_growth,
        "cap_growth": cap_growth,
    }


def project(params: dict[str, Any]) -> dict[str, Any]:
    years = max(1, min(30, int(params.get("hold_years") or 5)))
    rent_growth = float(params.get("annual_rent_growth_pct") if params.get("annual_rent_growth_pct") is not None else 0.02)
    cap_growth = float(params.get("annual_capital_growth_pct") if params.get("annual_capital_growth_pct") is not None else 0.02)
    value0 = max(0.0, float(params["property_value"]))
    cash_in = max(0.0, float(params["cash_invested"]))
    void_months = float(params.get("void_months_per_year") if params.get("void_months_per_year") is not None else 1)

    mortgage_annual = float(params["monthly_mortgage"]) * 12
    insurance_annual = float(params["monthly_insurance"]) * 12
    council_annual = float(params["monthly_council_tax"]) * 12
    utilities_annual = float(params["monthly_utilities"]) * 12

    schedule: list[dict[str, Any]] = []
    cumulative = 0.0
    cash_flows_for_npv = [-round(cash_in, 2)]

    for y in range(1, years + 1):
        rent_factor = (1 + rent_growth) ** (y - 1)
        value_factor = (1 + cap_growth) ** y

        monthly_rent = float(params["monthly_rent"]) * rent_factor
        gross_rent_annual = round(monthly_rent * 12, 2)

        mgmt_annual = round(float(params["monthly_management"]) * 12 * rent_factor, 2)
        maint_annual = round(float(params["monthly_maintenance"]) * 12, 2)
        void_annual = round(monthly_rent * void_months, 2)

        opex_annual = round(
            mgmt_annual + maint_annual + insurance_annual + council_annual + utilities_annual + void_annual, 2
        )

        net = round(gross_rent_annual - opex_annual - mortgage_annual, 2)
        property_value = round(value0 * value_factor, 2)
        loan_balance = max(0.0, float(params.get("mortgage_balance") or 0))
        equity = round(max(0.0, property_value - loan_balance), 2)

        schedule.append(
            {
                "year": y,
                "gross_rent_annual": gross_rent_annual,
                "operating_costs_annual": opex_annual,
                "mortgage_annual": round(mortgage_annual, 2),
                "void_cost_annual": void_annual,
                "net_cashflow_annual": net,
                "property_value": property_value,
                "equity": equity,
            }
        )

        cumulative += net
        cash_flows_for_npv.append(net)

    value_end = schedule[-1]["property_value"] if schedule else value0
    equity_gain = round(value_end - value0, 2)
    total_return = round(cumulative + equity_gain, 2)
    total_return_pct = round(total_return / cash_in * 100, 2) if cash_in > 0 else None

    return {
        "hold_years": years,
        "annual_rent_growth_pct": round(rent_growth * 100, 2),
        "annual_capital_growth_pct": round(cap_growth * 100, 2),
        "schedule": schedule,
        "cumulative_cashflow": round(cumulative, 2),
        "equity_gain": equity_gain,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
        "cash_flows_for_npv": cash_flows_for_npv,
    }
