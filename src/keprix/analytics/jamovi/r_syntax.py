"""R syntax workflow for jamovi analyses."""

from __future__ import annotations

from typing import Any


def plan_to_r_script(plan: dict[str, Any]) -> str:
    variables = plan.get("variables_to_load") or []
    analysis = plan.get("analysis", "descriptives")
    dataset = plan.get("dataset", "data")
    lines = [
        f"# Generated from keprix jamovi plan for {dataset}",
        f"data <- read.csv('{dataset}.csv')",
    ]
    if analysis == "regression" and len(variables) >= 2:
        y_var, x_var = variables[0], variables[1]
        lines.append(f"model <- lm({y_var} ~ {x_var}, data = data)")
        lines.append("summary(model)")
    elif analysis == "anova" and len(variables) >= 2:
        y_var, group_var = variables[0], variables[1]
        lines.append(f"fit <- aov({y_var} ~ factor({group_var}), data = data)")
        lines.append("summary(fit)")
    else:
        lines.append(f"summary(data[, c({', '.join(repr(v) for v in variables)})])")
    return "\n".join(lines) + "\n"


def store_user_r_syntax(source: str, *, analysis_id: str) -> dict[str, Any]:
    return {
        "analysis_id": analysis_id,
        "language": "r",
        "source": source.strip(),
        "artifact_type": "r_syntax",
    }
