"""Port of StrategyFinderService.php - five-question matcher scoring BTL,
BRR, HMO, R2R, SA, Flip, and Commercial against capital, goal, time, risk,
and skills. All scoring tables and typical-deal projections are ported
verbatim from the real Propreneur service."""

from __future__ import annotations

from typing import Any

STRATEGIES = ["btl", "brr", "hmo", "r2r", "sa", "flip", "commercial"]

CAPITAL_MIDPOINTS: dict[str, int] = {
    "under_5k": 2500,
    "5k_to_25k": 15000,
    "25_to_50k": 37500,
    "50_to_100k": 75000,
    "100_to_250k": 175000,
    "over_250k": 300000,
}

STRATEGY_MIN_CAPITAL: dict[str, int] = {
    "btl": 25000,
    "brr": 50000,
    "hmo": 50000,
    "r2r": 3000,
    "sa": 5000,
    "flip": 50000,
    "commercial": 100000,
}

BRIDGE_MONTHLY_SAVINGS = 500

CAPITAL: dict[str, dict[str, int]] = {
    "btl": {"under_5k": 0, "5k_to_25k": 0, "25_to_50k": 10, "50_to_100k": 20, "100_to_250k": 25, "over_250k": 20},
    "brr": {"under_5k": 0, "5k_to_25k": 0, "25_to_50k": 5, "50_to_100k": 15, "100_to_250k": 25, "over_250k": 20},
    "hmo": {"under_5k": 0, "5k_to_25k": 0, "25_to_50k": 5, "50_to_100k": 15, "100_to_250k": 25, "over_250k": 25},
    "r2r": {"under_5k": 25, "5k_to_25k": 22, "25_to_50k": 20, "50_to_100k": 15, "100_to_250k": 10, "over_250k": 5},
    "sa": {"under_5k": 10, "5k_to_25k": 14, "25_to_50k": 20, "50_to_100k": 25, "100_to_250k": 20, "over_250k": 15},
    "flip": {"under_5k": 0, "5k_to_25k": 0, "25_to_50k": 5, "50_to_100k": 15, "100_to_250k": 25, "over_250k": 20},
    "commercial": {"under_5k": 0, "5k_to_25k": 0, "25_to_50k": 0, "50_to_100k": 5, "100_to_250k": 10, "over_250k": 25},
}

GOAL: dict[str, dict[str, int]] = {
    "btl": {"passive_income": 25, "capital_growth": 10, "both": 18, "build_quickly": 10},
    "brr": {"passive_income": 15, "capital_growth": 25, "both": 25, "build_quickly": 20},
    "hmo": {"passive_income": 25, "capital_growth": 15, "both": 20, "build_quickly": 15},
    "r2r": {"passive_income": 20, "capital_growth": 5, "both": 15, "build_quickly": 25},
    "sa": {"passive_income": 25, "capital_growth": 10, "both": 20, "build_quickly": 20},
    "flip": {"passive_income": 5, "capital_growth": 25, "both": 15, "build_quickly": 25},
    "commercial": {"passive_income": 20, "capital_growth": 25, "both": 25, "build_quickly": 5},
}

TIME: dict[str, dict[str, int]] = {
    "btl": {"under_2": 25, "2_to_5": 25, "5_to_15": 20, "over_15": 15},
    "brr": {"under_2": 5, "2_to_5": 10, "5_to_15": 25, "over_15": 20},
    "hmo": {"under_2": 5, "2_to_5": 10, "5_to_15": 25, "over_15": 20},
    "r2r": {"under_2": 15, "2_to_5": 25, "5_to_15": 20, "over_15": 15},
    "sa": {"under_2": 10, "2_to_5": 20, "5_to_15": 25, "over_15": 15},
    "flip": {"under_2": 0, "2_to_5": 5, "5_to_15": 20, "over_15": 25},
    "commercial": {"under_2": 10, "2_to_5": 15, "5_to_15": 20, "over_15": 25},
}

RISK: dict[str, dict[str, int]] = {
    "btl": {"low": 25, "medium": 25, "high": 15},
    "brr": {"low": 10, "medium": 25, "high": 20},
    "hmo": {"low": 15, "medium": 25, "high": 15},
    "r2r": {"low": 25, "medium": 20, "high": 10},
    "sa": {"low": 15, "medium": 25, "high": 20},
    "flip": {"low": 5, "medium": 15, "high": 25},
    "commercial": {"low": 5, "medium": 15, "high": 25},
}

SKILLS: dict[str, dict[str, int]] = {
    "btl": {"none": 8, "finance": 8, "trades": 6, "sales": 6, "property": 10, "tech": 9},
    "brr": {"none": 4, "finance": 8, "trades": 10, "sales": 6, "property": 8, "tech": 6},
    "hmo": {"none": 6, "finance": 6, "trades": 8, "sales": 6, "property": 10, "tech": 7},
    "r2r": {"none": 8, "finance": 6, "trades": 6, "sales": 10, "property": 8, "tech": 9},
    "sa": {"none": 8, "finance": 6, "trades": 4, "sales": 10, "property": 8, "tech": 12},
    "flip": {"none": 4, "finance": 6, "trades": 10, "sales": 8, "property": 6, "tech": 5},
    "commercial": {"none": 2, "finance": 10, "trades": 4, "sales": 6, "property": 8, "tech": 8},
}

# Typical deal projections per strategy per capital bucket. None = not
# viable at that capital level.
PROJECTIONS: dict[str, dict[str, dict[str, Any] | None]] = {
    "btl": {
        "under_5k": None,
        "5k_to_25k": None,
        "25_to_50k": {"typical_property_value": 120000, "typical_deposit_or_capital": 30000, "typical_monthly_income": 128, "typical_gross_yield_pct": 6.0, "typical_setup_costs": 5000, "typical_months_to_first_income": 3, "note": "Northern / Midlands town, single let, IO mortgage at 5.5%."},
        "50_to_100k": {"typical_property_value": 180000, "typical_deposit_or_capital": 45000, "typical_monthly_income": 195, "typical_gross_yield_pct": 6.0, "typical_setup_costs": 7500, "typical_months_to_first_income": 3, "note": "Solid rental area, 3-bed terrace, stable long-term tenant."},
        "100_to_250k": {"typical_property_value": 250000, "typical_deposit_or_capital": 62500, "typical_monthly_income": 240, "typical_gross_yield_pct": 5.8, "typical_setup_costs": 10000, "typical_months_to_first_income": 3, "note": "Good yield belt property, long-term hold strategy."},
        "over_250k": {"typical_property_value": 350000, "typical_deposit_or_capital": 87500, "typical_monthly_income": 320, "typical_gross_yield_pct": 5.5, "typical_setup_costs": 14000, "typical_months_to_first_income": 3, "note": "Multiple units possible. Higher-value single let or portfolio start."},
    },
    "brr": {
        "under_5k": None,
        "5k_to_25k": None,
        "25_to_50k": None,
        "50_to_100k": {"typical_property_value": 65000, "typical_deposit_or_capital": 90000, "typical_monthly_income": 280, "typical_gross_yield_pct": 7.5, "typical_setup_costs": 18000, "typical_months_to_first_income": 6, "note": "Purchase £65k + £20k refurb. Refinance at 75% LTV returns ~£75k capital."},
        "100_to_250k": {"typical_property_value": 120000, "typical_deposit_or_capital": 145000, "typical_monthly_income": 380, "typical_gross_yield_pct": 8.0, "typical_setup_costs": 25000, "typical_months_to_first_income": 6, "note": "Refinance recycles most invested capital into next deal within 6 months."},
        "over_250k": {"typical_property_value": 180000, "typical_deposit_or_capital": 205000, "typical_monthly_income": 550, "typical_gross_yield_pct": 8.5, "typical_setup_costs": 30000, "typical_months_to_first_income": 6, "note": "Larger refurb project or multiple simultaneous BRR deals."},
    },
    "hmo": {
        "under_5k": None,
        "5k_to_25k": None,
        "25_to_50k": None,
        "50_to_100k": {"typical_property_value": 150000, "typical_deposit_or_capital": 55000, "typical_monthly_income": 700, "typical_gross_yield_pct": 11.0, "typical_setup_costs": 20000, "typical_months_to_first_income": 4, "note": "4-bed HMO, cheaper area. Rooms at £500/mo. Management and bills deducted."},
        "100_to_250k": {"typical_property_value": 220000, "typical_deposit_or_capital": 80000, "typical_monthly_income": 1050, "typical_gross_yield_pct": 11.5, "typical_setup_costs": 30000, "typical_months_to_first_income": 4, "note": "5-bed HMO. Rooms at £550/mo. Strong cash flow vs single let."},
        "over_250k": {"typical_property_value": 320000, "typical_deposit_or_capital": 110000, "typical_monthly_income": 1500, "typical_gross_yield_pct": 12.0, "typical_setup_costs": 40000, "typical_months_to_first_income": 4, "note": "6-7 bed HMO. Premium rooms or professional-let area."},
    },
    "r2r": {
        "under_5k": {"typical_property_value": None, "typical_deposit_or_capital": 3000, "typical_monthly_income": 200, "typical_gross_yield_pct": None, "typical_setup_costs": 3000, "typical_months_to_first_income": 1, "note": "Lease a 3-4 bed house from a landlord, sublet rooms. No mortgage or purchase deposit required."},
        "5k_to_25k": {"typical_property_value": None, "typical_deposit_or_capital": 3000, "typical_monthly_income": 350, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "One to two R2R units at this capital level. Strong immediate cashflow before deploying into ownership."},
        "25_to_50k": {"typical_property_value": None, "typical_deposit_or_capital": 5000, "typical_monthly_income": 400, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "Multiple R2R units possible at this capital level."},
        "50_to_100k": {"typical_property_value": None, "typical_deposit_or_capital": 5000, "typical_monthly_income": 400, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "R2R as immediate cashflow while remaining capital buys a BTL."},
        "100_to_250k": {"typical_property_value": None, "typical_deposit_or_capital": 5000, "typical_monthly_income": 400, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "R2R as a cashflow engine alongside ownership assets."},
        "over_250k": {"typical_property_value": None, "typical_deposit_or_capital": 5000, "typical_monthly_income": 400, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "R2R adds immediate monthly income while capital deploys into HMO or commercial."},
    },
    "sa": {
        "under_5k": None,
        "5k_to_25k": {"typical_property_value": None, "typical_deposit_or_capital": 5000, "typical_monthly_income": 300, "typical_gross_yield_pct": None, "typical_setup_costs": 5000, "typical_months_to_first_income": 1, "note": "Rent-to-SA: lease a property and sublet short-term. No purchase needed to start."},
        "25_to_50k": {"typical_property_value": 120000, "typical_deposit_or_capital": 35000, "typical_monthly_income": 650, "typical_gross_yield_pct": 14.0, "typical_setup_costs": 10000, "typical_months_to_first_income": 2, "note": "Purchase flat in commuter or tourist area. Listed on Airbnb and Booking.com."},
        "50_to_100k": {"typical_property_value": 180000, "typical_deposit_or_capital": 50000, "typical_monthly_income": 1100, "typical_gross_yield_pct": 15.5, "typical_setup_costs": 15000, "typical_months_to_first_income": 2, "note": "£120 avg nightly rate x 70% occupancy. SA management company at 20% fee."},
        "100_to_250k": {"typical_property_value": 250000, "typical_deposit_or_capital": 70000, "typical_monthly_income": 1600, "typical_gross_yield_pct": 16.0, "typical_setup_costs": 20000, "typical_months_to_first_income": 2, "note": "Premium property or 2-bed in strong SA demand area."},
        "over_250k": {"typical_property_value": 400000, "typical_deposit_or_capital": 110000, "typical_monthly_income": 2800, "typical_gross_yield_pct": 17.0, "typical_setup_costs": 30000, "typical_months_to_first_income": 2, "note": "Multiple SA units or luxury single SA property."},
    },
    "flip": {
        "under_5k": None,
        "5k_to_25k": None,
        "25_to_50k": None,
        "50_to_100k": {"typical_property_value": 80000, "typical_deposit_or_capital": 95000, "typical_monthly_income": None, "typical_gross_yield_pct": None, "typical_setup_costs": 15000, "typical_months_to_first_income": 5, "typical_profit_per_flip": 18000, "note": "Purchase £70k + £15k refurb, sell at £105k. Profit per completed flip (4-6 months)."},
        "100_to_250k": {"typical_property_value": 130000, "typical_deposit_or_capital": 155000, "typical_monthly_income": None, "typical_gross_yield_pct": None, "typical_setup_costs": 25000, "typical_months_to_first_income": 5, "typical_profit_per_flip": 35000, "note": "Purchase £120k + £25k refurb, sell at £185k after 4-6 months."},
        "over_250k": {"typical_property_value": 200000, "typical_deposit_or_capital": 235000, "typical_monthly_income": None, "typical_gross_yield_pct": None, "typical_setup_costs": 40000, "typical_months_to_first_income": 5, "typical_profit_per_flip": 55000, "note": "Larger refurb. May use bridging finance to run multiple flips in parallel."},
    },
    "commercial": {
        "under_5k": None,
        "5k_to_25k": None,
        "25_to_50k": None,
        "50_to_100k": None,
        "100_to_250k": {"typical_property_value": 350000, "typical_deposit_or_capital": 140000, "typical_monthly_income": 1800, "typical_gross_yield_pct": 7.0, "typical_setup_costs": 20000, "typical_months_to_first_income": 4, "note": "Small commercial unit on long FRI lease. Stable tenant, less management."},
        "over_250k": {"typical_property_value": 600000, "typical_deposit_or_capital": 200000, "typical_monthly_income": 3500, "typical_gross_yield_pct": 7.5, "typical_setup_costs": 35000, "typical_months_to_first_income": 4, "note": "Office/retail or permitted development (PD) conversion opportunity."},
    },
}

_SKILL_CONTENT: dict[str, dict[str, Any]] = {
    "tech": {
        "headline": "Your IT and tech background is a real edge in property",
        "body_template": (
            "Whether you build software, manage infrastructure, analyse data, support users, or ship digital "
            "products, you already think in systems, automation, and measurable outcomes. That maps cleanly onto "
            "property, especially when your focus is {goal}. Many tech professionals replace scattered spreadsheets "
            "and manual chasing with one workspace for compliance, tenants, deals, and short-let ops. {time}"
        ),
        "examples": [
            "Developers and engineers: script checks, APIs, and repeatable deal workflows",
            "Data and BI: portfolio dashboards, yield comparisons, void trends",
            "DevOps / cloud: reliable reminders, integrations, fewer dropped tasks",
            "Support and operations: tenant comms templates and SLA-style follow-ups",
            "Product and QA: test assumptions before you commit capital to a strategy",
        ],
    },
    "finance": {
        "headline": "Finance skills sharpen how you pick and fund deals",
        "body_template": (
            "A background in accounting, banking, corporate finance, or bookkeeping helps you read cashflow, "
            "stress-test assumptions, and structure funding with fewer surprises, particularly when you are aiming "
            "for {goal}. You are already comfortable with numbers; property adds asset-level detail (voids, refurb, "
            "refinance, tax wrappers). {time}"
        ),
        "examples": [
            "Mortgage and DSCR sense-checks before you offer",
            "Refinance and BRR numbers without guesswork",
            "Rent rolls and expense lines that reconcile",
        ],
    },
    "trades": {
        "headline": "Trades and construction skills cut refurb cost and risk",
        "body_template": (
            "Hands-on experience in building, plumbing, electrical, or project management means you can judge "
            "refurb scope, contractor quotes, and site issues early, valuable for {goal}. That often improves "
            "margins on BRR, flip, and HMO setups compared with investors who outsource everything blindly. {time}"
        ),
        "examples": [
            "Realistic refurb budgets and timelines",
            "Snagging and quality control on site",
            "Knowing when to DIY vs when to subcontract",
        ],
    },
    "sales": {
        "headline": "Sales and negotiation skills speed up sourcing and exits",
        "body_template": (
            "If you are used to prospecting, follow-up, and closing, property sourcing and agent relationships "
            "will feel familiar, especially when you want {goal}. Strong communicators often secure better terms on "
            "rent-to-rent, off-market leads, and tenant fill. {time}"
        ),
        "examples": [
            "Agent and vendor rapport for deal flow",
            "Pitching rent-to-rent or SA proposals to landlords",
            "Tenant enquiry handling and conversion",
        ],
    },
    "property": {
        "headline": "Property industry experience gives you a head start",
        "body_template": (
            "Time in lettings, agency, or block management means you already understand compliance, tenant "
            "cycles, and local markets, a practical advantage for {goal}. You can focus on ownership strategy and "
            "scaling rather than learning the basics from scratch. {time}"
        ),
        "examples": [
            "Compliance and licensing awareness (HMO, SA, deposits)",
            "Realistic rents and void expectations by area",
            "Professional-standard tenant and landlord processes",
        ],
    },
}

_STRATEGY_DISPLAY_NAME = {
    "btl": "Buy to Let",
    "brr": "BRR",
    "hmo": "HMO",
    "r2r": "Rent to Rent",
    "sa": "Serviced Accommodation",
    "flip": "Property Flip",
    "commercial": "Commercial property",
}

_STRATEGY_FIT_REASON = {
    "sa": "serviced accommodation benefits from automation - channel managers, dynamic pricing, guest messaging, and performance dashboards that one platform can coordinate.",
    "btl": "buy-to-let suits a systems mindset: one portfolio hub for tenancies, compliance renewals, rent tracking, and reporting without juggling spreadsheets.",
    "r2r": "rent-to-rent scales when marketing, tenant onboarding, and margin tracking are standardised, a strong fit for process-driven operators.",
    "hmo": "HMO portfolios generate more operational data (rooms, licences, inspections); structured tracking keeps compliance and per-room cashflow visible.",
    "brr": "BRR depends on tight refurb timelines and refinance numbers, project trackers and scenario models reduce guesswork.",
    "commercial": "commercial deals lean on yield, lease structure, and sensitivity analysis, closer to financial modelling than hands-on trades.",
    "flip": "flips still need disciplined cost and exit analysis; structured underwriting speeds refurb and sale decisions.",
}

_GOAL_PHRASE = {
    "passive_income": "passive income",
    "capital_growth": "capital growth",
    "both": "a balance of income and growth",
    "build_quickly": "building momentum quickly",
}

_TIME_PHRASE = {
    "under_2": "Even with only a couple of hours a week, alerts and dashboards can keep the portfolio on track.",
    "2_to_5": "A few focused hours each week are often enough once core workflows are in place.",
    "5_to_15": "With regular weekly time, you can tune automations and review performance properly.",
    "over_15": "With substantial weekly time, you can build deeper systems and move faster on the next deal.",
}


def score(answers: dict[str, Any]) -> dict[str, int]:
    capital = answers.get("capital_bucket", "under_5k")
    goal = answers.get("primary_goal", "passive_income")
    time_ = answers.get("weekly_hours", "2_to_5")
    risk = answers.get("risk_tolerance", "medium")
    skills = answers.get("pro_skills", "none")

    scores: dict[str, int] = {}
    for slug in STRATEGIES:
        scores[slug] = (
            CAPITAL[slug].get(capital, 0)
            + GOAL[slug].get(goal, 0)
            + TIME[slug].get(time_, 0)
            + RISK[slug].get(risk, 0)
            + SKILLS[slug].get(skills, 0)
        )
    return scores


def build_feasibility(
    capital_bucket: str, top_strategy: str, all_scores: dict[str, int], all_projections: dict[str, dict | None]
) -> dict[str, Any]:
    midpoint = CAPITAL_MIDPOINTS.get(capital_bucket)
    top_projection = all_projections.get(top_strategy)
    top_entry_cost = (
        (top_projection or {}).get("typical_deposit_or_capital") if top_projection is not None else None
    )
    if top_entry_cost is None:
        top_entry_cost = STRATEGY_MIN_CAPITAL.get(top_strategy)

    can_start_top = False
    capital_gap = None
    if midpoint is not None and top_entry_cost is not None:
        capital_gap = max(0, top_entry_cost - midpoint)
        can_start_top = capital_gap == 0

    ranked = sorted(all_scores.keys(), key=lambda s: all_scores[s], reverse=True)
    bridge_slug = None
    bridge_entry_cost = None
    bridge_gap = None
    for slug in ranked:
        if slug == top_strategy:
            continue
        proj = all_projections.get(slug)
        needed = (proj or {}).get("typical_deposit_or_capital") if proj is not None else None
        if needed is None or midpoint is None:
            continue
        gap = max(0, needed - midpoint)
        if bridge_slug is None or gap < (bridge_gap or float("inf")) or (gap == 0 and (bridge_gap or 0) > 0):
            bridge_slug = slug
            bridge_entry_cost = needed
            bridge_gap = gap
        if gap == 0:
            break

    months_to_top = int(-(-capital_gap // BRIDGE_MONTHLY_SAVINGS)) if capital_gap else None
    months_to_bridge = int(-(-bridge_gap // BRIDGE_MONTHLY_SAVINGS)) if bridge_gap else None

    return {
        "can_start_top_today": can_start_top,
        "top_entry_cost": top_entry_cost,
        "capital_midpoint": midpoint,
        "capital_gap": capital_gap,
        "bridge_strategy": bridge_slug,
        "bridge_entry_cost": bridge_entry_cost,
        "bridge_gap": bridge_gap,
        "months_to_bridge": months_to_bridge,
        "months_to_top": months_to_top,
        "monthly_savings_assumption": BRIDGE_MONTHLY_SAVINGS,
    }


def skill_insight(pro_skills: str, top_strategy: str, answers: dict[str, Any]) -> dict[str, Any] | None:
    if pro_skills in ("none", ""):
        return None
    content = _SKILL_CONTENT.get(pro_skills)
    if content is None:
        return None

    goal_phrase = _GOAL_PHRASE.get(answers.get("primary_goal", "passive_income"), "your stated investment goals")
    time_phrase = _TIME_PHRASE.get(
        answers.get("weekly_hours", "2_to_5"), "The time you have available still shapes how much you automate versus do manually."
    )
    strategy_name = _STRATEGY_DISPLAY_NAME.get(top_strategy, top_strategy.upper())
    why_reason = _STRATEGY_FIT_REASON.get(top_strategy, "structured workflows reduce admin overhead so more time goes to sourcing and deals.")
    skill_context = {
        "tech": "your IT and tech background",
        "finance": "your finance background",
        "trades": "your trades and construction background",
        "sales": "your sales and negotiation background",
        "property": "your property industry background",
    }.get(pro_skills, "your professional background")

    return {
        "skill_key": pro_skills,
        "headline": content["headline"],
        "body": content["body_template"].format(goal=goal_phrase, time=time_phrase),
        "why_match": f"Based on your answers and {skill_context}, {strategy_name} scores highly because {why_reason}",
        "examples": content["examples"],
    }


def run(answers: dict[str, Any]) -> dict[str, Any]:
    scores = score(answers)
    ranked = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
    top_slugs = ranked[:3]
    capital = answers.get("capital_bucket", "under_5k")

    projections = {slug: PROJECTIONS[slug].get(capital) for slug in top_slugs}
    all_projections = {slug: PROJECTIONS[slug].get(capital) for slug in STRATEGIES}

    pro_skills = answers.get("pro_skills", "none")
    top_strategy = top_slugs[0]

    return {
        "top_strategy": top_strategy,
        "top_three": top_slugs,
        "strategy_scores": scores,
        "projections": projections,
        "skill_insight": skill_insight(pro_skills, top_strategy, answers),
        "feasibility": build_feasibility(capital, top_strategy, scores, all_projections),
    }
