"""jamovi module catalog."""

from __future__ import annotations

MODULES = [
    {"id": "regression", "title": "Regression", "use_case": "Linear and logistic regression"},
    {"id": "anova", "title": "ANOVA", "use_case": "Group mean comparisons"},
    {"id": "mediation", "title": "Mediation", "use_case": "Indirect effect models"},
    {"id": "reliability", "title": "Reliability", "use_case": "Cronbach alpha and item analysis"},
    {"id": "psychometrics", "title": "Psychometrics", "use_case": "Scale construction"},
    {"id": "meta_analysis", "title": "Meta-analysis", "use_case": "Effect size synthesis"},
    {"id": "power", "title": "Power analysis", "use_case": "Sample size planning"},
    {"id": "survival", "title": "Survival analysis", "use_case": "Time-to-event models"},
]


def list_modules() -> list[dict[str, str]]:
    return list(MODULES)
