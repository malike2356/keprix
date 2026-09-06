"""Port of CommercialDealCalculatorService.php - commercial property
underwriting: yields on passing rent and ERV, WAULT, commercial SDLT,
value-add scenarios, mixed-use panels."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from keprix.property_calculators.financial import stamp_duty_commercial


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _resolve_passing_rent_annual(inputs: dict[str, Any]) -> float:
    if inputs.get("passing_rent_annual") not in (None, ""):
        return float(inputs["passing_rent_annual"])
    if inputs.get("monthly_rent") not in (None, ""):
        return float(inputs["monthly_rent"]) * 12
    leases = _normalize_leases(inputs.get("leases") or [])
    if leases:
        return sum(lease["annual_rent"] for lease in leases)
    vacancy = str(inputs.get("vacancy_status") or "fully_let")
    if vacancy == "partially_let":
        units_occupied = int(inputs.get("units_occupied") or 0)
        rent_per_unit = float(inputs.get("rent_per_unit_annual") or 0)
        return units_occupied * rent_per_unit
    return 0.0


def _resolve_erv_annual(inputs: dict[str, Any], passing_rent: float) -> float:
    if inputs.get("erv_annual") not in (None, ""):
        return float(inputs["erv_annual"])
    if inputs.get("erv_monthly") not in (None, ""):
        return float(inputs["erv_monthly"]) * 12
    return passing_rent


def _annual_operating_costs(inputs: dict[str, Any], purchase: float, passing_rent: float) -> float:
    service_charge_net = float(inputs.get("service_charge_net_annual") or 0)
    mgmt_pct = float(inputs.get("management_pct_rent") if inputs.get("management_pct_rent") is not None else 0.08)
    insurance = float(inputs.get("insurance_annual") or (float(inputs.get("monthly_insurance") or 0) * 12))
    void_pct = float(inputs.get("void_allowance_pct") if inputs.get("void_allowance_pct") is not None else 0.05)
    maint_pct = float(inputs.get("maintenance_reserve_pct") if inputs.get("maintenance_reserve_pct") is not None else 0.02)

    management = passing_rent * mgmt_pct
    void_allowance = passing_rent * void_pct
    maintenance = purchase * maint_pct

    return service_charge_net + management + insurance + void_allowance + maintenance


def _annual_mortgage_cost(inputs: dict[str, Any], purchase: float) -> float:
    if inputs.get("monthly_mortgage") not in (None, ""):
        return float(inputs["monthly_mortgage"]) * 12

    loan = float(inputs.get("mortgage_amount") or 0)
    if loan <= 0:
        return 0.0

    rate = float(inputs.get("mortgage_rate_annual") if inputs.get("mortgage_rate_annual") is not None else 0.055)
    interest_only = bool(inputs.get("interest_only") if inputs.get("interest_only") is not None else True)

    if interest_only:
        return round(loan * rate, 2)

    term_years = int(inputs.get("mortgage_term_years") or 25)
    months = max(1, term_years * 12)
    monthly_rate = rate / 12
    if monthly_rate <= 0:
        return round(loan / term_years, 2)

    payment = loan * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    return round(payment * 12, 2)


def _resolve_stamp_duty(inputs: dict[str, Any], purchase: float) -> float:
    if inputs.get("stamp_duty") not in (None, ""):
        return float(inputs["stamp_duty"])
    return stamp_duty_commercial(purchase)


def _total_equity_deployed(inputs: dict[str, Any], purchase: float, stamp: float) -> float:
    legal = float(inputs.get("legal_costs") or inputs.get("legal_fees") or 0)
    survey = float(inputs.get("survey_costs") or inputs.get("survey_fees") or 0)
    refurb = float(inputs.get("refurb_budget") or inputs.get("refurb_fit_out") or 0)
    mortgage = float(inputs.get("mortgage_amount") or 0)

    if mortgage <= 0 and inputs.get("deposit_amount") is not None:
        deposit = float(inputs["deposit_amount"])
        return max(0.0, deposit + stamp + legal + survey + refurb)

    equity = purchase - mortgage + stamp + legal + survey + refurb
    return max(0.0, equity)


def _normalize_leases(raw: list[Any]) -> list[dict[str, Any]]:
    leases = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        rent = float(row.get("annual_rent") or row.get("rent_annual") or 0)
        if rent <= 0:
            continue
        leases.append(
            {
                "tenant_name": str(row.get("tenant_name") or "Tenant"),
                "annual_rent": rent,
                "lease_start": row.get("lease_start"),
                "lease_expiry": row.get("lease_expiry"),
                "break_clause": row.get("break_clause_date") or row.get("break_clause"),
            }
        )
    return leases


def wault_years(leases: list[dict[str, Any]]) -> float:
    today = date.today()
    weighted_sum = 0.0
    total_rent = 0.0
    for lease in leases:
        rent = lease["annual_rent"]
        if rent <= 0:
            continue
        expiry = _parse_date(lease.get("lease_expiry"))
        if expiry is None:
            continue
        years = max(0.0, (expiry - today).days / 365.25)
        weighted_sum += years * rent
        total_rent += rent
    if total_rent <= 0:
        return 0.0
    return weighted_sum / total_rent


def _value_add_scenarios(
    inputs: dict[str, Any],
    purchase: float,
    passing_rent: float,
    erv: float,
    annual_costs: float,
    annual_mortgage: float,
    target_yield_decimal: float,
) -> dict[str, Any]:
    vacancy_status = str(inputs.get("vacancy_status") or "fully_let")
    vacant_rent_gap = 0.0
    if vacancy_status == "vacant":
        fill_vacancy_income = erv
        vacant_rent_gap = max(0.0, erv - passing_rent)
    elif vacancy_status == "partially_let":
        units = max(1, int(inputs.get("number_of_units") or 1))
        occupied = int(inputs.get("units_occupied") or 0)
        rent_per_unit = float(inputs.get("rent_per_unit_annual") or (erv / units if units else 0))
        vacant_units = max(0, units - occupied)
        vacant_rent_gap = vacant_units * rent_per_unit
        fill_vacancy_income = passing_rent + vacant_rent_gap
    else:
        fill_vacancy_income = passing_rent

    fill_net = fill_vacancy_income - annual_costs - annual_mortgage
    fill_capital = round(fill_vacancy_income / target_yield_decimal, 2) if fill_vacancy_income > 0 else 0.0

    restructure_net = erv - annual_costs - annual_mortgage
    restructure_capital = round(erv / target_yield_decimal, 2) if erv > 0 else 0.0

    planning_uplift = float(inputs.get("planning_uplift_value") or 0)

    surrender_refurb = float(inputs.get("surrender_refurb_cost") or 0)
    surrender_new_rent = float(inputs.get("surrender_new_rent_annual") or 0)
    surrender_net = surrender_new_rent - annual_costs - annual_mortgage
    surrender_capital = round(surrender_new_rent / target_yield_decimal, 2) if surrender_new_rent > 0 else 0.0

    return {
        "fill_vacancy": {
            "additional_rent_annual": round(vacant_rent_gap, 2),
            "net_annual_income": round(fill_net, 2),
            "capital_value": fill_capital,
            "capital_uplift": round(fill_capital - purchase, 2),
            "net_yield_pct": round(((fill_vacancy_income - annual_costs) / purchase) * 100, 4) if purchase > 0 else 0.0,
        },
        "lease_restructure": {
            "rent_at_erv_annual": round(erv, 2),
            "net_annual_income": round(restructure_net, 2),
            "capital_value": restructure_capital,
            "capital_uplift": round(restructure_capital - purchase, 2),
            "reversionary_yield_pct": round(((erv - annual_costs) / purchase) * 100, 4) if purchase > 0 else 0.0,
        },
        "planning_uplift": {
            "manual_value_add": round(planning_uplift, 2),
            "implied_total_value": round(purchase + planning_uplift, 2),
        },
        "surrender_redevelop_upper": {
            "refurb_cost": round(surrender_refurb, 2),
            "new_rent_annual": round(surrender_new_rent, 2),
            "net_annual_income": round(surrender_net, 2),
            "capital_value": surrender_capital,
            "capital_uplift": round(surrender_capital - purchase - surrender_refurb, 2),
        },
    }


def _mixed_use_panels(
    inputs: dict[str, Any], purchase: float, annual_costs: float, annual_mortgage: float, target_yield_decimal: float
) -> dict[str, Any] | None:
    commercial_rent = float(inputs.get("mixed_commercial_rent_annual") or 0)
    residential_rent = float(inputs.get("mixed_residential_rent_annual") or 0)
    if commercial_rent <= 0 and residential_rent <= 0:
        return None

    commercial_only_net = commercial_rent - annual_costs - annual_mortgage
    commercial_only_capital = round(commercial_rent / target_yield_decimal, 2) if commercial_rent > 0 else 0.0

    combined_rent = commercial_rent + residential_rent
    combined_net = combined_rent - annual_costs - annual_mortgage
    combined_capital = round(combined_rent / target_yield_decimal, 2) if combined_rent > 0 else 0.0

    return {
        "commercial_only": {
            "passing_rent_annual": round(commercial_rent, 2),
            "net_annual_income": round(commercial_only_net, 2),
            "capital_value": commercial_only_capital,
            "net_yield_pct": round(((commercial_rent - annual_costs) / purchase) * 100, 4) if purchase > 0 else 0.0,
        },
        "with_residential_above": {
            "combined_rent_annual": round(combined_rent, 2),
            "residential_contribution_annual": round(residential_rent, 2),
            "net_annual_income": round(combined_net, 2),
            "capital_value": combined_capital,
            "additional_capital_vs_commercial_only": round(combined_capital - commercial_only_capital, 2),
        },
    }


def calculate(inputs: dict[str, Any]) -> dict[str, Any]:
    purchase = float(inputs["purchase_price"])
    passing_rent = _resolve_passing_rent_annual(inputs)
    erv = _resolve_erv_annual(inputs, passing_rent)

    annual_costs = _annual_operating_costs(inputs, purchase, passing_rent)
    annual_mortgage = _annual_mortgage_cost(inputs, purchase)
    total_costs = annual_costs + annual_mortgage

    net_annual_income = passing_rent - total_costs

    gross_yield_pct = round((passing_rent / purchase) * 100, 4) if purchase > 0 else 0.0
    net_initial_yield_pct = round(((passing_rent - annual_costs) / purchase) * 100, 4) if purchase > 0 else 0.0
    reversionary_yield_pct = round(((erv - annual_costs) / purchase) * 100, 4) if purchase > 0 else 0.0

    stamp = _resolve_stamp_duty(inputs, purchase)
    equity_deployed = _total_equity_deployed(inputs, purchase, stamp)
    roi_pct = round((net_annual_income / equity_deployed) * 100, 4) if equity_deployed > 0 else 0.0

    target_yield_pct = float(inputs.get("target_yield_pct") or 7.5)
    target_yield_decimal = max(0.01, target_yield_pct / 100)
    capital_value_at_erv = round(erv / target_yield_decimal, 2) if erv > 0 else 0.0
    forced_value_uplift = round(capital_value_at_erv - purchase, 2)

    leases = _normalize_leases(inputs.get("leases") or [])
    wault = wault_years(leases)

    value_add = _value_add_scenarios(inputs, purchase, passing_rent, erv, annual_costs, annual_mortgage, target_yield_decimal)
    mixed_use = _mixed_use_panels(inputs, purchase, annual_costs, annual_mortgage, target_yield_decimal)

    outputs = {
        "gross_yield_pct": gross_yield_pct,
        "net_initial_yield_pct": net_initial_yield_pct,
        "reversionary_yield_pct": reversionary_yield_pct,
        "net_annual_income": round(net_annual_income, 2),
        "net_monthly_cash": round(net_annual_income / 12, 2),
        "wault_years": round(wault, 2),
        "roi_pct": roi_pct,
        "total_equity_deployed": round(equity_deployed, 2),
        "capital_value_at_erv": capital_value_at_erv,
        "forced_value_uplift": forced_value_uplift,
        "stamp_duty_computed": round(stamp, 2),
        "annual_costs_total": round(total_costs, 2),
        "passing_rent_annual": round(passing_rent, 2),
        "erv_annual": round(erv, 2),
        "reversionary_uplift_annual": round(max(0.0, erv - passing_rent), 2),
        "value_add_scenarios": value_add,
    }
    if mixed_use is not None:
        outputs["mixed_use"] = mixed_use

    return {
        "outputs": outputs,
        "assumptions": [
            "Commercial SDLT uses non-residential bands (0% to £150k, 2% to £250k, 5% above); no residential surcharge.",
            "Net initial yield uses passing rent minus operating costs (excludes finance) over purchase price.",
            "Reversionary yield uses ERV minus operating costs over purchase price.",
            "WAULT is rent-weighted average unexpired lease term in years from lease expiry dates.",
            "Capital value at ERV = ERV / target yield (default 7.5% unless target_yield_pct is set).",
            "ROI = net annual income after all costs including mortgage / total equity deployed.",
        ],
    }
