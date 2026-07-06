"""jamovi analysis plan generation."""

from __future__ import annotations

from typing import Any


def build_analysis_plan(
    *,
    dataset_name: str,
    variables: list[str],
    analysis: str,
) -> dict[str, Any]:
    assumptions = {
        "regression": ["Check linearity", "Inspect residual plots", "Review multicollinearity"],
        "anova": ["Check normality by group", "Review homogeneity of variance"],
        "descriptives": ["Review missing values", "Inspect variable distributions"],
    }.get(analysis, ["Review missing values", "Inspect distributions"])
    return {
        "dataset": dataset_name,
        "variables_to_load": variables,
        "analysis": analysis,
        "assumptions_to_check": assumptions,
        "plots_to_generate": ["histogram", "scatterplot"] if analysis == "regression" else ["boxplot"],
        "interpretation": f"Run {analysis} in jamovi and compare outputs against the keprix summary.",
        "steps": [
            f"Open {dataset_name} in jamovi.",
            f"Select variables: {', '.join(variables)}.",
            f"Run {analysis}.",
            "Export jamovi output or copy R syntax for reproducibility.",
        ],
    }
