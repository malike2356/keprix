"""Port of DevelopmentCalculatorService.php - small-scale
commercial-to-residential development underwriting (GDV, GDC, development
finance, sell vs hold vs supported-housing exit)."""

from __future__ import annotations

from typing import Any

MAX_LTC = 0.80
MAX_LTV_GDV = 0.65
MIN_VIABLE_MARGIN = 0.20
TARGET_MARGIN = 0.25
CONTINGENCY_RATE = 0.15
ARRANGEMENT_FEE_RATE = 0.02
SALES_AGENT_RATE = 0.015


def calculate(inputs: dict[str, Any]) -> dict[str, Any]:
    purchase_price = float(inputs.get("purchase_price") or 0)
    build_cost_per_unit = float(inputs.get("build_cost_per_unit") or 0)
    unit_count = int(inputs.get("unit_count") or 0)
    avg_unit_value = float(inputs.get("average_unit_value") or 0)
    avg_monthly_rent = float(inputs.get("average_monthly_rent") or 0)
    professional_fees = float(inputs.get("professional_fees") or 0)
    project_months = int(inputs.get("project_months") or 12)
    finance_rate = float(inputs.get("finance_rate_monthly") or 0.0105)
    supported_housing = bool(inputs.get("supported_housing_exit") or False)
    supported_housing_rent = float(inputs.get("supported_housing_monthly_rent") or 0)
    supported_housing_years = int(inputs.get("supported_housing_lease_years") or 15)

    gdv = avg_unit_value * unit_count

    construction_costs = build_cost_per_unit * unit_count
    contingency = construction_costs * CONTINGENCY_RATE
    gross_dev_costs = purchase_price + construction_costs + contingency + professional_fees

    max_by_ltc = gross_dev_costs * MAX_LTC
    max_by_gdv = gdv * MAX_LTV_GDV
    development_loan = min(max_by_ltc, max_by_gdv)
    equity_required = gross_dev_costs - development_loan
    arrangement_fee = development_loan * ARRANGEMENT_FEE_RATE

    average_drawdown = development_loan * 0.60
    finance_interest = average_drawdown * finance_rate * project_months

    total_project_costs = gross_dev_costs + arrangement_fee + finance_interest

    sales_costs = gdv * SALES_AGENT_RATE
    sell_profit = gdv - total_project_costs - sales_costs
    sell_margin_pct = (sell_profit / gdv) * 100 if gdv > 0 else 0
    sell_cash_on_cash = (sell_profit / equity_required) * 100 if equity_required > 0 else 0

    refinance_ltv = 0.70
    refinance_loan = gdv * refinance_ltv
    debt_repaid = development_loan + arrangement_fee + finance_interest
    cash_retained = refinance_loan - debt_repaid
    gross_annual_rent = avg_monthly_rent * unit_count * 12
    annual_mortgage_cost = refinance_loan * 0.055
    net_annual_income = gross_annual_rent * 0.80
    hold_monthly_net_cashflow = (net_annual_income - annual_mortgage_cost) / 12
    hold_gross_yield = (gross_annual_rent / gdv) * 100 if gdv > 0 else 0

    supported_housing_result = None
    if supported_housing and supported_housing_rent > 0:
        annual_sh_rent = supported_housing_rent * unit_count * 12
        total_sh_income = annual_sh_rent * supported_housing_years
        sh_net_annual_income = annual_sh_rent * 0.85
        sh_monthly_net_cashflow = (sh_net_annual_income - annual_mortgage_cost) / 12
        supported_housing_result = {
            "monthly_rent_per_unit": supported_housing_rent,
            "total_annual_rent": round(annual_sh_rent, 2),
            "lease_years": supported_housing_years,
            "total_contracted_income": round(total_sh_income, 2),
            "monthly_net_cashflow": round(sh_monthly_net_cashflow, 2),
            "annual_net_cashflow": round(sh_net_annual_income - annual_mortgage_cost, 2),
        }

    is_viable = sell_margin_pct >= (MIN_VIABLE_MARGIN * 100)
    is_target = sell_margin_pct >= (TARGET_MARGIN * 100)

    return {
        "gdv": {"total": round(gdv, 2), "per_unit": round(avg_unit_value, 2), "unit_count": unit_count},
        "costs": {
            "purchase_price": round(purchase_price, 2),
            "construction": round(construction_costs, 2),
            "contingency": round(contingency, 2),
            "professional_fees": round(professional_fees, 2),
            "gross_dev_costs": round(gross_dev_costs, 2),
            "arrangement_fee": round(arrangement_fee, 2),
            "finance_interest": round(finance_interest, 2),
            "total_project_cost": round(total_project_costs, 2),
        },
        "finance": {
            "development_loan": round(development_loan, 2),
            "equity_required": round(equity_required, 2),
            "max_by_ltc": round(max_by_ltc, 2),
            "max_by_gdv": round(max_by_gdv, 2),
            "monthly_rate_pct": round(finance_rate * 100, 3),
            "annual_rate_pct": round(finance_rate * 1200, 2),
            "project_months": project_months,
        },
        "exit_sell": {
            "sale_price": round(gdv, 2),
            "sales_costs": round(sales_costs, 2),
            "profit": round(sell_profit, 2),
            "margin_pct": round(sell_margin_pct, 1),
            "cash_on_cash_pct": round(sell_cash_on_cash, 1),
            "is_viable": is_viable,
            "is_target": is_target,
        },
        "exit_hold": {
            "refinance_loan": round(refinance_loan, 2),
            "cash_retained_after_refi": round(cash_retained, 2),
            "gross_annual_rent": round(gross_annual_rent, 2),
            "annual_mortgage_cost": round(annual_mortgage_cost, 2),
            "monthly_net_cashflow": round(hold_monthly_net_cashflow, 2),
            "annual_net_cashflow": round(net_annual_income - annual_mortgage_cost, 2),
            "gross_yield_pct": round(hold_gross_yield, 2),
        },
        "exit_supported_housing": supported_housing_result,
        "viability": {
            "is_viable": is_viable,
            "is_target": is_target,
            "margin_pct": round(sell_margin_pct, 1),
            "min_margin": round(MIN_VIABLE_MARGIN * 100, 0),
            "target_margin": round(TARGET_MARGIN * 100, 0),
        },
    }
