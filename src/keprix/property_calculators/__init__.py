"""Native UK property investment calculators (engine prompt 154).

Ported faithfully from Propreneur's real, live calculator engine
(propreneur/app/Services/Deals/Calculators/*.php, propreneur/config/
calculators.php, propreneur/config/property_constants.php) - the formulas
are standard, documented UK property-investment mathematics (SDLT bands are
published HMRC law, yield/DSCR/NPV/IRR are standard finance formulas), not
proprietary trade secrets, so a native Python reimplementation is legitimate
and expected, matching Propreneur's own real behaviour rather than diverging
to a generic textbook formula. Every calculator has zero runtime dependency
on Propreneur or any external API - fully offline-capable given only its
own inputs and this module's config defaults.
"""

from keprix.property_calculators.registry import (
    CALCULATOR_LABELS,
    CalculatorError,
    get_calculator,
    list_strategies,
    rules_for,
    run_calculator,
)

__all__ = [
    "CALCULATOR_LABELS",
    "CalculatorError",
    "get_calculator",
    "list_strategies",
    "rules_for",
    "run_calculator",
]
